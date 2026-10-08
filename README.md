# TurtleBot3 setup and team repeat procedure

> Updated working notes for TurtleBot3 Burger + Raspberry Pi 4 + ROS 2 Jazzy + LDS-02 + Nav2.

Progress record • Updated October 8, 2026 • Syed Razwanul Haque

Our TurtleBot3 Burger now runs ROS 2 Jazzy with working official keyboard teleoperation, LiDAR/odometry/TF, SLAM mapping, saved-map AMCL localization, and Nav2 goal navigation from UTM. The current TurtleBot3 /cmd_vel subscriber uses geometry_msgs/msg/TwistStamped. A custom Nav2 parameter file is used so the controller, behaviors, velocity smoother, and collision monitor also use stamped velocity commands. The current repeat procedure and full Nav2 parameter file are recorded below.

# 1 PC setup

I installed ROS 2 Jazzy in Ubuntu 24.04 on UTM on my MacBook and confirmed it works. The UTM Ubuntu username is nabil. Its password is not recorded here. I confirmed that its Ubuntu sources include noble, noble-updates, noble-backports, and noble-security.

# 2 Raspberry Pi setup

My robot is a ROBOTIS TurtleBot3 Burger with a Raspberry Pi 4 Model B with 2 GB RAM, an LDS-02 LiDAR, and an OpenCR 1.0 controller. I flashed Ubuntu Server 24.04 LTS, 64-bit, onto the microSD card using Raspberry Pi Imager and booted the Pi without a monitor, keyboard, or mouse.

The Mac and Pi were connected to the same phone hotspot. The recorded IP is a DHCP address and can change after reconnecting.

# 3 Discovering the IP address

My first SSH attempt to gncrpi.local failed because the hostname could not be resolved. I then checked the network from macOS Terminal, outside UTM. The macOS command networksetup does not run inside Ubuntu.

```bash
networksetup -listallhardwareports
arp -a
```

The Wi-Fi interface was en0. Entries on bridge100 in the 192.168.64.x range belonged to the UTM network. I checked the Mac Wi-Fi address, subnet mask, and gateway:

```bash
ipconfig getifaddr en0
ipconfig getoption en0 subnet_mask
ipconfig getoption en0 router
networksetup -getairportnetwork en0
```

The AirPort command reported that no network was associated, so that message alone was not used to decide whether Wi-Fi was connected. I probed the subnet and inspected the ARP entries:

```bash
for i in {1..254}; do
  ping -c 1 -W 1000 "10.91.215.$i" >/dev/null 2>&1 &
done
wait
arp -a | grep '10\.91\.215\.'
```

This produced many background-job messages and incomplete ARP entries. A new resolved entry appeared for 10.91.215.239 with MAC address e4:5f:1:b7:83:71. I tested SSH to that address:

```bash
ssh -o ConnectTimeout=10 ubuntu@10.91.215.239
```

I accepted the first-connection host-key prompt and entered the password ubuntu. The successful login prompt was ubuntu@gncrpi:~$, confirming the device identity. The welcome message confirmed Ubuntu 24.04.5 LTS on ARM64 and wlan0 IP 10.91.215.239.

# 4 Preparing the Pi for ROS 2

I followed the ROBOTIS SBC setup instructions. Wi-Fi was already working, so I kept the existing network configuration. I disabled periodic apt updates and unattended upgrades in /etc/apt/apt.conf.d/20auto-upgrades:

APT::Periodic::Update-Package-Lists "0";
APT::Periodic::Unattended-Upgrade "0";

I masked the network startup wait and sleep targets, then rebooted. Updates can still be run manually.

```bash
sudo systemctl mask systemd-networkd-wait-online.service
sudo systemctl mask sleep.target suspend.target \
  hibernate.target hybrid-sleep.target
sudo reboot
```

For the 2 GB Pi, I checked that no swapfile existed and created a 2 GB swapfile:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
swapon --show
free -h
```

Verified result: /swapfile was active with 2.0 GiB of swap and 0 B used. The fstab entry makes it persistent across reboots; it should be added only once.

# 5 Installing Jazzy on the Pi

I installed ros2-apt-source using the official Jazzy guide to configure the ROS repository and signing key. The Pi initially had only Suites: noble in its main Ubuntu source. I edited /etc/apt/sources.list.d/ubuntu.sources to add the update suites, while keeping noble-security unchanged:

Suites: noble noble-updates noble-backports
Suites: noble-security

I updated Ubuntu, followed the development tools installation step, and installed ROS Base:

```bash
sudo apt clean && sudo apt update && sudo apt full-upgrade -y
sudo apt install -y ros-dev-tools
sudo apt install -y ros-jazzy-ros-base
```

I sourced Jazzy and added the source line to ~/.bashrc so new interactive SSH sessions load it automatically:

```bash
grep -qxF 'source /opt/ros/jazzy/setup.bash' ~/.bashrc ||
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
source ~/.bashrc
echo "$ROS_DISTRO"
ros2 --help
```

Verified result: ROS_DISTRO printed jazzy and ros2 --help displayed the command list. The demo talker reported demo_nodes_cpp not found because the demo package was not installed; this did not prevent the ROS environment from working.

# 6 Enabling hostname access

Inside the Pi SSH session, I installed and enabled Avahi to advertise the hostname on the local network:

```bash
sudo apt update &&
sudo apt install -y avahi-daemon &&
sudo systemctl enable --now avahi-daemon
```

Installation initially waited because process 1421, unattended-upgr, held the package-manager lock. I allowed the automatic updater to finish. The lock cleared and Avahi and its dependencies installed successfully.

Ubuntu reported a pending kernel update from 6.8.0-1064-raspi to 6.8.0-1065-raspi. I rebooted after enabling Avahi. The SSH connection closed during the restart.

```bash
sudo systemctl enable --now avahi-daemon &&
sudo reboot
```

# 7 Connecting from macOS by name

After restarting, I ran this command in macOS Terminal:

```bash
ssh -o ConnectTimeout=10 ubuntu@gncrpi.local
```

The hostname resolved to the Pi at fe80::e65f:1ff:feb7:8371%en0. SSH showed the same ED25519 fingerprint as the earlier numeric-IP connection. I accepted the hostname prompt and reached the password prompt. This confirms hostname discovery and SSH reachability.

For future connections, connect the Mac and Pi to the same network, run the command above, and enter the Pi password. ConnectTimeout=10 limits the connection attempt to 10 seconds. Password characters are not shown while typing.

If hostname discovery fails on a different network, find the Pi IP again and connect directly. Do not assume that 10.91.215.239 remains its address.

# 8 Connecting from UTM Ubuntu

I first connected from a terminal inside UTM Ubuntu using the Pi IP:

```bash
ssh -o ConnectTimeout=10 ubuntu@10.91.215.239
```

For a short name, the UTM SSH configuration method is to open ~/.ssh/config as the local UTM user nabil and add:

Host gncrpi
    HostName 10.91.215.239
    User ubuntu
    ConnectTimeout 10

Connect with ssh gncrpi. This alias uses the recorded IP; update HostName if it changes. Try gncrpi.local only if local hostname discovery works through UTM.

After connecting, the prompt becomes ubuntu@gncrpi:~$ and commands run on the Pi. ROS communication and keyboard teleoperation from UTM were subsequently brought into operation; see sections 14 to 17.

# 9 TurtleBot3 packages on the Pi

I followed the official Jazzy SBC commands in the Pi SSH session. I installed the dependencies:

```bash
sudo apt install python3-argcomplete python3-colcon-common-extensions libboost-system-dev build-essential
sudo apt install ros-jazzy-hls-lfcd-lds-driver
sudo apt install ros-jazzy-turtlebot3-msgs
sudo apt install ros-jazzy-dynamixel-sdk
sudo apt install ros-jazzy-xacro
sudo apt install libudev-dev
```

I created the workspace and used the Jazzy branches of the official repositories. ld08_driver is the driver for my LDS-02.

```bash
mkdir -p ~/turtlebot3_ws/src && cd ~/turtlebot3_ws/src
git clone -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3.git
git clone -b jazzy https://github.com/ROBOTIS-GIT/ld08_driver.git
git clone -b jazzy https://github.com/ROBOTIS-GIT/coin_d4_driver
cd ~/turtlebot3_ws/src/turtlebot3
rm -r turtlebot3_cartographer turtlebot3_navigation2
cd ~/turtlebot3_ws/
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
source ~/.bashrc
colcon build --symlink-install --parallel-workers 1
echo 'source ~/turtlebot3_ws/install/setup.bash' >> ~/.bashrc
source ~/.bashrc
```

The build used one worker for the 2 GB Pi. I proceeded to the USB and firmware setup afterward; a final build summary was not recorded in these notes. Mapping and navigation packages were removed from this Pi workspace as instructed in the official SBC guide.

# 10 USB rules and environment settings

I followed the USB rule installation commands for OpenCR:

```bash
sudo cp `ros2 pkg prefix turtlebot3_bringup`/share/turtlebot3_bringup/script/99-turtlebot3-cdc.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

