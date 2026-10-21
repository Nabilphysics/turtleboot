# Intel RealSense L515 Camera Setup
## Ubuntu 24.04 in UTM on a MacBook Air

This README records installation, firmware updates, and the ROS 2 Jazzy/RViz 2 integration completed on October 20, 2026. It includes local compatibility patches and observed troubleshooting results. Intermittent streaming remains unresolved; TurtleBot3/Nav2 integration is pending.

## Quick start: open the camera

Choose one of the two methods below. **Close RealSense Viewer before launching the ROS camera driver, and stop the ROS camera driver before opening Viewer.** Attach the L515 to Ubuntu through UTM's USB menu first.

### Option A: RealSense Viewer (without ROS)

In Ubuntu:

```bash
realsense-viewer
```

Enable the **L500 depth sensor**. Use **2D** for the depth image and pixel-distance inspection, or **3D** for the point cloud. With the current USB 2 cable, choose **320×240 at 30 FPS**. Close Viewer when finished.

### Option B: ROS 2 camera and RViz 2

These commands assume the SDK, patched ROS wrapper, and workspace described below are already installed.

**Terminal 1 — start the camera driver:**

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash

ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true \
  enable_color:=false \
  enable_accel:=false \
  enable_gyro:=false \
  depth_module.profile:=320x240x30 \
  pointcloud.enable:=true \
  pointcloud.stream_filter:=0
```

Keep Terminal 1 running.

**Terminal 2 — open the saved RViz configuration:**

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash
rviz2 -d ~/rviz/rviz2.rviz
```

If you have not saved that configuration yet, run `rviz2` and configure:

| Display setting | Value |
| --- | --- |
| Global Fixed Frame | camera_link |
| Global Frame Rate | 10 |
| PointCloud2 Topic | /camera/depth/color/points |
| PointCloud2 Reliability / Durability | Best Effort / Volatile |
| PointCloud2 queue Depth / Decay Time | 1 / 0 |
| Color Transformer / Axis | AxisColor / Z |
| Use Fixed Frame (coloring) | Unchecked |
| Image Topic | /camera/depth/image_rect_raw |
| Image Reliability / Durability | Best Effort / Volatile |
| Image Normalize Range | Checked |

Save using **File → Save Config As** at `/home/nabil/rviz/rviz2.rviz` (create the folder if needed). Use your actual username/path on another computer.

**Optional Terminal 3 — check point-cloud reception:**

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash
ros2 topic hz /camera/depth/color/points --window 100
```

Stop monitoring and the camera driver with **Ctrl+C** in their respective terminals. Closing RViz alone does not stop the camera driver.

**Current limitation:** intermittent streaming stalls were observed in UTM. Restarting restored data, but the underlying cause has not been confirmed. Nav2 configuration is still pending.

---

## 1. Setup and verified status

| Component | Configuration / status |
| --- | --- |
| Host | MacBook Air, Apple Silicon |
| USB connection | Earlier USB 3 test: 5 Gbps; October 20 ROS session: USB 2.1 with Pixel 7 cable |
| Virtual machine | Ubuntu 24.04 ARM64 inside UTM |
| Camera | Intel RealSense L515 |
| SDK | librealsense v2.53.1, built from source |
| Firmware | Updated from 01.04.01.00 to 01.05.08.01 |
| Working | Camera enumeration, SDK viewer, ROS depth topics, point cloud, RViz 2 visualization |
| Capabilities detected | RGB, accelerometer, gyroscope |
| Pending | Streaming stability, robot mounting/TF, TurtleBot3 / Nav2 integration |

RGB and IMU capabilities were enumerated; that alone does not verify live RGB or IMU streaming.

## 2. Verify USB connection on macOS

Connect the camera using a USB 3-capable cable and port. In a macOS terminal:

```bash
ioreg -p IOUSB -l -w 0 | grep -A35 -i "RealSense"
```

The camera appeared as:

```text
Intel(R) RealSense(TM) 515
```

Initially:

```text
UsbLinkSpeed = 480000000
```

This indicates USB 2.0 speed (480 Mbps). After reconnecting/changing the USB connection:

```text
UsbLinkSpeed = 5000000000
```

This indicates a 5 Gbps USB 3.x link.

## 3. Attach the camera to Ubuntu through UTM

With Ubuntu running, select the L515 in UTM's USB device menu to attach it to the VM.

Inside Ubuntu:

```bash
lsusb
```

Observed output:

```text
Bus 006 Device 002: ID 8086:0b64 Intel Corp. RealSense L515
```

Bus and device numbers can change after reconnecting. The camera must be attached to the system running its driver; attaching it to Ubuntu passes control from macOS to the VM.

## 4. Install build dependencies

Run inside Ubuntu:

```bash
sudo apt update
sudo apt install -y \
  git \
  cmake \
  build-essential \
  libusb-1.0-0-dev \
  libudev-dev \
  libssl-dev \
  pkg-config \
  libgtk-3-dev \
  libglfw3-dev \
  libgl1-mesa-dev \
  libglu1-mesa-dev
