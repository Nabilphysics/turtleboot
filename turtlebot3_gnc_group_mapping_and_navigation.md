# TurtleBot3 GNC Group Mapping and Navigation

This document summarizes the working ROS 2 Jazzy workflow used by the GNC group for TurtleBot3 Burger mapping and navigation.

---

## 1. Basic Startup

### On the Raspberry Pi / TurtleBot3

Start the TurtleBot3 hardware bringup:

```bash
source /opt/ros/jazzy/setup.bash

export ROS_DOMAIN_ID=30
export TURTLEBOT3_MODEL=burger

ros2 launch turtlebot3_bringup robot.launch.py
```

The robot should publish the main topics such as:

```text
/scan
/odom
/tf
/tf_static
/joint_states
/cmd_vel
```

---

## 2. Start Mapping

### On the Ubuntu computer

Open a new terminal and run:

```bash
source /opt/ros/jazzy/setup.bash

export ROS_DOMAIN_ID=30
export TURTLEBOT3_MODEL=burger

ros2 launch slam_toolbox online_async_launch.py
```

### Start RViz

In another terminal:

```bash
rviz2
```

Recommended RViz settings:

```text
Fixed Frame = map
```

Add these displays:

```text
Map        -> /map
LaserScan  -> /scan
RobotModel
TF
```

### Start Teleoperation

In another terminal:

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

Drive the robot slowly around the environment until the map is complete.

---

## 3. Save the Map

Create a map folder if needed:

```bash
mkdir -p ~/maps
```

Save the current SLAM map:

```bash
ros2 run nav2_map_server map_saver_cli \
  -f ~/maps/my_room
```

This creates:

```text
~/maps/my_room.yaml
~/maps/my_room.pgm
```

Verify:

```bash
ls -lh ~/maps/my_room.*
```

---

# 4. Start Navigation

Stop SLAM Toolbox before starting localization and navigation:

```bash
pkill -INT -f slam_toolbox 2>/dev/null || true
```

## Start Localization

```bash
source /opt/ros/jazzy/setup.bash

export ROS_DOMAIN_ID=30
export TURTLEBOT3_MODEL=burger

ros2 launch nav2_bringup localization_launch.py \
  map:=$HOME/maps/my_room.yaml \
  params_file:=$HOME/nav2_params_tb3.yaml \
  use_sim_time:=False \
  use_composition:=False
```

Keep this terminal running.

---

## Start Navigation

Open another terminal:

```bash
source /opt/ros/jazzy/setup.bash

export ROS_DOMAIN_ID=30
export TURTLEBOT3_MODEL=burger

ros2 launch nav2_bringup navigation_launch.py \
  params_file:=$HOME/nav2_params_tb3.yaml \
  use_sim_time:=False \
  use_composition:=False
```

Keep this terminal running.

---

## Start RViz for Navigation

Open another terminal:

```bash
ros2 launch nav2_bringup rviz_launch.py
```

In RViz:

1. Set the fixed frame to:

```text
map
```

2. Use **2D Pose Estimate** to place the robot at its real position and orientation.

3. Wait a few seconds for AMCL to settle.

4. Use **Nav2 Goal** to send the robot to a destination.

---

# 5. Activate Nav2 Lifecycle Servers

In our current setup, some Nav2 lifecycle servers sometimes remain `inactive` or `unconfigured` after launch.

Run this activation block after starting localization and navigation:

```bash
for node in \
/map_server \
/amcl \
/controller_server \
/smoother_server \
/planner_server \
/route_server \
/behavior_server \
/velocity_smoother \
/collision_monitor \
/bt_navigator \
/waypoint_follower \
/docking_server
do

  state=$(ros2 lifecycle get "$node" 2>/dev/null)

  echo "$node -> $state"

  if echo "$state" | grep -q "unconfigured"; then
    echo "Configuring $node ..."
    ros2 lifecycle set "$node" configure
    sleep 1
    state=$(ros2 lifecycle get "$node" 2>/dev/null)
  fi

  if echo "$state" | grep -q "inactive"; then
    echo "Activating $node ..."
    ros2 lifecycle set "$node" activate
    sleep 1
  fi

done
```

Check final states:

```bash
for node in \
/map_server \
/amcl \
/controller_server \
/smoother_server \
/planner_server \
/route_server \
/behavior_server \
/velocity_smoother \
/collision_monitor \
/bt_navigator \
/waypoint_follower \
/docking_server
do
  echo -n "$node -> "
  ros2 lifecycle get "$node" 2>/dev/null
done
```