I configured ROS domain 30 and selected only LDS-02, then reloaded the saved settings:

```bash
echo 'export ROS_DOMAIN_ID=30 #TURTLEBOT3' >> ~/.bashrc
source ~/.bashrc
echo 'export LDS_MODEL=LDS-02' >> ~/.bashrc
source ~/.bashrc
```

The UTM environment must also use ROS_DOMAIN_ID=30 for future ROS communication tests. Do not add the LDS-01 or LDS-03 settings for this robot.

# 11 OpenCR firmware setup

On the Pi, I enabled 32-bit ARM support for the official firmware uploader, selected the Burger model, and downloaded the ROS 2 firmware:

```bash
sudo dpkg --add-architecture armhf
sudo apt-get update
sudo apt-get install libc6:armhf
export OPENCR_PORT=/dev/ttyACM0
export OPENCR_MODEL=burger
rm -rf ./opencr_update.tar.bz2
wget https://github.com/ROBOTIS-GIT/OpenCR-Binaries/raw/master/turtlebot3/ROS2/latest/opencr_update.tar.bz2
tar -xvf opencr_update.tar.bz2
cd ./opencr_update
./update.sh $OPENCR_PORT $OPENCR_MODEL.opencr
```

The archive was downloaded and extracted from ~/turtlebot3_ws. The uploader ran from ~/turtlebot3_ws/opencr_update with OpenCR connected to the Pi by USB.

The upload succeeded. The terminal output confirmed:

file name: burger.opencr
file size: 136 KB
fw_name: burger
fw_ver: V230127R1
Board Name: OpenCR R1.0
[OK] Open port: /dev/ttyACM0
[OK] flash_erase
[OK] flash_write
[OK] CRC Check: D92222 D92222
[OK] Download
[OK] jump_to_fw

The matching CRC values confirm that firmware verification passed. jump_to_fw confirms that the uploader instructed OpenCR to start the firmware.

# 12 OpenCR motor test

PUSH SW 1 was tested and confirmed to move the robot forward correctly. The individual PUSH SW 2 rotation result has not been explicitly recorded.

Test procedure: turn on OpenCR power, check the red Power LED, and place the robot on a flat floor with a 1 meter clear radius. Hold PUSH SW 1 for a few seconds for 30 cm forward motion. After it stops, hold PUSH SW 2 for a few seconds for a 180 degree turn. Keep power cables clear of the wheels.

# 13 Current status and next tasks

Working: Pi Ubuntu and Jazzy, 2 GB swap, OpenCR upload, forward motor test, SSH, bridged UTM networking, and low-speed keyboard teleop. Next: sensor and TF checks, mapping, and Nav2.

UTM changed from 192.168.64.3 to bridged 10.91.215.248; the Pi stayed at 10.91.215.239. Teleop works. The original talker/listener demo and full topic list have not been reverified.

# 14 UTM networking and ROS discovery

UTM SSH using gncrpi.local failed with Name or service not known. SSH using the Pi IP worked, so hostname resolution was the immediate SSH problem. Use numeric-IP SSH from UTM for the repeat procedure; macOS hostname access remains available.

```bash
ssh -o ConnectTimeout=10 ubuntu@10.91.215.239
```

UTM initially showed only /parameter_events and /rosout. Its domain was already 30 and its discovery range was SUBNET. The VM address was 192.168.64.3/24 on enp0s1.

I shut down Ubuntu, opened the VM settings in UTM, changed Network Mode from Shared to Bridged (macOS Bridged on some versions), selected Wi-Fi en0, saved, and restarted Ubuntu. The Mac and robot remained on the gncboot hotspot.

```bash
sudo poweroff
```

After restarting, ip -br addr confirmed enp0s1 had 10.91.215.248/24. The Pi remained at 10.91.215.239. These are observed DHCP addresses, not fixed reservations; check them after reconnecting.

