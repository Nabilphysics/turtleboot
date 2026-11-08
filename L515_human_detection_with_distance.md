# L515 human detection and distance

## Quick start — four terminals

Use these commands after completing installation and saving the scripts below. Keep all four terminals running. Terminal 1 logs into the Pi; terminals 2–4 run locally in UTM Ubuntu.

**Terminal 1: SSH to Pi and start the camera**

```bash
ssh ubuntu@gncrpi.local
```

After logging in:

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash
export ROS_DOMAIN_ID=30
ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true enable_color:=true \
  enable_accel:=false enable_gyro:=false \
  depth_module.profile:=320x240x30 \
  rgb_camera.profile:=640x480x15 \
  enable_sync:=false align_depth.enable:=false pointcloud.enable:=false
```

**Terminal 2: UTM calibration relay**

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=30
python3 ~/human_detection/calibration_relay.py
```

**Terminal 3: UTM depth registration**

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=30
ros2 run depth_image_proc register_node --ros-args \
  -r __node:=l515_depth_registration \
  -r depth/image_rect:=/registration_input/depth/image_rect \
  -r depth/camera_info:=/registration_input/depth/camera_info \
  -r rgb/camera_info:=/registration_input/rgb/camera_info \
  -r depth_registered/image_rect:=/camera/depth_registered/image_rect \
  -r depth_registered/camera_info:=/camera/depth_registered/camera_info \
  -p queue_size:=5
```

**Terminal 4: UTM person detection and distance**

```bash
source /opt/ros/jazzy/setup.bash
source ~/human_detection/.venv/bin/activate
export ROS_DOMAIN_ID=30
cd ~/human_detection
python human_distance.py
```

Press **Q** in the video window to exit. Ctrl+C stops each other process. Restart a process after editing its script. Avoid duplicate drivers/relays and close RViz/rate monitors while judging latency.



Session record: November 8, 2026. Prepared with ChatGPT from our working session.

**Camera capture runs on the TurtleBot3 Pi; detection and depth registration run in Ubuntu 24.04 ARM64 inside UTM on the Mac.** Both use ROS 2 Jazzy and `ROS_DOMAIN_ID=30`. First install/start the Pi camera using [L515_TurtleBot3_RPi4.md](L515_TurtleBot3_RPi4.md).

Our tested settings produced responsive RGB person detection and useful, intermittent distance estimates. The complete code below consolidates the code and fixes from our session; it is syntax checked, but this exported consolidation has not been rerun on the physical camera. Keep your existing working scripts as backups before replacing them.

## 1. Install on UTM Ubuntu

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv \
  ros-jazzy-cv-bridge ros-jazzy-depth-image-proc
mkdir -p ~/human_detection
cd ~/human_detection
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install 'numpy<2' 'opencv-python<4.12' ultralytics
python -m pip freeze > requirements-working.txt
```

Use the existing working environment if already installed. The model is `yolo11n.pt`; Ultralytics downloads it on first use if it is absent, requiring internet access. Only class `0` (person) is requested. CPU inference in our earlier RGB test was typically about 27–36 ms after warmup; this is not total video latency.

## 2. Save the calibration relay

Save this as `~/human_detection/calibration_relay.py`:

```python
import copy
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image


class CalibrationRelay(Node):
    def __init__(self):
        super().__init__('calibration_relay')
        self.depth_info = None
        self.color_info = None
        # Integer depth creates RELIABLE/VOLATILE publishers. Registration
        # requests RELIABLE, so BEST_EFFORT publishers would be incompatible.
        self.image_pub = self.create_publisher(
            Image, '/registration_input/depth/image_rect', 10)
        self.depth_pub = self.create_publisher(
            CameraInfo, '/registration_input/depth/camera_info', 10)
        self.color_pub = self.create_publisher(
            CameraInfo, '/registration_input/rgb/camera_info', 10)
        self.subs = [
            self.create_subscription(CameraInfo, '/camera/depth/camera_info',
                                     self.receive_depth_info, qos_profile_sensor_data),
            self.create_subscription(CameraInfo, '/camera/color/camera_info',
                                     self.receive_color_info, qos_profile_sensor_data),
            self.create_subscription(Image, '/camera/depth/image_rect_raw',
                                     self.receive_depth, qos_profile_sensor_data),
        ]

    def receive_depth_info(self, msg):
        self.depth_info = msg

    def receive_color_info(self, msg):
        self.color_info = msg

    def receive_depth(self, msg):
        if self.depth_info is None or self.color_info is None:
            return
        if (msg.width, msg.height) != (self.depth_info.width,
                                       self.depth_info.height):
            return
        di = copy.deepcopy(self.depth_info)
        ci = copy.deepcopy(self.color_info)
        # Cache fixed calibration, stamp metadata for this depth image.
        # Actual RGB/depth image timestamps are never rewritten.
        di.header.stamp = copy.deepcopy(msg.header.stamp)
        ci.header.stamp = copy.deepcopy(msg.header.stamp)
        self.depth_pub.publish(di)
        self.color_pub.publish(ci)
        self.image_pub.publish(msg)


def main():
    rclpy.init()
    node = CalibrationRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
```

The relay avoids waiting for a separately timestamped color calibration message for every depth frame. Keep camera profiles fixed during a run. This does not synchronize the physical exposures.

## 3. Save the detector

Save this as `~/human_detection/human_distance.py`:

```python
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import rclpy
import torch
from cv_bridge import CvBridge
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Image
from ultralytics import YOLO


def stamp(msg):
    return msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9


class HumanDistance(Node):
    def __init__(self):
        super().__init__('human_distance')
        self.bridge = CvBridge()
        self.lock = threading.Lock()
        self.rgb = deque(maxlen=10)
        self.depth = deque(maxlen=120)  # History for delayed RGB arrival.
        qos = QoSProfile(depth=1,
                         reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        self.subs = [
            self.create_subscription(Image, '/camera/color/image_raw',
                                     self.receive_rgb, qos),
            self.create_subscription(Image, '/camera/depth_registered/image_rect',
                                     self.receive_depth, qos),
        ]
        self.output = self.create_publisher(Image, '/human_detection/image', qos)

    def receive_rgb(self, msg):
        with self.lock:
            self.rgb.append((msg, time.monotonic()))

    def receive_depth(self, msg):
        with self.lock:
            self.depth.append(msg)

    def take_pair(self):
        with self.lock:
            if not self.rgb:
                return None
            rgb, received = self.rgb[-1]
            self.rgb.clear()  # Process newest RGB, never a video backlog.
            if time.monotonic() - received > 0.75:
                return None
            candidates = [d for d in self.depth
                          if (d.width, d.height) == (rgb.width, rgb.height)]
            depth = None
            if candidates:
                nearest = min(candidates, key=lambda d: abs(stamp(d)-stamp(rgb)))
                if abs(stamp(nearest)-stamp(rgb)) <= 0.20:
                    depth = nearest
            return rgb, depth


def estimate_depth(depth, box):
    h, w = depth.shape
    x1, y1, x2, y2 = map(float, box)
    bw, bh = x2-x1, y2-y1
    left = max(0, min(w, int(x1 + 0.30*bw)))
    right = max(0, min(w, int(x2 - 0.30*bw)))
    top = max(0, min(h, int(y1 + 0.25*bh)))
    bottom = max(0, min(h, int(y2 - 0.25*bh)))
    roi = depth[top:bottom, left:right]
    if roi.size == 0:
        return None
    values = roi[np.isfinite(roi) & (roi >= 0.25) & (roi <= 9.0)]
    if values.size < max(10, int(roi.size * 0.10)):
        return None
    return float(np.median(values))


def spin_node(node):
    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass


def main():
    torch.set_num_threads(2)
    model = YOLO(str(Path(__file__).with_name('yolo11n.pt')))
    rclpy.init()
    node = HumanDistance()
    worker = threading.Thread(target=spin_node, args=(node,), daemon=True)
    worker.start()
    cv2.namedWindow('Human distance', cv2.WINDOW_NORMAL)
    node.get_logger().info('Waiting for RGB and registered depth. Press Q to exit.')
    last_log = 0.0
    try:
        while rclpy.ok():
            pair = node.take_pair()
            if pair is None:
                if cv2.waitKey(10) & 0xff == ord('q'):
                    break
                time.sleep(0.005)
                continue
            rgb_msg, depth_msg = pair
            frame = node.bridge.imgmsg_to_cv2(rgb_msg, 'bgr8').copy()
            depth = None
            if depth_msg is not None:
                a = node.bridge.imgmsg_to_cv2(depth_msg, 'passthrough')
                if depth_msg.encoding == '16UC1':
                    depth = a.astype(np.float32) * 0.001
                elif depth_msg.encoding == '32FC1':
                    depth = a.astype(np.float32)
                if depth is not None and depth.shape != frame.shape[:2]:
                    depth = None
            result = model.predict(frame, classes=[0], conf=0.45,
                                   imgsz=320, device='cpu', verbose=False)[0]
            reports = []
            for box in result.boxes:
                coords = box.xyxy[0].cpu().numpy()
                z = estimate_depth(depth, coords) if depth is not None else None
                distance = f'{z:.2f} m' if z is not None else 'distance unavailable'
                reports.append(distance)
                x1, y1, x2, y2 = map(int, coords)
                label = f'Person {float(box.conf[0]):.2f} | {distance}'
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, max(20, y1-8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            output = node.bridge.cv2_to_imgmsg(frame, 'bgr8')
            output.header = rgb_msg.header
            node.output.publish(output)
            cv2.imshow('Human distance', frame)
            now = time.monotonic()
            if now-last_log >= 2.0:
                node.get_logger().info(f'People: {len(reports)}; depths: {reports}')
                last_log = now
            if cv2.waitKey(1) & 0xff == ord('q'):
                break
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        worker.join(timeout=3)
        node.destroy_node()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
```

