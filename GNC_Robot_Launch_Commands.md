## 1. Mapping

Stop UTM navigation before starting mapping. If Raspberry Pi bringup is already running, leave it running and skip the first command. For LiDAR-only mapping, you can skip RealSense.

### Raspberry Pi Terminal 1 · Robot bringup

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/turtlebot3_ws/install/setup.bash"
source "$HOME/gnc_robot_ros/install/local_setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch gnc_bringup robot.launch.py mode:=mapping \
  usb_port:=/dev/serial/by-id/usb-ROBOTIS_OpenCR_Virtual_ComPort_in_FS_Mode_FFFFFFFEFFFF-if00
```

### UTM Terminal 1 · Start mapping

This opens RViz and a keyboard teleop window. Drive the robot with teleop to build the map.

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/gnc_robot_ros/install/setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export TURTLEBOT3_MODEL=burger
ros2 launch gnc_bringup mapping.launch.py
```

### UTM Terminal 2 · Save the map

Keep mapping running while you save. Change `lab_map` to the name you want, without a file extension. Use a new name to keep your existing maps.

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/gnc_robot_ros/install/setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
map_name=lab_map
mkdir -p "$HOME/gnc_robot_ros/maps"
ros2 run nav2_map_server map_saver_cli \
  -f "$HOME/gnc_robot_ros/maps/$map_name" \
  --ros-args -p save_map_timeout:=10.0
```

Wait for the save to succeed before stopping mapping with `Ctrl+C`. Keep the saved `.yaml` file and its companion image together.

## 2. Navigation

Stop UTM mapping before starting navigation. Keep Raspberry Pi robot bringup running using the command from Section 1.

### Raspberry Pi Terminal 2 · RealSense and LED

Run this in a separate Pi terminal to start the L515 camera driver and LED node.

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/gnc_robot_ros/install/setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch "$HOME/gnc_robot_ros/camera_led.launch.py"
```

### UTM Terminal 1 · Start navigation

Your launcher requires `map:=`. This command uses your existing `home_room_map.yaml`. To use a map saved in Section 1, change the filename to `lab_map.yaml` or the name you chose.

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/gnc_robot_ros/install/setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export GNC_ROOT="$HOME/gnc_robot_ros"
ros2 launch "$GNC_ROOT/navigation_only/navigation_split.launch.py" \
  map:="$GNC_ROOT/maps/home_room_map.yaml"
```

Once the map appears in RViz, use **2D Pose Estimate** to set the robot’s actual position and heading. Wait for Nav2 to activate before sending a goal.

### UTM Terminal 2 · Detection viewer

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/gnc_robot_ros/install/setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export GNC_ROOT="$HOME/gnc_robot_ros"
ros2 launch "$HOME/gnc_robot_ros/navigation_only/detection_viewer.launch.py"
```