On the local UTM terminal, I loaded Jazzy and set domain 30. The persistent domain setting had also been added to ~/.bashrc.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=30
ros2 daemon stop
ros2 topic list
ip -br addr
printenv | grep -E 'ROS_|RMW_'
```

The first topic check after bridging still showed only the two default topics. Later keyboard teleoperation worked. Therefore, bridging alone was not recorded as immediately completing discovery, and there is no saved full topic-list output.

# 15 Robot bringup and Twist compatibility

On the Pi, I launched the Burger hardware nodes and kept that terminal open:

```bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_bringup robot.launch.py
```

Earlier setup: generic teleop published Twist, so bringup used enable_stamped_cmd_vel: false. This was later replaced by true for official TurtleBot3 teleop. The current repeat configuration is in section 22.

```bash
nano "$(ros2 pkg prefix turtlebot3_bringup)/share/turtlebot3_bringup/param/burger.yaml"
```

enable_stamped_cmd_vel: false  # historical generic teleop setup

Preserve YAML indentation. Save with Ctrl+O, Enter, then exit with Ctrl+X and restart bringup. The editing command was provided during setup; a separate parameter readback was not recorded. Verify the active subscriber type before repeating teleop.

# 16 Working teleoperation and speed correction

Keyboard teleop published /cmd_vel as geometry_msgs/msg/Twist. The captured forward command had linear.x: 0.5 and angular.z: 0.0. The robot turned rather than driving straight. PUSH SW 1 moved it forward correctly, helping rule out a basic inability of the wheels to drive forward.

I reduced the teleop speed and confirmed that keyboard teleoperation then worked. The exact final working speed and original teleop launch command were not recorded. Use 0.05 m/s as a conservative starting value for repeat tests, not as a measured final setting.

Historical alternative: teleop_twist_keyboard was used as a repeat example. The team now uses official TurtleBot3 teleop with TwistStamped. The command below requires the old false setting; do not use it with the current true setting.

```bash
sudo apt install ros-jazzy-teleop-twist-keyboard
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=30
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -p speed:=0.05 -p turn:=0.3 -p stamped:=false
```

Focus teleop: i moves forward, j and l rotate, k stops. Use a clear floor and stop before exiting. TurtleBot3 teleop uses different keys and may use a different message type; check compatibility before substituting.

The robot subscriber and teleop publisher must both use geometry_msgs/msg/Twist in this configuration. Inspect the endpoints from UTM or a second Pi SSH terminal:

```bash
ros2 topic info /cmd_vel -v
ros2 topic echo /cmd_vel geometry_msgs/msg/Twist
```

Stop the echo command with Ctrl+C after checking. The echo command only observes messages; it does not drive the robot.

# 17 Repeat the session with the team

1. Power the TurtleBot and connect the Mac and Pi to gncboot. Start UTM with Bridged networking through en0. Check the current VM address with ip -br addr.

2. Find the current Pi IP from a macOS SSH session to gncrpi.local using hostname -I. If unchanged, use 10.91.215.239 for SSH from UTM.

3. In the Pi SSH terminal, load the installed workspace and launch bringup:

```bash
source /opt/ros/jazzy/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export LDS_MODEL=LDS-02
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_bringup robot.launch.py
```

4. Keep bringup open. In LOCAL UTM, verify domain 30 and matching TwistStamped endpoints, then run official TurtleBot3 teleop as shown in section 22.

5. Test forward, stop, and rotation. Stop before closing teleop, then Ctrl+C in bringup.

# 18 Verification and remaining work

Working as reported: Pi OS and ROS, OpenCR firmware, forward push-button test, SSH, bridged UTM networking, and official TurtleBot3 keyboard teleop after fixing the message type. UTM .local resolution previously failed; use current-IP SSH.

Not yet completed: saved full topic inventory, sensor and TF checks, SLAM map creation, map saving, localization, and Nav2 autonomous goals. Keep these as next tasks rather than completed milestones.

With bringup running, use the following read-only checks on the Pi first, then in local UTM. Compare the results:

```bash
ros2 node list
ros2 topic list
ros2 topic info /cmd_vel -v
ros2 topic hz /scan
ros2 topic hz /odom
ros2 topic hz /imu
```

Run each topic-rate check separately and stop it with Ctrl+C. Verify topic names against topic list; these checks are proposed and their outputs have not been recorded.

# 19 If discovery fails again

First verify that the Pi has nodes and topics locally, both systems use domain 30, and UTM obtained an address on the hotspot subnet. Numeric-IP SSH tests reachability; it does not prove ROS discovery.

```bash
echo "$ROS_DOMAIN_ID"
ip -br addr
printenv | grep -E 'ROS_|RMW_'
ros2 daemon stop
ros2 topic list
```

Test multicast by running ros2 multicast receive in UTM, then ros2 multicast send on the Pi. A received Hello World message confirms that direction. Repeat in reverse to check both directions. These tests were suggested but no results were supplied.

If the installed Burger YAML change is lost after a rebuild, make the same parameter change in ~/turtlebot3_ws/src/turtlebot3/turtlebot3_bringup/param/burger.yaml and rebuild only turtlebot3_bringup, then reload the workspace and restart bringup:

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install --packages-select turtlebot3_bringup
source ~/turtlebot3_ws/install/setup.bash
```

Current velocity type is TwistStamped. When adding Nav2, check that its velocity publishers also use TwistStamped.

# 20 Automatic ROS loading in new terminals

I edited ~/.bashrc to load ROS automatically, so the team does not need to source ROS manually in every new terminal. The Pi file had duplicate source lines. Keep each source line once and preserve the existing bash-completion block.

On the Pi as ubuntu, open nano ~/.bashrc and keep these settings at the bottom:

```bash
source /opt/ros/jazzy/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-02
```

In local UTM Ubuntu as nabil, use its separate ~/.bashrc:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=30
export TURTLEBOT3_MODEL=burger
```

Save with Ctrl+O, Enter; exit with Ctrl+X. Run source ~/.bashrc once to update the existing terminal. New interactive Bash terminals and interactive Pi SSH sessions then load these settings automatically.

```bash
source ~/.bashrc
echo "$ROS_DISTRO"
echo "$ROS_DOMAIN_ID"
echo "$TURTLEBOT3_MODEL"
```

Expected values: jazzy, 30, and burger. The workspace path belongs to the Pi setup; do not add it to UTM unless that workspace exists there.

# 21 Network reconnection after changing WiFi

Later, UTM SSH to 10.91.215.239 failed with No route to host. ip -br addr and ip route showed UTM had moved to 10.0.0.66/24 with gateway 10.0.0.1. It was no longer on the earlier hotspot subnet.

I reconnected to gncboot. The team should connect the Mac and Pi to the same hotspot, retain UTM Bridged mode through en0, and check the current addresses. No new address output was recorded after reconnection.

```bash
ip -br addr
ip route
```

If the saved IP fails, use macOS Terminal outside UTM to connect by name and read the current Pi address:

```bash
ssh -o ConnectTimeout=10 ubuntu@gncrpi.local
hostname -I
```

Then SSH from UTM to that address. The observed Pi IP was 10.91.215.239; it is DHCP and can change. UTM gncrpi.local lookup still failed during troubleshooting. Changing ~/.bashrc affects ROS loading, not WiFi connection.

# 22 Official TurtleBot3 teleop now working

I switched to official TurtleBot3 keyboard teleop for W A S D X controls. UTM initially reported Package turtlebot3_teleop not found. The installation command provided was:

```bash
sudo apt update
sudo apt install ros-jazzy-turtlebot3-teleop
```

Afterward, teleop_keyboard ran and its publisher appeared in ros2 topic info /cmd_vel -v. The endpoint output proved the mismatch:

Publisher: teleop_keyboard
Type: geometry_msgs/msg/TwistStamped
Subscriber: turtlebot3_node
Type: geometry_msgs/msg/Twist

I changed the Burger bringup parameter to true, restarted bringup, and confirmed that the robot then moved with official teleop. This is the current working setup; it supersedes the earlier Twist configuration.

To repeat the parameter change on the Pi, stop bringup with Ctrl+C and edit:

```bash
nano "$(ros2 pkg prefix turtlebot3_bringup)/share/turtlebot3_bringup/param/burger.yaml"
```

enable_stamped_cmd_vel: true

Preserve YAML indentation, save, exit, and restart bringup. If needed, apply the same true setting to the source YAML before rebuilding, as described in section 19. A post-change endpoint dump was not saved; successful movement was confirmed by the user.

# 23 Daily commands for the team

Terminal 1 in UTM: connect to the Pi using its current address, then launch hardware bringup inside SSH. With ~/.bashrc configured, no manual source commands are needed:

```bash
ssh -o ConnectTimeout=10 ubuntu@10.91.215.239
ros2 launch turtlebot3_bringup robot.launch.py
```

Terminal 2 in LOCAL UTM: start official teleop:

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

W and X increase or decrease linear velocity. A and D increase or decrease angular velocity. S or Space stops. Start with a single W press and increase gradually. The earlier generic 0.5 m/s command caused problems.

Terminal 3 in LOCAL UTM: inspect the graph and commands:

```bash
ros2 topic list
ros2 node list
ros2 topic info /cmd_vel -v
ros2 topic echo /cmd_vel geometry_msgs/msg/TwistStamped
```

Both velocity endpoints should show TwistStamped. Stop echo with Ctrl+C. Sensor checks remain: ros2 topic hz /scan, /odom, and /imu, one at a time. Stop the robot with S or Space before closing teleop; then Ctrl+C in teleop and bringup. Run sudo poweroff on the Pi for shutdown.

# 24 Official documentation

Use the Jazzy tab on the ROBOTIS pages before copying commands. The robot configuration is Burger with LDS-02. PC setup applies to Ubuntu in UTM; SBC setup applies to the Raspberry Pi.

Raspberry Pi Imager

Download the application used to flash the microSD card.

https://www.raspberrypi.com/software/

TurtleBot3 PC setup

Remote PC installation and TurtleBot3 dependencies.

https://emanual.robotis.com/docs/en/platform/turtlebot3/quick-start/

TurtleBot3 Raspberry Pi setup

Ubuntu Server installation, ROS Base, robot packages, swap, USB rules, and LDS configuration.

https://emanual.robotis.com/docs/en/platform/turtlebot3/sbc_setup/

ROS 2 Jazzy Ubuntu installation

Official Debian package installation instructions for Jazzy.

https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

TurtleBot3 OpenCR setup

Upload the Burger ROS 2 firmware and test the controller.

https://emanual.robotis.com/docs/en/platform/turtlebot3/opencr_setup/

TurtleBot3 bringup

Start the robot drivers and check communication.

https://emanual.robotis.com/docs/en/platform/turtlebot3/bringup/

TurtleBot3 basic operation

Keyboard teleoperation and basic movement tests.

https://emanual.robotis.com/docs/en/platform/turtlebot3/basic_operation/

TurtleBot3 SLAM

Create and save a map for navigation.

https://emanual.robotis.com/docs/en/platform/turtlebot3/slam/

TurtleBot3 Navigation2

Load the saved map and navigate to a goal.

https://emanual.robotis.com/docs/en/platform/turtlebot3/navigation/

LDS 02 specifications

Official specifications for the installed LiDAR.

https://emanual.robotis.com/docs/en/platform/turtlebot3/appendix_lds_02/

UTM networking reference

Bridged networking configuration and the Wi-Fi bridging caveat.

https://docs.getutm.app/settings-apple/devices/network/

https://docs.getutm.app/settings-qemu/devices/network/network/

Keyboard teleop parameters and usage

https://index.ros.org/p/teleop_twist_keyboard/

# 25 Mapping and SLAM setup

Mapping is performed on the UTM Ubuntu computer while the Raspberry Pi continues to run the TurtleBot3 hardware bringup. SLAM Toolbox receives /scan and TF from the robot. The map was successfully created by driving the robot with keyboard teleoperation.

```bash
ros2 launch slam_toolbox online_async_launch.py
```

For RViz during mapping, either start normal RViz or use the saved SLAM view:

```bash
rviz2
# or
rviz2 -d ~/rviz/turtlebot3_slam.rviz
```

Drive the robot while SLAM is running:

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

Save the completed map:

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_room
```