```

## 5. Download the working SDK version

```bash
cd ~
git clone https://github.com/realsenseai/librealsense.git
cd librealsense
git checkout v2.53.1
```

A detached HEAD message is expected when checking out a release tag.

**Version requirement:** retain the working v2.53.1 installation. The SDK v2.55.1 release removed L515 support, so upgrading blindly to a newer SDK can break detection. See the official release discussion in References.

If the repository already exists, use the existing folder rather than cloning over it.

## 6. Install udev rules

From the source directory:

```bash
cd ~/librealsense
sudo ./scripts/setup_udev_rules.sh
```

## 7. Build and install librealsense

```bash
cd ~/librealsense
mkdir -p build
cd build

cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_EXAMPLES=true \
  -DBUILD_GRAPHICAL_EXAMPLES=true

make -j2
sudo make install
sudo ldconfig
```

The build completed successfully at 100%. These are the commands used in this setup; no kernel patch or alternate USB backend was needed for the successful viewer test.

## 8. Troubleshoot “No device detected”

Initially:

```bash
rs-enumerate-devices
```

returned:

```text
No device detected. Is it plugged in?
```

No video devices were present:

```bash
ls -l /dev/video*
```

The following checks were used:

```bash
lsusb -t
lsmod | grep uvcvideo
sudo modprobe uvcvideo
sudo dmesg | grep -i -E "realsense|uvc|video|8086|0b64" | tail -100
```

The kernel log included:

```text
Found UVC 1.50 device Intel(R) RealSense(TM) 515 (8086:0b64)
```

The successful fix was to **reattach the L515 from UTM's USB device menu**. USB re-enumeration had temporarily disrupted the VM attachment.

If this recurs:

1. Check whether UTM still has the camera attached.
2. Reattach it if needed.
3. Run `lsusb` and `rs-enumerate-devices` again.
4. Check `lsusb -t` for the negotiated USB speed.
5. Check kernel logs if enumeration still fails.

## 9. Verify camera detection

```bash
rs-enumerate-devices
```

Before the firmware update, the device reported:

```text
Name                          : Intel RealSense L515
Firmware Version              : 01.04.01.00
Recommended Firmware Version  : 01.05.08.01
Usb Type Descriptor           : 3.2
Product Line                  : L500
```

Enumerated profiles included:

| Stream | Profiles reported |
| --- | --- |
| Depth | 1024×768 at 30 Hz; 640×480 at 30 Hz |
| Confidence | 1024×768 at 30 Hz; 640×480 at 30 Hz |
| Infrared | 1024×768 at 30 Hz; 640×480 at 30 Hz |
| RGB | Up to 1920×1080 at 30 Hz; 1280×720 at 60 Hz |
| Accelerometer | 100, 200, and 400 Hz |
| Gyroscope | 100, 200, and 400 Hz |

These are reported capabilities, not a guarantee that every combination can stream simultaneously.

## 10. Open RealSense Viewer

```bash
realsense-viewer
```

Enable the **L500 depth sensor**.

Verified results:

- Live depth visualization.
- A 3D point cloud.
- Objects changing position in the point cloud when moved in front of the camera.

Use 2D view to inspect individual image pixels and 3D view to examine surface geometry.

## 11. Update the firmware

The installed firmware was 01.04.01.00; the viewer recommended 01.05.08.01.

The update was performed through RealSense Viewer. During the update, it displayed:

```text
Backing-up camera flash memory
Backup completed
Requesting to switch to recovery mode
```

The camera stayed connected, and UTM and Ubuntu remained running until the update completed.

Firmware recovery can cause USB re-enumeration. If the device disappears from the VM, check UTM's USB attachment rather than assuming the camera is broken. Do not interrupt an active flash operation.

## 12. Verify the updated firmware

```bash
rs-enumerate-devices | grep -E "Firmware Version|Recommended Firmware Version"
```

Verified output:

```text
Firmware Version              : 01.05.08.01
Recommended Firmware Version  : 01.05.08.01
```

There is no need to repeat this update when both versions already match.

## 13. Understand the depth image

Each depth pixel contains a measurement of the visible surface's distance along the camera's forward axis (Z depth). The displayed colors visualize these measurements; the colors themselves are not the numeric data.

| Output | Main use |
| --- | --- |
| RGB image | Color, appearance, object identification |
| Depth image | Surface distance and shape |
| RGB aligned with depth | Associate RGB detections with depth measurements |
| Point cloud | Inspect 3D surfaces, obstacles, and geometry |

Raw Z16 depth values convert to meters using:

```text
depth_meters = raw_depth_value × depth_scale
```

Read the scale from the camera SDK rather than assuming one raw unit is one millimeter. A raw depth value of zero means an invalid/missing measurement.

For an object-distance estimate, use a small region near its center, reject invalid pixels, and take the median valid depth. This avoids relying on a single noisy pixel or a pixel at an object boundary.

Depth is not the full straight-line range to an off-center point. To calculate that range, deproject the pixel to a 3D point and compute its Euclidean distance.

## 14. View numeric distance in RealSense Viewer

1. Run `realsense-viewer` inside Ubuntu.
2. Enable the L500 depth sensor.
3. Select **2D** view.
4. Hover the mouse over an object in the depth image.
5. Inspect the pixel/depth readout displayed by the viewer.

Examples of unit conversion:

| Reading in meters | Equivalent |
| --- | --- |
| 0.250 m | 25 cm |
| 0.500 m | 50 cm |
| 0.750 m | 75 cm |
| 1.000 m | 100 cm |

Hover near the center of a flat surface for an easier first test. A zero reading indicates missing depth.

## 15. Troubleshoot the observed 0.5 m near-distance cutoff

**Observed:** the camera seemed unable to measure objects closer than approximately 0.5 m.

**Not yet verified:** whether adjusting the settings resolves this cutoff.

The L515's specified minimum depth range is approximately **0.25 m** under suitable conditions. Near-object performance depends on settings, surface properties, and lighting.

In the L500 depth sensor controls:

1. Select **Short Range** preset, if available. It lowers laser power and receiver gain to reduce receiver saturation on close objects.
2. Inspect **Min Distance**. If it is around **490–500 mm**, try **250 mm**. This is a rejection threshold: depth below it is reported as invalid. Lowering it does not guarantee accurate measurements outside the specified range.
3. If Short Range is unavailable, the older documentation recommends **Low Ambient** for objects closer than 50 cm.
4. Test a matte, flat object at **30–40 cm**, indoors and away from direct sunlight.
5. Hover over the object's center and check the numeric reading.

Confirm that the units shown by the control are millimeters before entering 250. Recheck Min Distance after changing presets, because presets can change other controls.

If the result still cuts off near 50 cm, record the preset, Min Distance, laser power, receiver gain, and depth profile, along with a screenshot of the controls.

## 16. macOS versus Ubuntu/UTM

macOS already detects the camera over USB. That verifies the physical connection; it does not verify native macOS depth streaming.

Native macOS use would require a compatible SDK build and testing on Apple Silicon. It has not been installed or verified in this workflow. The working route is currently:

```text
L515 → UTM USB passthrough → Ubuntu 24.04 → librealsense v2.53.1 → RealSense Viewer
```

## 17. ROS 2 Jazzy integration completed on October 20, 2026

The L515 was connected to Ubuntu 24.04 ARM64 inside UTM on the Mac. ROS wrapper **4.51.1** was built against the existing source-installed **librealsense 2.53.1**. This is a locally patched legacy wrapper, not an officially validated Jazzy/L515 combination.

During this session, the Pixel 7 cable connection reported **USB 2.1**. Depth was therefore tested at **320×240, 30 FPS**; upgrading the cable was deferred.

### 17.1 Install ROS dependencies and download the wrapper

Run in Ubuntu, with ROS 2 Jazzy already installed:

```bash
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y \
  git \
  python3-colcon-common-extensions \
  python3-rosdep \
  ros-jazzy-cv-bridge \
  ros-jazzy-image-transport \
  ros-jazzy-diagnostic-updater \
  ros-jazzy-xacro