For normal operation, the important servers should show:

```text
active [3]
```

Especially:

```text
/map_server
/amcl
/controller_server
/planner_server
/behavior_server
/velocity_smoother
/collision_monitor
/bt_navigator
```

---

# 6. Custom GNC Group Navigation Setup

Our navigation uses a custom Nav2 parameter file:

```text
~/nav2_params_tb3.yaml
```

The current TurtleBot3 is an official **TurtleBot3 Burger**.

## Burger Robot Geometry

Both local and global costmaps use:

```yaml
robot_radius: 0.105
```

This matches the physical TurtleBot3 Burger radius.

---

## Obstacle Clearance

Our current target is approximately a 2-inch obstacle clearance.

```yaml
inflation_radius: 0.16
cost_scaling_factor: 10.0
```

This is intentionally less conservative than the normal TurtleBot3/Nav2 example settings because we want the Burger to move through relatively tight indoor spaces.

The Collision Monitor is still enabled as an additional safety layer.

---

## MPPI Controller Tuning

The controller was tuned to reduce CPU load and improve response:

```yaml
controller_frequency: 15.0
```

MPPI:

```yaml
time_steps: 40
model_dt: 0.067
batch_size: 800
visualize: false
```

Velocity limits:

```yaml
vx_max: 0.5
vx_min: -0.35
wz_max: 1.9
```

Additional MPPI behavior:

```yaml
failure_tolerance: 2.0
retry_attempt_limit: 3
regenerate_noises: false
```

---

## MPPI Path-Following Critic Tuning

### PathAlignCritic

```yaml
cost_weight: 9.0
offset_from_furthest: 20
```

### PathFollowCritic

```yaml
cost_weight: 7.0
offset_from_furthest: 6
```

### PathAngleCritic

```yaml
cost_weight: 2.0
offset_from_furthest: 20
max_angle_to_furthest: 0.785
```

These settings were adjusted to reduce unnecessary turning, wandering, and over-correction while following a simple path.

---

## Progress Checker Tuning

To prevent the robot from incorrectly declaring itself stuck near the goal:

```yaml
required_movement_radius: 0.03
movement_time_allowance: 30.0
```

This is more tolerant than the earlier configuration.

---

## Costmap Timing

The planner was repeatedly reporting:

```text
Costmap timed out waiting for update
```

So the planner timeout was increased:

```yaml
costmap_update_timeout: 5.0
```

Target global costmap rates:

```yaml
update_frequency: 5.0
publish_frequency: 2.0
```

Local costmap rates used during tuning:

```yaml
update_frequency: 8.0
publish_frequency: 4.0
```

---

## TF Timing Tolerance

Because this system uses ROS 2 communication between the TurtleBot3 Raspberry Pi and an Ubuntu environment running in UTM, occasional TF timing delays were observed.

The custom configuration uses a larger transform tolerance where applicable:

```yaml
transform_tolerance: 1.0
```

Typical errors that indicate a TF/time synchronization problem are:

```text
Lookup would require extrapolation into the future
Transform data too old
Failed to transform end pose to global frame
Message Filter dropping message
```

When these appear repeatedly, check the Raspberry Pi and Ubuntu clocks before changing navigation tuning.

---

# 7. Live Navigation Monitor

A custom `htop`-style monitor is used during navigation.

It continuously checks:

```text
Nav2 lifecycle server states
/scan publisher
/odom publisher
/map publisher
map -> base_footprint TF
odom -> base_footprint TF
base_footprint -> base_scan TF
robot/Pi timestamp vs Ubuntu/UTM timestamp
recent navigation errors
```

It highlights unhealthy states in red.

For example:

```text
/planner_server     INACTIVE
```

or:

```text
/scan timestamp     TIME MISMATCH
```

The monitor is useful because several navigation failures were caused by stale TF data rather than by the global path itself.

---

# 8. Important Time Synchronization Check

The Raspberry Pi and Ubuntu computer must have closely synchronized clocks.

On Ubuntu:

```bash
date +%s.%N
```

On the Raspberry Pi:

```bash
date +%s.%N
```

The difference should be small.

A significant time mismatch can cause:

```text
base_scan transform failures
map -> odom transform too old
costmap updates to fail
collision monitor to stop the robot
planner timeouts
navigation goal aborts
```