The saved navigation map consists of:

```bash
~/maps/my_room.yaml
~/maps/my_room.pgm
```

# RViz configurations for hardware checks and SLAM

Run these steps on **UTM Ubuntu**. Keep TurtleBot3 bringup running on the Pi and use ROS_DOMAIN_ID=30 on both machines. ROS setup is already loaded by the configured ~/.bashrc.

## Hardware view: odometry, LiDAR, robot model and TF

This is the configuration supplied by the team. It uses `odom` as the fixed frame and can be used before SLAM starts.

Create the directory and open the file:

```bash
mkdir -p ~/rviz
nano ~/rviz/turtlebot3_hardware.rviz
```

Paste the full configuration below. Save with Ctrl+O, Enter, then exit with Ctrl+X.

```yaml
Panels:
  - Class: rviz_common/Displays
    Name: Displays
    Property Tree Widget:
      Expanded:
        - /Global Options1
        - /RobotModel1
        - /LaserScan1
        - /Odometry1
        - /TF1
      Splitter Ratio: 0.5
    Tree Height: 700

  - Class: rviz_common/Selection
    Name: Selection

  - Class: rviz_common/Tool Properties
    Name: Tool Properties
    Expanded: []
    Splitter Ratio: 0.5

  - Class: rviz_common/Views
    Name: Views
    Expanded:
      - /Current View1
    Splitter Ratio: 0.5

Visualization Manager:
  Class: ""
  Global Options:
    Background Color: 48; 48; 48
    Fixed Frame: odom
    Frame Rate: 30

  Displays:
    - Class: rviz_default_plugins/Grid
      Name: Grid
      Enabled: true
      Alpha: 0.5
      Cell Size: 1
      Color: 160; 160; 164
      Line Style:
        Line Width: 0.03
        Value: Lines
      Normal Cell Count: 0
      Offset:
        X: 0
        Y: 0
        Z: 0
      Plane: XY
      Plane Cell Count: 20
      Reference Frame: <Fixed Frame>

    - Class: rviz_default_plugins/RobotModel
      Name: RobotModel
      Enabled: true
      Alpha: 1
      Collision Enabled: false
      Description Source: Topic
      Description Topic:
        Depth: 5
        Durability Policy: Transient Local
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /robot_description
      Links:
        All Links Enabled: true
      Update Interval: 0

    - Class: rviz_default_plugins/LaserScan
      Name: LaserScan
      Enabled: true
      Alpha: 1
      Autocompute Intensity Bounds: true
      Autocompute Value Bounds:
        Max Value: 10
        Min Value: 0
        Value: true
      Axis: Z
      Channel Name: intensity
      Color: 255; 255; 255
      Color Transformer: FlatColor
      Decay Time: 0
      Invert Rainbow: false
      Max Color: 255; 255; 255
      Min Color: 0; 0; 0
      Position Transformer: XYZ
      Selectable: true
      Size (Pixels): 4
      Size (m): 0.01
      Style: Points
      Topic:
        Depth: 10
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Best Effort
        Value: /scan
      Use Fixed Frame: true

    - Class: rviz_default_plugins/Odometry
      Name: Odometry
      Enabled: true
      Alpha: 1
      Axes Length: 0.3
      Axes Radius: 0.03
      Color: 255; 25; 0
      Keep: 100
      Position Tolerance: 0.1
      Shape:
        Alpha: 1
        Axes Length: 0.3
        Axes Radius: 0.03
        Color: 255; 25; 0
        Head Length: 0.1
        Head Radius: 0.03
        Shaft Length: 0.3
        Shaft Radius: 0.015
        Value: Arrow
      Topic:
        Depth: 10
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /odom

    - Class: rviz_default_plugins/TF
      Name: TF
      Enabled: true
      Frame Timeout: 15
      Marker Scale: 0.5
      Show Arrows: true
      Show Axes: true
      Show Names: true
      Update Interval: 0

  Enabled: true

  Tools:
    - Class: rviz_default_plugins/Interact
    - Class: rviz_default_plugins/MoveCamera
    - Class: rviz_default_plugins/Select
    - Class: rviz_default_plugins/FocusCamera
    - Class: rviz_default_plugins/Measure
    - Class: rviz_default_plugins/SetInitialPose
      Topic:
        Value: /initialpose
    - Class: rviz_default_plugins/SetGoal
      Topic:
        Value: /goal_pose
    - Class: rviz_default_plugins/PublishPoint
      Topic:
        Value: /clicked_point

  Views:
    Current:
      Class: rviz_default_plugins/TopDownOrtho
      Name: Current View
      Angle: 0
      Scale: 50
      X: 0
      Y: 0

Window Geometry:
  Height: 900
  Width: 1400
  X: 50
  Y: 50
```

Open the hardware view:

```bash
rviz2 -d ~/rviz/turtlebot3_hardware.rviz
```

## SLAM view: live map, LiDAR, odometry and TF