mkdir -p ~/l515_ws/src
cd ~/l515_ws/src
git clone --branch 4.51.1 --depth 1 \
  https://github.com/realsenseai/realsense-ros.git

cd ~/l515_ws
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  sudo rosdep init
fi
rosdep update
rosdep install --from-paths src --ignore-src \
  --rosdistro jazzy --skip-keys=librealsense2 -y
```

If the checkout already exists, do not clone again. The skip key preserves the SDK installed in /usr/local; do not install the current RealSense SDK over it.

### 17.2 Apply the four fixes discovered during the session

The initial builds and launch exposed these issues:

| Error | Change |
| --- | --- |
| Unsupported ROS Distribution: jazzy | Allow Jazzy through the wrapper's Humble compilation branch |
| cv_bridge/cv_bridge.h missing | Use cv_bridge/cv_bridge.hpp |
| NodeParametersInterface::OnParametersSetCallbackType missing | Use NodeParametersInterface::OnSetParametersCallbackType |
| No default profile found | Fall back to an available sensor profile when none is SDK-marked as default |

The following consolidates the same changes applied during troubleshooting. It backs up each modified file and can be rerun after these fixes are already present.

```bash
cd ~/l515_ws
python3 - <<'PY'
from pathlib import Path

root = Path("src/realsense-ros/realsense2_camera")

