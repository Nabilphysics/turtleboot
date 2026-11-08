#!/usr/bin/env python3
"""Animate a Gazebo obstacle and visualize its commanded pose in RViz."""
import math
import subprocess
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker


class ObstacleAnimator(Node):
    def __init__(self):
        super().__init__('obstacle_animator')

        self.world = 'default'
        self.model_name = 'moving_obstacle'
        self.center_x = 0.25
        self.center_y = 1.0
        self.amplitude = 0.75
        self.period = 30.0
        self.z = 0.0
        self.mesh_scale = 0.01

        # Assumes Gazebo world coordinates coincide with ROS odom.
        self.reference_frame = 'odom'
        self.mesh_uri = (
            Path.home() / 'turtlebot3_custom/models/test_object/meshes/obstacle_basic.obj'
        ).as_uri()

        self.start_time = time.monotonic()
        self.marker_pub = self.create_publisher(
            Marker, '/moving_obstacle/marker', 10
        )
        self.path_pub = self.create_publisher(
            Marker, '/moving_obstacle/trajectory', 10
        )
        self.timer = self.create_timer(0.2, self.update_obstacle)
        self.get_logger().info('Moving obstacle animation started.')

    def update_obstacle(self):
        t = time.monotonic() - self.start_time
        omega = 2.0 * math.pi / self.period
        x = self.center_x + self.amplitude * math.cos(omega * t)
        y = self.center_y

        request = (
            f'name: "{self.model_name}", '
            f'position: {{x: {x:.6f}, y: {y:.6f}, z: {self.z:.6f}}}, '
            'orientation: {w: 1.0}'
        )
        try:
            result = subprocess.run(
                [
                    'gz', 'service', '-s', f'/world/{self.world}/set_pose',
                    '--reqtype', 'gz.msgs.Pose',
                    '--reptype', 'gz.msgs.Boolean',
                    '--timeout', '500', '--req', request,
                ],
                capture_output=True, text=True, timeout=1.0,
            )
        except subprocess.TimeoutExpired:
            self.get_logger().warning('Gazebo pose request timed out.')
            return

        if result.returncode != 0 or 'data: true' not in result.stdout.lower():
            self.get_logger().warning('Gazebo did not confirm the pose update.')
            return

        marker = Marker()
        marker.header.frame_id = self.reference_frame
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = 'moving_obstacles'
        marker.id = 0
        marker.type = Marker.MESH_RESOURCE
        marker.action = Marker.ADD
        marker.mesh_resource = self.mesh_uri
        marker.pose.position.x = x
        marker.pose.position.y = y
        marker.pose.position.z = self.z
        marker.pose.orientation.w = 1.0
        marker.scale.x = self.mesh_scale
        marker.scale.y = self.mesh_scale
        marker.scale.z = self.mesh_scale
        marker.color.r = 0.2
        marker.color.g = 0.8
        marker.color.b = 1.0
        marker.color.a = 1.0
        self.marker_pub.publish(marker)
        self.publish_trajectory()

    def publish_trajectory(self):
        trajectory = Marker()
        trajectory.header.frame_id = self.reference_frame
        trajectory.header.stamp = self.get_clock().now().to_msg()
        trajectory.ns = 'obstacle_trajectory'
        trajectory.id = 1
        trajectory.type = Marker.LINE_STRIP
        trajectory.action = Marker.ADD
        trajectory.pose.orientation.w = 1.0
        trajectory.scale.x = 0.03
        trajectory.color.r = 0.0
        trajectory.color.g = 1.0
        trajectory.color.b = 0.0
        trajectory.color.a = 1.0

        for i in range(101):
            t = self.period * i / 100
            x = self.center_x + self.amplitude * math.cos(
                2.0 * math.pi * t / self.period
            )
            point = Point()
            point.x = x
            point.y = self.center_y
            point.z = self.z + 0.05
            trajectory.points.append(point)

        self.path_pub.publish(trajectory)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleAnimator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