This SLAM configuration is derived from the supplied hardware view: the fixed frame is changed to `map`, and a Map display subscribes to `/map`. It is a repeatable configuration added to these notes; it is not a recovered copy of an earlier saved RViz file.

Create the file:

```bash
nano ~/rviz/turtlebot3_slam.rviz
```

Paste the full configuration below and save:

```yaml
Panels:
  - Class: rviz_common/Displays
    Name: Displays
    Property Tree Widget:
      Expanded:
        - /Global Options1
        - /RobotModel1
        - /LaserScan1
        - /Odometry1
        - /TF1
        - /Map1
      Splitter Ratio: 0.5
    Tree Height: 700

  - Class: rviz_common/Selection
    Name: Selection

  - Class: rviz_common/Tool Properties
    Name: Tool Properties
    Expanded: []
    Splitter Ratio: 0.5

  - Class: rviz_common/Views
    Name: Views
    Expanded:
      - /Current View1
    Splitter Ratio: 0.5

Visualization Manager:
  Class: ""
  Global Options:
    Background Color: 48; 48; 48
    Fixed Frame: map
    Frame Rate: 30

  Displays:
    - Class: rviz_default_plugins/Map
      Name: Map
      Enabled: true
      Alpha: 0.7
      Color Scheme: map
      Draw Behind: true
      Topic:
        Depth: 1
        Durability Policy: Transient Local
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /map
      Update Topic:
        Depth: 5
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /map_updates
      Use Timestamp: false

    - Class: rviz_default_plugins/Grid
      Name: Grid
      Enabled: true
      Alpha: 0.5
      Cell Size: 1
      Color: 160; 160; 164
      Line Style:
        Line Width: 0.03
        Value: Lines
      Normal Cell Count: 0
      Offset:
        X: 0
        Y: 0
        Z: 0
      Plane: XY
      Plane Cell Count: 20
      Reference Frame: <Fixed Frame>

    - Class: rviz_default_plugins/RobotModel
      Name: RobotModel
      Enabled: true
      Alpha: 1
      Collision Enabled: false
      Description Source: Topic
      Description Topic:
        Depth: 5
        Durability Policy: Transient Local
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /robot_description
      Links:
        All Links Enabled: true
      Update Interval: 0

    - Class: rviz_default_plugins/LaserScan
      Name: LaserScan
      Enabled: true
      Alpha: 1
      Autocompute Intensity Bounds: true
      Autocompute Value Bounds:
        Max Value: 10
        Min Value: 0
        Value: true
      Axis: Z
      Channel Name: intensity
      Color: 255; 255; 255
      Color Transformer: FlatColor
      Decay Time: 0
      Invert Rainbow: false
      Max Color: 255; 255; 255
      Min Color: 0; 0; 0
      Position Transformer: XYZ
      Selectable: true
      Size (Pixels): 4
      Size (m): 0.01
      Style: Points
      Topic:
        Depth: 10
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Best Effort
        Value: /scan
      Use Fixed Frame: true

    - Class: rviz_default_plugins/Odometry
      Name: Odometry
      Enabled: true
      Alpha: 1
      Axes Length: 0.3
      Axes Radius: 0.03
      Color: 255; 25; 0
      Keep: 100
      Position Tolerance: 0.1
      Shape:
        Alpha: 1
        Axes Length: 0.3
        Axes Radius: 0.03
        Color: 255; 25; 0
        Head Length: 0.1
        Head Radius: 0.03
        Shaft Length: 0.3
        Shaft Radius: 0.015
        Value: Arrow
      Topic:
        Depth: 10
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /odom

    - Class: rviz_default_plugins/TF
      Name: TF
      Enabled: true
      Frame Timeout: 15
      Marker Scale: 0.5
      Show Arrows: true
      Show Axes: true
      Show Names: true
      Update Interval: 0

  Enabled: true

  Tools:
    - Class: rviz_default_plugins/Interact
    - Class: rviz_default_plugins/MoveCamera
    - Class: rviz_default_plugins/Select
    - Class: rviz_default_plugins/FocusCamera
    - Class: rviz_default_plugins/Measure
    - Class: rviz_default_plugins/SetInitialPose
      Topic:
        Value: /initialpose
    - Class: rviz_default_plugins/SetGoal
      Topic:
        Value: /goal_pose
    - Class: rviz_default_plugins/PublishPoint
      Topic:
        Value: /clicked_point

  Views:
    Current:
      Class: rviz_default_plugins/TopDownOrtho
      Name: Current View
      Angle: 0
      Scale: 50
      X: 0
      Y: 0

Window Geometry:
  Height: 900
  Width: 1400
  X: 50
  Y: 50
```

With robot bringup running on the Pi, start mapping on UTM:

```bash
ros2 launch slam_toolbox online_async_launch.py
```

In another UTM terminal, open the SLAM view:

```bash
rviz2 -d ~/rviz/turtlebot3_slam.rviz
```

In another UTM terminal, drive slowly to build the map:

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

Save the map:

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_room
```

The output files are `~/maps/my_room.yaml` and `~/maps/my_room.pgm`. The `map` fixed frame requires SLAM to publish the map-to-odom transform; use the hardware view when checking the robot before SLAM starts. The RViz goal tool in these configurations does not start navigation by itself; use the Nav2 launch and RViz instructions in section 27 for saved-map navigation.

# 26 RViz and desktop dependencies

The desktop initially lacked the TurtleBot3 description package, which caused the RobotModel display to fail. Installing the Jazzy TurtleBot3 description package restored the robot model in RViz.

```bash
sudo apt update
sudo apt install ros-jazzy-turtlebot3-description
```

RViz also reported that libsdformat_urdf_plugin.so could not load because libsdformat14.so.14 was missing. After installing the matching sdformat14 runtime library from the configured OSRF/Gazebo repository, RViz loaded correctly. The system later confirmed libsdformat14.so.14 in the aarch64 library path.

```bash
ldconfig -p | grep sdformat14
```

# 27 Nav2 packages and saved-map navigation

Nav2 runs on UTM Ubuntu. The Raspberry Pi runs TurtleBot3 hardware bringup and communicates with UTM using ROS_DOMAIN_ID=30.

## Install Nav2 on UTM Ubuntu

The exact original apt installation command was not recorded. To repeat the Nav2 installation for ROS 2 Jazzy, install the released binary packages:

```bash
sudo apt update
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup
```

Official reference: [Nav2 Jazzy installation documentation](https://docs.nav2.org/jazzy/getting_started/build_and_install/local_installation/).

The desktop setup also uses SLAM Toolbox for mapping. The command above installs the Nav2 navigation and bringup packages; it does not document the separate SLAM Toolbox installation.

## Run saved-map navigation

The working saved-map launch command is:

```bash
ros2 launch nav2_bringup bringup_launch.py \
  map:=$HOME/maps/my_room.yaml \
  params_file:=$HOME/nav2_params_tb3.yaml \
  use_sim_time:=False \
  use_composition:=False \
  autostart:=True