def save(p, original, updated):
    if updated != original:
        backup = p.with_name(p.name + ".before_readme_fixes")
        if not backup.exists():
            backup.write_text(original)
        p.write_text(updated)
        print("Updated:", p)

p = root / "CMakeLists.txt"
text = p.read_text()
old = 'elseif("$ENV{ROS_DISTRO}" STREQUAL "humble")'
new = 'elseif("$ENV{ROS_DISTRO}" STREQUAL "humble" OR "$ENV{ROS_DISTRO}" STREQUAL "jazzy")'
if new not in text and text.count(old) != 1:
    raise SystemExit("Unexpected CMake condition; inspect before editing.")
save(p, text, text.replace(old, new, 1))

for p in root.rglob("*"):
    if p.suffix in {".h", ".hpp", ".cpp"}:
        text = p.read_text()
        updated = text.replace("cv_bridge/cv_bridge.h",
                               "cv_bridge/cv_bridge.hpp")
        updated = updated.replace(
            "NodeParametersInterface::OnParametersSetCallbackType",
            "NodeParametersInterface::OnSetParametersCallbackType")
        save(p, text, updated)

p = root / "src/profile_manager.cpp"
text = p.read_text()
old = '''    if (!(default_profile.get()))
        throw std::runtime_error("No default profile found");'''
new = '''    if (!(default_profile.get()))
    {
        default_profile = _all_profiles.front();

        // Prefer a depth profile when this sensor provides one.
        for (const auto& profile : _all_profiles)
        {
            if (profile.stream_type() == RS2_STREAM_DEPTH &&
                profile.format() == RS2_FORMAT_Z16)
            {
                default_profile = profile;
                break;
            }
        }

        ROS_WARN_STREAM("No SDK default profile marked; using an available "
                        "profile as fallback.");
    }'''
if new not in text and text.count(old) != 1:
    raise SystemExit("Unexpected default-profile code; inspect before editing.")
save(p, text, text.replace(old, new, 1))
PY
```

The fallback does not increase USB capability. It lets initialization continue so the explicit supported profile can be selected. Its warning was observed for the RGB module even with color disabled.

### 17.3 Build

```bash
cd ~/l515_ws
source /opt/ros/jazzy/setup.bash