---

# 9. Difference Between Our Custom Setup and the Official TurtleBot3 Setup

The official TurtleBot3 Navigation2 setup normally uses the TurtleBot3-specific navigation package and its provided parameters.

A typical official launch is:

```bash
ros2 launch turtlebot3_navigation2 navigation2.launch.py \
  map:=$HOME/maps/my_room.yaml
```

Our current GNC group setup is different in several important ways.

## 9.1 Separate Localization and Navigation Launches

Instead of launching everything from one TurtleBot3-specific launch file, we use:

```bash
ros2 launch nav2_bringup localization_launch.py
```

and:

```bash
ros2 launch nav2_bringup navigation_launch.py
```

separately.

This makes debugging easier because localization and navigation can be inspected independently.

---

## 9.2 Composition Disabled

We currently use:

```text
use_composition:=False
```

This runs Nav2 servers as separate processes instead of loading them into one component container.

This was chosen because it makes lifecycle and crash debugging easier in our Ubuntu/UTM setup.

---

## 9.3 Manual Lifecycle Recovery

The official setup expects the Nav2 Lifecycle Manager to automatically configure and activate all managed servers.

In our setup, some servers occasionally remain inactive.

Therefore, we manually check and activate:

```text
planner_server
behavior_server
velocity_smoother
collision_monitor
bt_navigator
and other Nav2 lifecycle nodes
```

when required.

---

## 9.4 Custom Burger Costmap Geometry

Our previous custom file incorrectly used:

```yaml
robot_radius: 0.22
```

which is much too large for a Burger.

The current GNC configuration uses:

```yaml
robot_radius: 0.105
```

for the official TurtleBot3 Burger.

---

## 9.5 Smaller Obstacle Inflation

Our custom configuration uses:

```yaml
inflation_radius: 0.16
cost_scaling_factor: 10.0
```

to allow approximately 2 inches of additional obstacle clearance.

This is more aggressive and less conservative than typical official/example Navigation2 settings.

---

## 9.6 Custom MPPI Tuning

Our MPPI controller has been tuned for this particular robot/computer combination.

The important custom settings include:

```yaml
controller_frequency: 15.0
batch_size: 800
time_steps: 40
model_dt: 0.067
visualize: false
```

This was done because the original heavier MPPI setup could not maintain the desired controller loop rate.

---

## 9.7 More Tolerant Progress Checking

Our custom setup uses:

```yaml
required_movement_radius: 0.03
movement_time_allowance: 30.0
```

to prevent false `Failed to make progress` errors near the goal.

---

## 9.8 Larger TF Tolerance

Because our control computer is running Ubuntu in UTM and communicating with a Raspberry Pi over the network, we observed occasional timestamp and TF delays.

Therefore, our custom setup uses more tolerant transform timing parameters and a live clock/TF monitor.

---

# 10. Recommended Workflow

For normal GNC group operation:

```text
1. Start TurtleBot3 bringup on Raspberry Pi
2. Start mapping with SLAM Toolbox
3. Drive using teleop
4. Save the map
5. Stop SLAM
6. Start localization
7. Start navigation
8. Configure/activate any inactive lifecycle nodes
9. Start RViz
10. Set 2D Pose Estimate
11. Verify Nav2/TF status
12. Send Nav2 Goal
13. Keep the live monitor running during navigation
```

---

## Useful Logs

Navigation log:

```bash
tail -f ~/navigation.log
```

Localization log:

```bash
tail -f ~/localization.log
```

Common errors to watch for:

```text
Costmap timed out waiting for update
Failed to make progress
Optimizer fail to compute path
Collision Ahead
Lookup would require extrapolation into the future
Transform data too old
Action server is inactive
```

---

## Notes

- Always verify that the TurtleBot3 model is set correctly:

```bash
export TURTLEBOT3_MODEL=burger
```

- Keep the same ROS domain on the Raspberry Pi and Ubuntu computer:

```bash
export ROS_DOMAIN_ID=30
```

- Always set the initial pose in RViz after starting AMCL.

- If navigation suddenly becomes confused even when the physical path is clear, first check:
  1. Nav2 lifecycle states
  2. TF freshness
  3. Raspberry Pi vs Ubuntu clock synchronization
  4. `/scan`
  5. `/odom`
  6. costmap update errors

Do not immediately change planner/controller parameters until timing and lifecycle health are verified.
