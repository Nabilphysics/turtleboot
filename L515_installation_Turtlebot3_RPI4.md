# L515 on TurtleBot3 Raspberry Pi 4

Session record: November 8, 2026. Prepared with ChatGPT from our installation and troubleshooting session.

Tested setup: TurtleBot3 Burger, Raspberry Pi 4 (2 GB RAM), Ubuntu 24.04 ARM64, ROS 2 Jazzy, L515 firmware **01.05.08.01**, librealsense **2.53.1**, ROS wrapper **4.51.1**. This is a legacy, locally patched combination, not an assertion of official Jazzy support.

## Start the camera first

SSH from the computer to the Pi:

```bash
ssh ubuntu@gncrpi.local
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

Keep this terminal running. Run only one camera driver. Alignment is performed on the UTM computer for human detection; see the companion guide. These commands do not start TurtleBot3 base bringup or Nav2.

## 1. Connect and check USB

Use a USB 3 data cable and a blue Pi USB port. Our final working connection used the factory cable.

```bash
lsusb
lsusb -t
```

Look for `8086:0b64` and **5000M** on the camera interfaces. A blue port alone does not prove USB 3 negotiation. Our earlier 480M connection exposed only 320×240 depth. Provide adequate power; USB storage and the camera also share Pi USB resources.

## 2. Build the legacy SDK on the Pi

ROS 2 Jazzy must already be installed. Our Pi had a 2 GB swapfile; use a single build job on this 2 GB model.

```bash
sudo apt update
sudo apt install -y git cmake build-essential pkg-config \
  libusb-1.0-0-dev libudev-dev libssl-dev
cd ~
git clone --branch v2.53.1 --depth 1 https://github.com/realsenseai/librealsense.git
cd ~/librealsense
sudo ./scripts/setup_udev_rules.sh
```

Disconnect the camera when the udev script asks; reconnect after rules are installed. Configure a headless build:

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release -DFORCE_RSUSB_BACKEND=ON \
  -DBUILD_EXAMPLES=OFF -DBUILD_TOOLS=ON \
  -DBUILD_GRAPHICAL_EXAMPLES=OFF -DBUILD_UNIT_TESTS=OFF \
  -DBUILD_PYTHON_BINDINGS=OFF
cmake --build build --parallel 1
sudo cmake --install build
sudo ldconfig
rs-enumerate-devices
```

`BUILD_EXAMPLES=OFF` avoids the GLFW/X11 configuration failure encountered with the earlier headless build. Deprecation warnings from old Boost code were not build failures. Confirm the L515, firmware, and USB descriptor; our final descriptor was **3.2**. No further firmware update was needed.

## 3. Build the ROS wrapper

```bash
sudo apt install -y python3-colcon-common-extensions python3-rosdep
source /opt/ros/jazzy/setup.bash
mkdir -p ~/l515_ws/src
cd ~/l515_ws/src
git clone --branch 4.51.1 --depth 1 https://github.com/realsenseai/realsense-ros.git
```

Apply the compatibility edits we needed. This block is for a fresh 4.51.1 checkout and backs up changed files:

```bash
python3 - <<'PY'
from pathlib import Path
root = Path.home() / 'l515_ws/src/realsense-ros/realsense2_camera'
for p in [root/'CMakeLists.txt', *root.rglob('*.h'), *root.rglob('*.cpp')]:
    original = p.read_text()
    text = original.replace(
        'elseif("$ENV{ROS_DISTRO}" STREQUAL "humble")',
        'elseif("$ENV{ROS_DISTRO}" STREQUAL "humble" OR "$ENV{ROS_DISTRO}" STREQUAL "jazzy")')
    text = text.replace('cv_bridge/cv_bridge.h>', 'cv_bridge/cv_bridge.hpp>')
    text = text.replace('OnParametersSetCallbackType', 'OnSetParametersCallbackType')
    if p.name == 'profile_manager.cpp':
        old = 'throw std::runtime_error("No default profile found");'
        new = '''{
        default_profile = _all_profiles.front();
        for (const auto& candidate : _all_profiles)
        {
            if (candidate.stream_type() == RS2_STREAM_DEPTH &&
                candidate.format() == RS2_FORMAT_Z16)
            {
                default_profile = candidate;
                break;
            }
        }
        ROS_WARN_STREAM("No SDK default profile marked; using an available profile as fallback.");
    }'''
        text = text.replace(old, new)
    if text != original:
        backup = p.with_name(p.name + '.before_jazzy')
        if not backup.exists():
            backup.write_text(original)
        p.write_text(text)
print('Compatibility edits applied. Review with git diff before building.')
PY
cd ~/l515_ws/src/realsense-ros
git diff
```

The fallback preserves the existing empty-profile guard. It handles the SDK reporting profiles without a default flag; the explicit launch profiles still select the desired resolution.

```bash
cd ~/l515_ws
# Run sudo rosdep init only if rosdep has never been initialized.
rosdep update
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy \
  --skip-keys librealsense2
export CMAKE_BUILD_PARALLEL_LEVEL=1
colcon build --symlink-install --executor sequential \
  --cmake-args -DCMAKE_BUILD_TYPE=Release \
  -Drealsense2_DIR=/usr/local/lib/cmake/realsense2 \
  --parallel-workers 1
```

If compilation runs out of memory, repeat with `CMAKE_BUILD_PARALLEL_LEVEL=1` prefixed to `colcon build`. Sequential package execution alone does not limit compiler jobs inside a package. For this Pi, setting `export CMAKE_BUILD_PARALLEL_LEVEL=1` before the first build is recommended.

## 4. Verify

Start the camera using the first section. In another Pi terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/l515_ws/install/setup.bash
export ROS_DOMAIN_ID=30
ros2 topic list -t | grep camera
ros2 topic hz /camera/depth/image_rect_raw --window 30
# Ctrl+C, then:
ros2 topic hz /camera/color/image_raw --window 30
```

We measured approximately **30 Hz depth** and **15 Hz RGB**. Stop rate checks after testing to reduce traffic. On UTM, source Jazzy and set the same domain to discover the topics; both devices must have ROS connectivity through the network.

## Working decisions and limits

- Keep SDK alignment and point clouds off for the human-distance baseline. Pi SDK alignment produced alternating depth image sizes and USB watchdog warnings during our tests.
- Persistent watchdog errors indicate a stream problem even if the node still exists. Stop the driver, check processes and USB, reconnect if necessary, and restart. USB 3 enumeration does not prove uninterrupted streaming.
- For RViz PointCloud2, when enabled separately, use `/camera/depth/color/points`, Best Effort, Volatile, and `camera_link` as a standalone fixed frame.
- Camera mounting in the TurtleBot3 URDF and a measured base-to-camera transform, followed by Nav2 costmap configuration, remain separate work. This guide installs and streams the camera; it does not complete Nav2 integration.