CMAKE_BUILD_PARALLEL_LEVEL=2 MAKEFLAGS=-j2 \
colcon build \
  --symlink-install \
  --executor sequential \
  --cmake-clean-cache \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -Drealsense2_DIR=/usr/local/lib/cmake/realsense2
```

Verified result:

```text
Summary: 3 packages finished
```

The description package warning that realsense2_DIR was unused was harmless. The launch log subsequently confirmed both the build-time and runtime SDK versions were 2.53.1.

### 17.4 Launch depth only

Close RealSense Viewer before starting ROS. Source the environment in each new terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash

ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true \
  enable_color:=false \
  enable_infra1:=false \
  enable_infra2:=false \
  enable_accel:=false \
  enable_gyro:=false \
  depth_module.profile:=320x240x30 \
  pointcloud.enable:=false
```

Observed startup:

```text
RealSense ROS v4.51.1
Built with LibRealSense v2.53.1
Running with LibRealSense v2.53.1
RealSense Node Is Up!
```

The sensor also opened confidence and infrared profiles. The L515 infrared stream is indexed 0, so disabling infra1/infra2 does not necessarily disable this stream.

In a second sourced terminal:

```bash
ros2 topic hz /camera/depth/image_rect_raw
```

Depth-only streaming was measured at approximately **30.008 Hz for more than one minute**.

### 17.5 Launch an untextured point cloud

Stop the previous launch with Ctrl+C. Run:

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash

ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true \
  enable_color:=false \
  enable_accel:=false \
  enable_gyro:=false \
  depth_module.profile:=320x240x30 \
  pointcloud.enable:=true \
  pointcloud.stream_filter:=0
```

This permits point-cloud generation without an RGB texture stream.

Verified topic names:

| Topic | Type / purpose |
| --- | --- |
| /camera/depth/image_rect_raw | sensor_msgs/msg/Image: depth |
| /camera/depth/camera_info | sensor_msgs/msg/CameraInfo: calibration |
| /camera/depth/color/points | sensor_msgs/msg/PointCloud2: 3D points |
| /camera/confidence/image_rect_raw | Confidence image |
| /camera/infra/image_rect_raw | Infrared image |

These are the observed names for this installation. There is no second /camera in the depth topic path. The cloud topic retains “color” in its name even though RGB is disabled. An /camera/imu topic appeared in discovery, but IMU message streaming was not tested.

Check the cloud:

```bash
ros2 topic list -t | grep camera

timeout --signal=INT --kill-after=2s 15s \
ros2 topic echo /camera/depth/color/points \
  --once --field header \
  --qos-reliability best_effort \
  --qos-durability volatile
```

Observed frame:

```text
frame_id: camera_depth_optical_frame
```

With RViz closed, a roughly 75-second test received about **27 Hz** continuously. Later recovery tests measured approximately **26–28 Hz**. These CLI rates are received-message rates, not a complete latency or reliability benchmark.

## 18. RViz 2 visualization and orientation

### 18.1 Start RViz

Keep the camera launch running, then:

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash
rviz2
```

Add a PointCloud2 display.

| Setting | Value |
| --- | --- |
| Fixed Frame | camera_link for an upright camera-body view |
| PointCloud2 Topic | /camera/depth/color/points |
| Reliability Policy | Best Effort |
| Durability Policy | Volatile |
| History Policy | Keep Last |
| Topic queue Depth | 1 |
| Style | Points |
| Size (Pixels) | 1–3 |
| Decay Time | 0 |
| Global Frame Rate | 10 |

Both Global Status and PointCloud2 Status were observed as OK, and scene geometry was visible.

### 18.2 Why the cloud initially looked sideways

The optical frame convention is X right, Y down, Z forward. The camera body frame normally uses X forward, Y left, Z up.

Using camera_depth_optical_frame as Fixed Frame is useful for an initial TF-independent view of the cloud, but the RViz grid does not then represent the physical floor.

Changing Fixed Frame to camera_link made the scene upright in the tested setup. It still does not establish real mounting height or tilt relative to TurtleBot3.

