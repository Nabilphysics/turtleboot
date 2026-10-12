# Intel RealSense L515 Camera Setup
## Ubuntu 24.04 in UTM on a MacBook Air

This README records the completed installation, USB troubleshooting, firmware update, and depth viewing workflow. Close-range adjustments are suggested troubleshooting steps; their success has not yet been confirmed. ROS 2 Jazzy and RViz 2 integration is the next stage and has not been completed.

## 1. Setup and verified status

| Component | Configuration / status |
| --- | --- |
| Host | MacBook Air, Apple Silicon |
| USB connection | UGREEN Revodok USB hub; macOS reported 5 Gbps after reconnecting |
| Virtual machine | Ubuntu 24.04 ARM64 inside UTM |
| Camera | Intel RealSense L515 |
| SDK | librealsense v2.53.1, built from source |
| Firmware | Updated from 01.04.01.00 to 01.05.08.01 |
| Working | Camera enumeration, depth visualization, 3D point cloud |
| Capabilities detected | RGB, accelerometer, gyroscope |
| Pending | ROS 2 topics, RViz 2, TurtleBot3 / Nav2 integration |

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

## 17. Next stage: ROS 2 Jazzy and RViz 2

Planned workflow:

```text
L515 → compatible RealSense ROS wrapper → ROS 2 Jazzy topics → RViz 2
```

Planned outputs include RGB, depth, camera calibration, IMU, and point cloud topics.

Before installing the wrapper:

- Select a wrapper version compatible with the older L515-capable SDK.
- Verify that it can build with ROS 2 Jazzy; older wrappers predate Jazzy.
- Avoid installing conflicting librealsense versions over the working source installation.
- Close RealSense Viewer before starting a ROS driver that needs the same camera.

ROS wrapper installation, topic publication, RViz visualization, and TurtleBot3/Nav2 integration remain pending. No ROS launch command is documented here as tested.

## 18. Quick commands

### macOS: USB link check

```bash
ioreg -p IOUSB -l -w 0 | grep -A35 -i "RealSense"
```

### Ubuntu: camera checks

```bash
lsusb
lsusb -t
rs-enumerate-devices
rs-enumerate-devices | grep -E "Firmware Version|Recommended Firmware Version"
```

### Ubuntu: visualization

```bash
realsense-viewer
```

### Ubuntu: driver diagnostics

```bash
ls -l /dev/video*
lsmod | grep uvcvideo
sudo dmesg | grep -i -E "realsense|uvc|video|8086|0b64" | tail -100
```

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