For RGB-only detection, run with registration and the relay stopped: RGB continues without distance after any retained depth history no longer matches. The model and thresholds are unchanged.

## 4. What made it work

| Problem | Working change |
|---|---|
| Pi SDK alignment alternated 320×240 and 640×480 | Disable it; register raw depth on UTM using camera calibration and TF |
| Relay published Best Effort; registration requested Reliable | Make all three relay publishers Reliable/Volatile |
| RGB arrived behind depth; short history lost matching frames | Retain 120 depth frames, choose nearest timestamp within 0.20 s |
| GUI froze waiting for matched pairs | Always process newest RGB; distance is optional |

Our diagnostic found matching 640×480 images with a **0.016 s** timestamp difference, but latest depth was **0.913 s** ahead of latest RGB. Registered depth had **10.4%** valid pixels. After increasing depth history, distances such as 0.74 m, 0.93 m, and 1.25 m appeared and the user confirmed good operation. Registration varied roughly 6–20 Hz in one test; these are observations, not guaranteed performance.

## Interpretation and troubleshooting

- `16UC1` ROS depth is converted from millimetres; `32FC1` is interpreted in metres. The displayed number is median camera-forward depth in the central portion of the detected box, not a tracked person's exact body centre or Euclidean range.
- `distance unavailable` is intentional when no timestamp-compatible frame exists or the ROI has too few usable pixels. The code does not substitute the last person's old distance.
- Registration creates sparse output when projecting low-resolution depth into larger RGB geometry. Do not resize raw depth and assume RGB pixels correspond.
- Registration targets the color camera's rectified geometry; this baseline detects on the driver's raw RGB. Residual lens distortion and calibration errors can affect box-to-depth correspondence. Rectifying RGB consistently and validating with measured targets are needed before claiming precision.
- A large history permits delayed matching but does not remove upstream latency. The 0.75 s check measures time since local receipt, not sensor-to-screen age. We have not validated this as a collision-safety or robot-control system.
- If output stops, check `ros2 topic info /registration_input/depth/image_rect --verbose` for QoS, raw RGB/depth rates, and `ros2 run tf2_ros tf2_echo camera_color_optical_frame camera_depth_optical_frame`. Registration subscribes lazily when an output subscriber exists.
- The Wayland/XDG Qt warning did not prevent our window working. These scripts do **not** record images or video; they publish annotated frames and log detections. ROS launch may retain ordinary text logs.