Check the internal transform if needed:

```bash
ros2 run tf2_ros tf2_echo camera_link camera_depth_optical_frame
```

Do not add a duplicate transform if the driver already publishes it.

Under Views, use Orbit; rotate and zoom to inspect surfaces. Orbit “Distance” controls the virtual viewing distance, not a measured object distance.

### 18.3 Color points by distance instead of height

| PointCloud2 setting | Value |
| --- | --- |
| Color Transformer | AxisColor |
| Axis | Z |
| Use Fixed Frame | Unchecked |
| Autocompute Value Bounds | Checked initially |

With Use Fixed Frame unchecked, the color coordinate is the cloud's optical-frame Z depth. With it checked and camera_link selected, Z instead represents height; this produced horizontal rainbow bands during testing.

For a consistent distance scale, turn off Autocompute Value Bounds and try Min Value 0.25 and Max Value 3.0 (meters). These bounds affect visualization, not sensor range.

Nearer points appeared red/orange and farther points blue/purple in the tested display. Empty regions are missing depth, not measured black surfaces. Auto bounds can shift color meanings as the scene changes.

### 18.4 Add a grayscale depth image

Add an Image display:

| Setting | Value |
| --- | --- |
| Topic | /camera/depth/image_rect_raw |
| Reliability | Best Effort |
| Durability | Volatile |
| Queue Depth | 1 to reduce queued frames |
| Normalize Range | Checked |

The 2D depth image displayed successfully alongside the cloud. In the observed normalized image, farther surfaces were brighter. Normalization changes the brightness scale with the scene; it does not provide a fixed numeric distance legend.

### 18.5 Save and reopen the configuration

Use File → Save Config As. The final screenshot showed this configuration path:

```text
/home/nabil/rviz/rviz2.rviz
```

Press Ctrl+S after changing settings. Reopen that file with:

```bash
rviz2 -d ~/rviz/rviz2.rviz
```

This command assumes the configuration was saved at that path. An earlier screenshot showed a different configuration under ~/rviz2; use whichever file you actually saved.

## 19. Troubleshooting intermittent streaming

### 19.1 QoS durability mismatch

Observed warnings:

```text
requesting incompatible QoS
Last incompatible policy: DURABILITY_QOS_POLICY
```

Setting RViz's PointCloud2 durability to Volatile and reliability to Best Effort resolved the observed mismatch. Uncheck/recheck the display after changing QoS.

The point-cloud publisher was observed as Reliable/Volatile. The depth-image publisher was later observed as Reliable/Transient Local; a Volatile subscriber can still match it. Do not assume all topics share the same publisher QoS.

### 19.2 Distinguish a viewer freeze from loss of messages

Leave the camera driver running and check in another sourced terminal:

```bash
timeout --signal=INT --kill-after=2s 15s \
ros2 topic hz /camera/depth/image_rect_raw

timeout --signal=INT --kill-after=2s 15s \
ros2 topic echo /camera/depth/color/points \
  --once --field header \
  --qos-reliability best_effort \
  --qos-durability volatile
```

Let the commands finish. Timeout with no output means no message was received during that check; it does not identify the cause.

- Depth and cloud arrive while RViz freezes: investigate rendering or resource load.
- Depth arrives but cloud does not: investigate cloud processing/publication or delivery.
- Neither arrives: investigate acquisition, the driver, or ROS transport.
- Changing Fixed Frame only changes RViz visualization; it cannot remove a ROS topic.

### 19.3 A live process does not guarantee frames

Diagnostics used:

```bash
pgrep -af realsense2_camera_node
ros2 node list
ros2 topic info /camera/depth/image_rect_raw --verbose
ros2 topic info /camera/depth/color/points --verbose
sudo dmesg | tail -60
```

During a stall, the camera process, node, and publisher remained discoverable, but CLI checks received neither depth nor point-cloud messages.

Subscription count zero after a CLI subscriber exits is expected; it does not by itself identify a fault.

### 19.4 USB error and recovery

A kernel log contained:

```text
uvcvideo 5-1:1.1: Failed to resubmit video URB (-1).
```