```

Start the official Nav2 RViz view in a second terminal:

```bash
ros2 launch nav2_bringup rviz_launch.py
```

In RViz, use 2D Pose Estimate first and place the robot at its actual position and heading on the saved map. AMCL then publishes the map-to-odom transform. A valid localization chain was verified as map -> odom -> base_footprint.

```bash
ros2 run tf2_ros tf2_echo map base_footprint
```

# 28 Nav2 TwistStamped compatibility changes

The TurtleBot3 node is configured to subscribe to geometry_msgs/msg/TwistStamped. Nav2 initially used ordinary Twist for several velocity publishers, so the robot could not receive the final motion command. A copy of the stock Nav2 parameter file was made and edited.

```bash
cp $(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/params/nav2_params.yaml ~/nav2_params_tb3.yaml
```

The following parameter was added under ros__parameters in all four of these sections: controller_server, behavior_server, velocity_smoother, and collision_monitor:

```bash
enable_stamped_cmd_vel: true
```

After the change, the navigation velocity path uses TwistStamped from controller_server through velocity_smoother and collision_monitor to turtlebot3_node. The active topics are /cmd_vel_nav -> /cmd_vel_smoothed -> /cmd_vel.

```bash
ros2 topic info /cmd_vel_nav -v
ros2 topic info /cmd_vel_smoothed -v
ros2 topic info /cmd_vel -v
```

# 29 Route Server crash and fix

During Nav2 startup, the composed Nav2 container crashed with SIGSEGV immediately after the route_server created its nav2_route::CollisionMonitor operation. The Route Server CollisionMonitor operation was therefore removed from the custom parameter file. This is separate from the standalone collision_monitor node, which is still retained for the robot velocity safety pipeline.

```bash
Route Server operation removed: nav2_route::CollisionMonitor
Standalone node retained: /collision_monitor
```

Navigation is launched with use_composition:=False. This runs Nav2 servers as separate processes, which also makes failures easier to isolate.

# 30 Duplicate Nav2 process problem

At one point navigation_launch.py and bringup_launch.py were running at the same time. This created duplicate planner, controller, BT navigator, velocity smoother, collision monitor, and lifecycle-manager processes. RViz then reported unknown goal responses. Only one Nav2 stack should run.

```bash
Do not run navigation_launch.py separately when bringup_launch.py is already running.
```

For a clean restart on UTM, old local Nav2/RViz processes can be stopped before launching the single stack again:

```bash
pkill -f "ros2 launch nav2_bringup" 2>/dev/null
pkill -f "/nav2_" 2>/dev/null
pkill -f "controller_server" 2>/dev/null
pkill -f "planner_server" 2>/dev/null
pkill -f "smoother_server" 2>/dev/null
pkill -f "route_server" 2>/dev/null
pkill -f "behavior_server" 2>/dev/null
pkill -f "bt_navigator" 2>/dev/null
pkill -f "waypoint_follower" 2>/dev/null
pkill -f "velocity_smoother" 2>/dev/null
pkill -f "collision_monitor" 2>/dev/null
pkill -f "map_server" 2>/dev/null
pkill -f "amcl" 2>/dev/null
pkill -f "rviz2" 2>/dev/null
```

# 31 Lifecycle activation workaround after localization

With the current configuration, map_server, AMCL, controller_server, and smoother_server become active, but planner_server and several later navigation lifecycle nodes may remain inactive during initial startup. After setting the 2D Pose Estimate and confirming localization, the remaining nodes can be activated. This was the successful workaround used for the working navigation tests.

```bash
for node in \
/planner_server \
/behavior_server \
/velocity_smoother \
/collision_monitor \
/bt_navigator
do
  state=$(ros2 lifecycle get "$node" 2>/dev/null)
  echo "$node -> $state"
  if echo "$state" | grep -q "inactive"; then
    ros2 lifecycle set "$node" activate
  fi
done
```

Verify the complete Nav2 state:

```bash
for node in \
/map_server \
/amcl \
/controller_server \
/smoother_server \
/planner_server \
/behavior_server \
/bt_navigator \
/velocity_smoother \
/collision_monitor
do
  printf "%-25s " "$node"
  ros2 lifecycle get "$node"
done
```

The successful test showed all listed nodes as active [3], and /navigate_to_pose had one action server provided by /bt_navigator.

```bash
ros2 action info /navigate_to_pose
```

# 32 Current working navigation procedure

Use this sequence from a clean start:

1. Power the TurtleBot3 and keep the Raspberry Pi hardware bringup running.
1. On UTM, launch the single Nav2 bringup command using my_room.yaml and nav2_params_tb3.yaml.
1. Start Nav2 RViz in a second terminal.
1. Use 2D Pose Estimate to set the robot actual location and heading.
1. Wait a few seconds and verify map -> base_footprint if needed.
1. Run the lifecycle activation block in Section 31 if the remaining nodes are inactive.
1. Use Nav2 Goal in RViz and select a nearby free location.
This procedure was repeated from a clean start and worked. The robot reached multiple Nav2 goals. In the small test area it sometimes took time to settle at the goal or appeared briefly confused; controller/AMCL tuning can be improved later after preserving this working baseline.

# 33 Useful checks for future troubleshooting

```bash
ros2 topic list | grep cmd_vel
ros2 action info /navigate_to_pose
ros2 lifecycle get /planner_server
ros2 lifecycle get /bt_navigator
ros2 run tf2_ros tf2_echo map base_footprint
ros2 topic echo /amcl_pose --once
ros2 topic info /cmd_vel -v
```

If RViz says navigate_to_pose is unavailable, check whether /bt_navigator is active. If map -> base_footprint is missing, set or correct the 2D Pose Estimate. If RViz reports unknown goal responses, check for duplicate Nav2 stacks before changing parameters.

# 34 Current status after October 8 navigation test

Confirmed working: TurtleBot3 hardware bringup, official keyboard teleoperation, LDS-02 scan, odometry, TF, RobotModel in RViz, SLAM Toolbox mapping, map saving, AMCL localization on the saved map, Nav2 planning/control, stamped velocity pipeline, and repeated NavigateToPose goals. The current saved map is ~/maps/my_room.yaml with ~/maps/my_room.pgm. The custom Nav2 file is ~/nav2_params_tb3.yaml.

Known follow-up items: make lifecycle startup fully automatic, tune navigation behavior for the small room, and optionally clean up the docking_server Twist publisher because /cmd_vel can still advertise both Twist and TwistStamped when docking_server is present. The working navigation path itself uses TwistStamped through collision_monitor to turtlebot3_node.

# Appendix A - Full current nav2_params_tb3.yaml

This is the complete custom Nav2 parameter file recorded after the working navigation test. It contains the four stamped velocity settings and does not include the Route Server CollisionMonitor operation that caused the startup crash.

```bash
amcl:
  ros__parameters:
    alpha1: 0.2
    alpha2: 0.2
    alpha3: 0.2
    alpha4: 0.2
    alpha5: 0.2
    base_frame_id: "base_footprint"
    beam_skip_distance: 0.5
    beam_skip_error_threshold: 0.9
    beam_skip_threshold: 0.3
    do_beamskip: false
    global_frame_id: "map"
    lambda_short: 0.1
    laser_likelihood_max_dist: 2.0
    laser_max_range: 100.0
    laser_min_range: -1.0
    laser_model_type: "likelihood_field"
    max_beams: 60
    max_particles: 2000
    min_particles: 500
    odom_frame_id: "odom"
    pf_err: 0.05
    pf_z: 0.99
    recovery_alpha_fast: 0.0
    recovery_alpha_slow: 0.0
    resample_interval: 1
    robot_model_type: "nav2_amcl::DifferentialMotionModel"
    save_pose_rate: 0.5
    sigma_hit: 0.2
    tf_broadcast: true
    transform_tolerance: 1.0
    update_min_a: 0.2
    update_min_d: 0.25
    z_hit: 0.5
    z_max: 0.05
    z_rand: 0.5
    z_short: 0.05
    scan_topic: scan
```

```bash
bt_navigator:
  ros__parameters:
    global_frame: map
    robot_base_frame: base_link
    odom_topic: /odom
    bt_loop_duration: 10
    default_server_timeout: 20
    wait_for_service_timeout: 1000
    action_server_result_timeout: 900.0
    navigators: ["navigate_to_pose", "navigate_through_poses"]
```

```bash
    navigate_to_pose:
      plugin: "nav2_bt_navigator::NavigateToPoseNavigator"
```

```bash
    navigate_through_poses:
      plugin: "nav2_bt_navigator::NavigateThroughPosesNavigator"
```

```bash
    error_code_names:
      - compute_path_error_code
      - follow_path_error_code
```

```bash
controller_server:
  ros__parameters:
    enable_stamped_cmd_vel: true
```

```bash
    controller_frequency: 20.0
    costmap_update_timeout: 0.30
    min_x_velocity_threshold: 0.001
    min_y_velocity_threshold: 0.5
    min_theta_velocity_threshold: 0.001
    failure_tolerance: 0.3
```

```bash
    progress_checker_plugins: ["progress_checker"]
    goal_checker_plugins: ["general_goal_checker"]
    controller_plugins: ["FollowPath"]
```

```bash
    use_realtime_priority: false
```

```bash
    progress_checker:
      plugin: "nav2_controller::SimpleProgressChecker"
      required_movement_radius: 0.5
      movement_time_allowance: 10.0
```

```bash
    general_goal_checker:
      stateful: True
      plugin: "nav2_controller::SimpleGoalChecker"
      xy_goal_tolerance: 0.25
      yaw_goal_tolerance: 0.25
```

```bash
    FollowPath:
      plugin: "nav2_mppi_controller::MPPIController"
```

```bash
      time_steps: 56
      model_dt: 0.05
      batch_size: 2000
```

```bash
      ax_max: 3.0
      ax_min: -3.0
      ay_max: 3.0
      ay_min: -3.0
      az_max: 3.5
```

```bash
      vx_std: 0.2
      vy_std: 0.2
      wz_std: 0.4
```

```bash
      vx_max: 0.5
      vx_min: -0.35
      vy_max: 0.5
      wz_max: 1.9
```

```bash
      iteration_count: 1
      prune_distance: 1.7
      transform_tolerance: 0.1
      temperature: 0.3
      gamma: 0.015
```

```bash
      motion_model: "DiffDrive"
```

```bash
      visualize: true
      regenerate_noises: true
```

```bash
      TrajectoryVisualizer:
        trajectory_step: 5
        time_step: 3
```

```bash
      AckermannConstraints:
        min_turning_r: 0.2
```

```bash
      critics:
        [
          "ConstraintCritic",
          "CostCritic",
          "GoalCritic",
          "GoalAngleCritic",
          "PathAlignCritic",
          "PathFollowCritic",
          "PathAngleCritic",
          "PreferForwardCritic"
        ]
```

```bash
      ConstraintCritic:
        enabled: true
        cost_power: 1
        cost_weight: 4.0
```

```bash
      GoalCritic:
        enabled: true
        cost_power: 1
        cost_weight: 5.0
        threshold_to_consider: 1.4
```

```bash
      GoalAngleCritic:
        enabled: true
        cost_power: 1
        cost_weight: 3.0
        threshold_to_consider: 0.5
```

```bash
      PreferForwardCritic:
        enabled: true
        cost_power: 1
        cost_weight: 5.0
        threshold_to_consider: 0.5
```

```bash
      CostCritic:
        enabled: true
        cost_power: 1
        cost_weight: 3.81
        near_collision_cost: 253
        critical_cost: 300.0
        consider_footprint: false
        collision_cost: 1000000.0
        near_goal_distance: 1.0
        trajectory_point_step: 2
```

```bash
      PathAlignCritic:
        enabled: true
        cost_power: 1
        cost_weight: 14.0
        max_path_occupancy_ratio: 0.05
        trajectory_point_step: 4
        threshold_to_consider: 0.5
        offset_from_furthest: 20
        use_path_orientations: false
```

```bash
      PathFollowCritic:
        enabled: true
        cost_power: 1
        cost_weight: 5.0
        offset_from_furthest: 5
        threshold_to_consider: 1.4
```

```bash
      PathAngleCritic:
        enabled: true
        cost_power: 1
        cost_weight: 2.0
        offset_from_furthest: 4
        threshold_to_consider: 0.5
        max_angle_to_furthest: 1.0
        mode: 0
```

```bash
local_costmap:
  local_costmap:
    ros__parameters:
```

```bash
      update_frequency: 5.0
      publish_frequency: 2.0
```

```bash
      global_frame: odom
      robot_base_frame: base_link
```

```bash
      rolling_window: true
```

```bash
      width: 3
      height: 3
      resolution: 0.05
```

```bash
      robot_radius: 0.22
```

```bash
      plugins:
        [
          "voxel_layer",
          "inflation_layer"
        ]
```

```bash
      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0
        inflation_radius: 0.70
```

```bash
      voxel_layer:
        plugin: "nav2_costmap_2d::VoxelLayer"
        enabled: True
        publish_voxel_map: True
```

```bash
        origin_z: 0.0
        z_resolution: 0.05
        z_voxels: 16
```

```bash
        max_obstacle_height: 2.0
        mark_threshold: 0
```

```bash
        observation_sources: scan
```

```bash
        scan:
          topic: /scan
          max_obstacle_height: 2.0
          clearing: True
          marking: True
          data_type: "LaserScan"
```

```bash
          raytrace_max_range: 3.0
          raytrace_min_range: 0.0
```

```bash
          obstacle_max_range: 2.5
          obstacle_min_range: 0.0
```

```bash
      static_layer:
        plugin: "nav2_costmap_2d::StaticLayer"
        map_subscribe_transient_local: True
```

```bash
      always_send_full_costmap: True
```

```bash
global_costmap:
  global_costmap:
    ros__parameters:
```

```bash
      update_frequency: 1.0
      publish_frequency: 1.0
```

```bash
      global_frame: map
      robot_base_frame: base_link
```

```bash
      robot_radius: 0.22
      resolution: 0.05
```

```bash
      track_unknown_space: true
```

```bash
      plugins:
        [
          "static_layer",
          "obstacle_layer",
          "inflation_layer"
        ]
```

```bash
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        enabled: True
```

```bash
        observation_sources: scan
```

```bash
        scan:
          topic: /scan
          max_obstacle_height: 2.0
          clearing: True
          marking: True
          data_type: "LaserScan"
```

```bash
          raytrace_max_range: 3.0
          raytrace_min_range: 0.0
```

```bash
          obstacle_max_range: 2.5
          obstacle_min_range: 0.0
```

```bash
      static_layer:
        plugin: "nav2_costmap_2d::StaticLayer"
        map_subscribe_transient_local: True
```

```bash
      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0
        inflation_radius: 0.7
```

```bash
      always_send_full_costmap: True
```

```bash
map_saver:
  ros__parameters:
    save_map_timeout: 5.0
    free_thresh_default: 0.25
    occupied_thresh_default: 0.65
    map_subscribe_transient_local: True
```

```bash
planner_server:
  ros__parameters:
```

```bash
    expected_planner_frequency: 20.0
    planner_plugins: ["GridBased"]
    costmap_update_timeout: 1.0
```

```bash
    GridBased:
      plugin: "nav2_navfn_planner::NavfnPlanner"
      tolerance: 0.5
      use_astar: false
      allow_unknown: true
```

```bash
smoother_server:
  ros__parameters:
```

```bash
    smoother_plugins: ["simple_smoother"]
```

```bash
    simple_smoother:
      plugin: "nav2_smoother::SimpleSmoother"
      tolerance: 1.0e-10
      max_its: 1000
      do_refinement: True
```

```bash
behavior_server:
  ros__parameters:
    enable_stamped_cmd_vel: true
```

```bash
    local_costmap_topic: local_costmap/costmap_raw
    global_costmap_topic: global_costmap/costmap_raw
```

```bash
    local_footprint_topic: local_costmap/published_footprint
    global_footprint_topic: global_costmap/published_footprint
```

```bash
    cycle_frequency: 10.0
```

```bash
    behavior_plugins:
      [
        "spin",
        "backup",
        "drive_on_heading",
        "assisted_teleop",
        "wait"
      ]
```

```bash
    spin:
      plugin: "nav2_behaviors::Spin"
```

```bash
    backup:
      plugin: "nav2_behaviors::BackUp"
```

```bash
    drive_on_heading:
      plugin: "nav2_behaviors::DriveOnHeading"
```

```bash
    wait:
      plugin: "nav2_behaviors::Wait"
```

```bash
    assisted_teleop:
      plugin: "nav2_behaviors::AssistedTeleop"
```

```bash
    local_frame: odom
    global_frame: map
```

```bash
    robot_base_frame: base_link
```

```bash
    transform_tolerance: 0.1
    simulate_ahead_time: 2.0
```

```bash
    max_rotational_vel: 1.0
    min_rotational_vel: 0.4
    rotational_acc_lim: 3.2
```

```bash
waypoint_follower:
  ros__parameters:
```

```bash
    loop_rate: 20
    stop_on_failure: false
```

```bash
    action_server_result_timeout: 900.0
```

```bash
    waypoint_task_executor_plugin: "wait_at_waypoint"
```

```bash
    wait_at_waypoint:
      plugin: "nav2_waypoint_follower::WaitAtWaypoint"
      enabled: True
      waypoint_pause_duration: 200
```

```bash
route_server:
  ros__parameters:
```

```bash
    boundary_radius_to_achieve_node: 1.0
    radius_to_achieve_node: 2.0
    smooth_corners: true
```

```bash
    operations:
      [
        "AdjustSpeedLimit",
        "ReroutingService"
      ]
```

```bash
    ReroutingService:
      plugin: "nav2_route::ReroutingService"
```

```bash
    AdjustSpeedLimit:
      plugin: "nav2_route::AdjustSpeedLimit"
```

```bash
    edge_cost_functions:
      [
        "DistanceScorer",
        "CostmapScorer"
      ]
```

```bash
    DistanceScorer:
      plugin: "nav2_route::DistanceScorer"
```

```bash
    CostmapScorer:
      plugin: "nav2_route::CostmapScorer"
```

```bash
velocity_smoother:
  ros__parameters:
    enable_stamped_cmd_vel: true
```

```bash
    smoothing_frequency: 20.0
    stamp_smoothed_velocity_with_smoothing_time: False
```

```bash
    scale_velocities: False
```

```bash
    feedback: "OPEN_LOOP"
```

```bash
    max_velocity: [0.5, 0.0, 2.0]
    min_velocity: [-0.5, 0.0, -2.0]
```

```bash
    max_accel: [2.5, 0.0, 3.2]
    max_decel: [-2.5, 0.0, -3.2]
```

```bash
    odom_topic: "odom"
    odom_duration: 0.1
```

```bash
    deadband_velocity: [0.0, 0.0, 0.0]
```

```bash
    velocity_timeout: 1.0
```

```bash
collision_monitor:
  ros__parameters:
    enable_stamped_cmd_vel: true
```

```bash
    base_frame_id: "base_footprint"
    odom_frame_id: "odom"
```

```bash
    cmd_vel_in_topic: "cmd_vel_smoothed"
    cmd_vel_out_topic: "cmd_vel"
```

```bash
    state_topic: "collision_monitor_state"
```

```bash
    transform_tolerance: 0.2
    source_timeout: 1.0
```

```bash
    base_shift_correction: True
```

```bash
    stop_pub_timeout: 2.0
```

```bash
    polygons:
      [
        "FootprintApproach"
      ]
```

```bash
    FootprintApproach:
      type: "polygon"
      action_type: "approach"
      footprint_topic: "/local_costmap/published_footprint"
      time_before_collision: 1.2
      simulation_time_step: 0.1
      min_points: 6
      visualize: False
      enabled: True
```

```bash
    observation_sources:
      [
        "scan"
      ]
```

```bash
    scan:
      type: "scan"
      topic: "scan"
      min_height: 0.15
      max_height: 2.0
      enabled: True
```

```bash
docking_server:
  ros__parameters:
```

```bash
    controller_frequency: 50.0
```

```bash
    initial_perception_timeout: 5.0
    wait_charge_timeout: 5.0
    dock_approach_timeout: 30.0
```

```bash
    undock_linear_tolerance: 0.05
    undock_angular_tolerance: 0.1
```

```bash
    max_retries: 3
```

```bash
    base_frame: "base_link"
    fixed_frame: "odom"
```

```bash
    dock_backwards: false
```

```bash
    dock_prestaging_tolerance: 0.5
```

```bash
    dock_plugins:
      [
        "simple_charging_dock"
      ]
```

```bash
    simple_charging_dock:
      plugin: "opennav_docking::SimpleChargingDock"
```

```bash
      docking_threshold: 0.05
      staging_x_offset: -0.7
```

```bash
      use_external_detection_pose: true
      use_battery_status: false
      use_stall_detection: false
```

```bash
      external_detection_timeout: 1.0
```

```bash
      external_detection_translation_x: -0.18
      external_detection_translation_y: 0.0
```

```bash
      external_detection_rotation_roll: -1.57
      external_detection_rotation_pitch: -1.57
      external_detection_rotation_yaw: 0.0
```

```bash
      filter_coef: 0.1
```

```bash
    controller:
      k_phi: 3.0
      k_delta: 2.0
```

```bash
      v_linear_min: 0.15
      v_linear_max: 0.15
```

```bash
      use_collision_detection: true
```

```bash
      costmap_topic: "local_costmap/costmap_raw"
      footprint_topic: "local_costmap/published_footprint"
```

```bash
      transform_tolerance: 0.1
```

```bash
      projection_time: 5.0
      simulation_step: 0.1
```

```bash
      dock_collision_threshold: 0.3
```

```bash
loopback_simulator:
  ros__parameters:
```

```bash
    base_frame_id: "base_footprint"
    odom_frame_id: "odom"
    map_frame_id: "map"
    scan_frame_id: "base_scan"
```

```bash
    update_duration: 0.02
```

```bash
    scan_range_min: 0.05
    scan_range_max: 30.0
```

```bash
    scan_angle_min: -3.1415
    scan_angle_max: 3.1415
    scan_angle_increment: 0.02617
```

```bash
    scan_use_inf: true
```

## Tables from the original notes

| Setting | Value |
| --- | --- |
| Pi hostname | gncrpi |
| Pi username | ubuntu |
| Pi password used | ubuntu |
| Phone hotspot name | gncboot |
| Hotspot password | gncboot123 |
| Time zone and Wi-Fi country | America/Los_Angeles; United States |
| Pi IP at initial connection | 10.91.215.239 |
| Confirmed operating system | Ubuntu 24.04.5 LTS; aarch64 / ARM64 |

| Network item | Observed value |
| --- | --- |
| Mac Wi-Fi IP | 10.91.215.126 |
| Subnet mask | 255.255.255.0 |
| Gateway | 10.91.215.107 |
| Subnet scanned | 10.91.215.0/24 |
