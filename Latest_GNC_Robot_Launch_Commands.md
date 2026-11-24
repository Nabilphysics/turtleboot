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

### Optional · Enable the OpenCR buzzer with the red LED

On UTM, stop the detection viewer with `Ctrl+C` and open its launch file:

```bash
nano "$HOME/gnc_robot_ros/navigation_only/detection_viewer.launch.py"
```

In the `human_led_alert_gate` node's parameter dictionary, change `'sound_enabled': False` to `'sound_enabled': True`. Add the parameter if it is missing.

Save the file and rerun the UTM detection viewer command above. Keep the Pi's robot bringup and RealSense + LED launch running. The launch-file edit takes effect on restart without a `colcon build`.

The built-in OpenCR buzzer requests one beep when the gate enters the red STOP state. The red LED can continue flashing while the state remains active.

## 3. Connect the Pi to 5 GHz

1. On the Pixel, open **Settings → Network & internet → Hotspot & tethering → Wi‑Fi hotspot → Speed & compatibility**. Select **5 GHz** if offered. If there is an **Extend compatibility** switch, turn it off. Toggle the hotspot off and on and let the Pi reconnect to `gncboot`.
2. On the Pi, run `iw dev wlan0 link`. A frequency in the **5xxx MHz** range confirms 5 GHz. The tested connection showed **5785 MHz**. A frequency in the **24xx MHz** range means 2.4 GHz.
3. If the Pixel only offers **2.4 and 5 GHz** together and the Pi keeps choosing 2.4 GHz, run the block below from a **local Pi terminal**. Reassociation can interrupt SSH.

```bash
net_id=$(sudo wpa_cli -i wlan0 list_networks |
  awk -F '\t' '$2 == "gncboot" && $4 ~ /\[CURRENT\]/ {print $1; exit}')

if [ -n "$net_id" ]; then
  sudo wpa_cli -i wlan0 set_network "$net_id" freq_list \
    '5180 5200 5220 5240 5745 5765 5785 5805 5825' &&
    sudo wpa_cli -i wlan0 reassociate
else
  echo "Connect wlan0 to gncboot first."
fi
```

After a few seconds, verify again with `iw dev wlan0 link`. This restricts the Pi to the listed 5 GHz channels, including the previously tested 5785 MHz. The hotspot needs to offer one of those channels. The change is temporary and is cleared when the Pi reboots. See [GNC_Network_Speed_Testing.md](GNC_Network_Speed_Testing.md) for throughput and live traffic tests.

## 4. Standalone human detection and stop demonstration using keyboard teleop

Keep Nav2 and mapping stopped during this demo. Stop any ordinary teleop session. Use five terminals and start them in the order below. If either Pi launch is already running, keep that instance.

### Raspberry Pi Terminal 1 · Robot bringup and watchdog

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/turtlebot3_ws/install/setup.bash"
source "$HOME/gnc_robot_ros/install/local_setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch gnc_bringup robot.launch.py mode:=mapping \
  usb_port:=/dev/serial/by-id/usb-ROBOTIS_OpenCR_Virtual_ComPort_in_FS_Mode_FFFFFFFEFFFF-if00
```

### Raspberry Pi Terminal 2 · RealSense and LED

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/gnc_robot_ros/install/setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch "$HOME/gnc_robot_ros/camera_led.launch.py"
```

### UTM Terminal 1 · Human detection viewer

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/gnc_robot_ros/install/setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export GNC_ROOT="$HOME/gnc_robot_ros"
ros2 launch "$GNC_ROOT/navigation_only/detection_viewer.launch.py"
```

### UTM Terminal 2 · Human teleop velocity gate

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/gnc_robot_ros/install/setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 run gnc_human_detection velocity_gate --ros-args \
  -r __node:=human_teleop_gate \
  -p output_topic:=/gnc/velocity_requested \
  -p command_timeout:=0.3 \
  -p sound_enabled:=false
```

### UTM Terminal 3 · Remapped keyboard teleop

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/gnc_robot_ros/install/setup.bash"
export ROS_DOMAIN_ID=30 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_teleop teleop_keyboard --ros-args \
  -p enable_stamped_cmd_vel:=true \
  -r cmd_vel:=/cmd_vel_teleop
```

Keyboard velocity commands go through the human teleop gate and the Pi watchdog. The detection viewer supplies person-distance status and drives the LED alert gate. For buzzer alerts, use the optional setting in Section 2.

Verify stopping with the wheels lifted before a floor demonstration. Check that a valid person distance within 1 m, and missing or invalid perception, result in zero velocity. Press Space or S to stop manually. Keep a physical stop available.

Before returning to Nav2, stop the keyboard teleop and human teleop gate with Ctrl+C. This prevents competing publishers on the watchdog input.