This is a USB video-transfer submission error, but its timestamp was not conclusively correlated with the current stall. The root cause remains unresolved.

Recovery used during the session:

1. Stop the ROS camera driver.
2. Close RViz and RealSense Viewer.
3. Restart/reconnect the camera, reattaching through UTM if necessary.
4. Relaunch ROS with the tested 320×240 profile.
5. Verify message reception before opening RViz.

Restarting restored the cloud at approximately 26–28 Hz. Repeated recovery is not proof of long-term reliability.

To monitor fresh errors during another test:

```bash
sudo dmesg --follow --human
```

### 19.5 USB 2 cable and UTM considerations

The session used a Pixel 7 USB cable and reported USB Type Descriptor 2.1. USB 2 successfully streamed the reduced profile, so speed alone was not proven to cause the stalls.

Cable quality, hub behavior, VM passthrough, SDK/driver behavior, processing load, and ROS transport remain possible contributors. A useful next test is a USB 3 data cable rated for at least 5 Gbps, connected directly if possible. Verify 5000M using lsusb -t, then repeat the same low-resolution test before increasing load.

### 19.6 Hardware-clock warning

```text
frame's time domain is HARDWARE_CLOCK. Timestamps may reset periodically.
```

This warning appeared while streaming both worked and stalled. It does not by itself diagnose a USB or RViz failure. Timestamp consistency and TF timing still need validation before robot integration.

## 20. Current result and remaining Nav2 work

Verified on October 20, 2026:

- Patched ROS wrapper 4.51.1 built successfully on Jazzy.
- Driver used SDK 2.53.1 at build time and runtime.
- Depth at 320×240 streamed at about 30 Hz.
- Untextured PointCloud2 was generated and received.
- RViz showed the point cloud and grayscale depth image.
- camera_link provided the upright camera-body frame.
- Distance coloring worked with optical Z and Use Fixed Frame unchecked.

Not yet completed:

- Resolve recurring stream interruptions and verify longer-term stability.
- Verify ROS RGB/IMU streaming if needed.
- Install and test this setup on the TurtleBot3 Raspberry Pi.
- Mount the camera and measure its translation/rotation relative to the robot.
- Connect camera_link to the robot TF tree without duplicate transforms.
- Validate timestamps between the robot and camera host.
- Add filtered camera observations to Nav2's local costmap alongside LiDAR.
- Verify floor rejection, obstacle marking/clearing, blind zones, and latency.

**Nav2 integration has not been completed.** A visible cloud in RViz is an important milestone, but does not yet mean Nav2 uses it for obstacle avoidance.

## 21. Daily startup

Attach the camera to Ubuntu in UTM. Keep RealSense Viewer closed.

Terminal 1:

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash
ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true \
  enable_color:=false \
  enable_accel:=false \
  enable_gyro:=false \
  depth_module.profile:=320x240x30 \
  pointcloud.enable:=true \
  pointcloud.stream_filter:=0
```

Terminal 2:

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash
rviz2 -d ~/rviz/rviz2.rviz
```

Optional monitoring terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash
ros2 topic hz /camera/depth/color/points --window 100
```

Stop the driver with Ctrl+C when finished.



## References

- [Official librealsense repository](https://github.com/realsenseai/librealsense)
- [SDK v2.53.1 source](https://github.com/realsenseai/librealsense/tree/v2.53.1)
- [SDK v2.55.1 release discussion: removal of L515 support](https://github.com/realsenseai/librealsense/discussions/12871)
- [L515 datasheet](https://realsenseai.com/wp-content/uploads/2025/06/Intel_RealSense_LiDAR_L515_Datasheet_Rev003.pdf)
- [L515 user guide and controls](https://www.realsenseai.com/download/13061/)
- [Optimizing L515 range and Short Range preset](https://www.realsenseai.com/news-insights/optimizing-the-lidar-camera-l515-range/)
- [SDK projection mathematics and depth units](https://github.com/realsenseai/librealsense/wiki/Projection-in-RealSense-SDK-2.0)
- [RealSense Viewer hover-depth discussion](https://github.com/realsenseai/librealsense/issues/6104)
- [Official RealSense ROS wrapper](https://github.com/realsenseai/realsense-ros)

