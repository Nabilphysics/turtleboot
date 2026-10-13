We used ChatGPT to organize and format our setup instructions into this guide.

# TurtleBot OS Setup and Mobile Hotspot

Our completed headless Raspberry Pi setup, written so other Intro to Robotics I teams can repeat it.

## What we did

We used a mobile phone hotspot to connect our TurtleBot3 and laptop to the same local network. Before writing Ubuntu to the Raspberry Pi's microSD card, we configured the Wi-Fi SSID, password, hostname, user account, and SSH access in Raspberry Pi Imager. After booting, the Pi connected to the hotspot and we completed the setup over SSH without a keyboard, monitor, or mouse.

Our hardware was a TurtleBot3 Burger with a Raspberry Pi 4 (2 GB). We installed Ubuntu Server 24.04 LTS (64-bit); the first SSH login reported Ubuntu 24.04.5 LTS and an aarch64 Raspberry Pi kernel. Our laptop was a MacBook running Ubuntu in UTM. We used the Mac Terminal for the first successful SSH connection and later connected from UTM Ubuntu as well.

For this public guide, our hotspot SSID is replaced with `syed_example_ssid`; choose your own network name. Our Pi hostname was `gncrpi`, and Pi username `ubuntu`. We initially used `ubuntu` as the Pi login password. For a public guide, the hotspot password is omitted and teams should choose their own Pi login password rather than reuse our initial one.

This guide covers OS installation and networking. ROS installation, OpenCR firmware, SLAM, and Nav2 are separate steps.

## 1. Prepare the equipment

- Assembled TurtleBot3 with Raspberry Pi 4.
- microSD card (32 GB or larger recommended) and a card reader.
- Laptop with Raspberry Pi Imager installed.
- Mobile phone with Wi-Fi hotspot support.
- Reliable power for the robot/Pi, connected according to the TurtleBot3 instructions.

Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

**Writing the OS erases the selected card. Check that you selected the microSD card, not another drive.**

## 2. Create the mobile hotspot first

On the phone, open the hotspot settings and enable the Wi-Fi hotspot. Menu names differ between Android and iPhone.

Choose an SSID and password and keep them unchanged during setup. This guide uses `syed_example_ssid` as an example network name. Replace it with the SSID you create on your phone.

| Setting | Example / action |
|---|---|
| Hotspot SSID | `syed_example_ssid` or your team's network name |
| Hotspot password | Choose your own password; do not publish it |
| Wi-Fi band | Use 2.4 GHz for a straightforward first setup |
| Automatic hotspot shutdown | Disable it during setup if your phone offers this option |

Connect the laptop to this hotspot before continuing. Keep the phone charged and the hotspot enabled throughout the first boot.

The hotspot acts as the local network between the laptop and robot. Internet access is also needed when downloading software or installing packages; those downloads may use mobile data.

## 3. Select Ubuntu in Raspberry Pi Imager

1. Insert the microSD card into the laptop.
2. Open Raspberry Pi Imager.
3. Select **Raspberry Pi 4** as the device.
4. Select **Other general-purpose OS → Ubuntu → Ubuntu Server 24.04 LTS (64-bit)**. Select the available 24.04 point release for Raspberry Pi 4.
5. Select the microSD card as storage.
6. Open **OS customisation / Edit settings** before writing.

Use Ubuntu **Server**, not Raspberry Pi OS, for this Jazzy setup. Imager labels may differ between versions. The selected Ubuntu image must support Wi-Fi and SSH customisation; if the options are missing, check the latest Imager and the official TurtleBot3 SBC guide rather than writing an unconfigured image.

## 4. Configure Wi-Fi and SSH before writing

Enter these settings in Imager:

| Setting | Value / action |
|---|---|
| Hostname | `gncrpi` in our setup; use a unique hostname for each team's robot |
| Username | `ubuntu` in our setup |
| Login password | Choose a password and keep it in your team's private notes |
| Wi-Fi SSID | The exact hotspot name from step 2 |
| Wi-Fi password | The exact hotspot password from step 2 |
| Wireless country | Your actual country; `US` for our Corvallis setup |
| Time zone | `America/Los_Angeles` for Corvallis, Oregon |
| SSH | Enable SSH |
| SSH authentication | Enable password authentication for this walkthrough |

The Pi login password and hotspot password are separate settings. The username `ubuntu` does not mean that the password is automatically `ubuntu`.

Save the settings, apply them to the image, and write the card. Allow verification to finish, then safely eject the card.

## 5. Boot the Pi without a monitor

1. With power off, insert the card into the Raspberry Pi.
2. Confirm the hotspot is enabled and the laptop is connected to it.
3. Power the robot/Pi using the supported TurtleBot3 power connection.
4. Allow several minutes for the first boot and initial configuration.
5. Check the phone's connected-device list for the Pi, if available.

Do not interrupt the first boot unnecessarily. No keyboard, monitor, or mouse is needed when Wi-Fi credentials and SSH were configured correctly.

## 6. Find the Raspberry Pi's IP address

### First choice: the phone's connected-device list

Other teams can first check the phone: if it shows connected devices and their IP addresses, find the Raspberry Pi there. This is a suggested discovery method, not a step confirmed in our recorded terminal output. The hostname may appear as `gncrpi`, although some phones show only a generic device name.

Our Pi's address during the original session was `10.91.215.239`. **This was a DHCP address, not a permanent address. Your address may differ or change after reconnecting.**

### On macOS

Run these commands in the **Mac Terminal**, not inside Ubuntu:

```bash
networksetup -listallhardwareports
ipconfig getifaddr en0
ipconfig getoption en0 subnet_mask
ipconfig getoption en0 router
arp -a
```

Our Mac's Wi-Fi interface was `en0`. Replace it if the hardware-port list shows a different Wi-Fi interface. The router address is usually the phone, not the Pi. The ARP list may not show every connected device.

### Ubuntu checks we used later

```bash
ip -br addr
ip route
```

These show the laptop's interfaces, route, and known neighbors. They do not guarantee discovery of the Pi.

## 7. Connect using SSH and the IP address

From the laptop terminal:

```bash
ssh -o ConnectTimeout=10 ubuntu@<PI_IP_ADDRESS>
```

Replace `<PI_IP_ADDRESS>` with the address you found. Our original example was:

```bash
ssh -o ConnectTimeout=10 ubuntu@10.91.215.239
```

In our first connection, we accepted the SSH host-key prompt and logged in successfully. For a new connection, SSH asks whether to trust the host key. Confirm you are connecting to your Pi, then type `yes`. Enter the Pi login password from Imager. Password characters are not displayed while typing.

A successful session looks like:

```text
ubuntu@gncrpi:~$
```

Commands entered at this prompt run on the **Pi**, even though the terminal window is on your laptop.

Check the setup:

```bash
hostname
cat /etc/os-release
uname -m
hostname -I
timedatectl
```

Expected results include the selected hostname, Ubuntu 24.04, and `aarch64` for the 64-bit OS.

## 8. Enable connection by hostname

Initially, `gncrpi.local` did not resolve, so we connected by IP first. In the **Pi SSH session**, we installed and enabled Avahi:

```bash
sudo apt update &&
sudo apt install -y avahi-daemon &&
sudo systemctl enable --now avahi-daemon
```

Optional check that it is running:

```bash
systemctl is-active avahi-daemon
```

From another laptop terminal, try:

```bash
ssh -o ConnectTimeout=10 ubuntu@gncrpi.local
```

Replace `gncrpi` if you chose another hostname. Hostname access avoids having to type the current IP when local name discovery works.

For other teams: if Ubuntu cannot resolve `.local`, the following resolver setup is an optional troubleshooting step **on the Ubuntu laptop/VM**. The exact client-side installation command was not retained in our setup history:

```bash
sudo apt update
sudo apt install -y avahi-daemon libnss-mdns
sudo systemctl enable --now avahi-daemon
getent hosts gncrpi.local
```

Some hotspots or VM network modes block multicast name discovery. If hostname access still fails, connect using the IP address. Working SSH by IP confirms that hostname resolution is a separate issue.

## 9. Extra step for Ubuntu inside UTM

Our Ubuntu VM initially had an address such as `192.168.64.3`, while the Pi was on `10.91.215.x`. This was UTM's shared network, a different subnet.

For our ROS setup, we shut down Ubuntu, changed the UTM network to **Bridged** using the Mac's Wi-Fi interface (`en0` in our case), and restarted the VM. Inside Ubuntu, check:

```bash
ip -br addr
ip route
```

Confirm the VM gets an address on the hotspot subnet and can SSH to the Pi:

```bash
ssh -o ConnectTimeout=10 ubuntu@<PI_IP_ADDRESS>
```

Bridging availability depends on UTM, macOS, and the network. Being able to SSH does not automatically mean ROS 2 discovery works. ROS 2 also requires compatible discovery settings, matching domain IDs, and network access for its discovery/data traffic. In our project, we used `ROS_DOMAIN_ID=30` on both computers.

## 10. Problems we encountered and repeat checks

| Problem | What to check |
|---|---|
| Pi does not appear on the hotspot | Wait for first boot; check power, Wi-Fi credentials, hotspot band, and whether the hotspot is still enabled |
| `Could not resolve hostname` | Try the current IP; check Avahi, Ubuntu `.local` support, and VM network mode |
| `No route to host` | Check whether the laptop changed Wi-Fi networks or the Pi's IP changed |
| `Connection timed out` | Check the Pi is online, SSH was enabled, and the hotspot permits communication between clients |
| `Connection refused` | The address may be reachable but SSH is not ready or enabled; allow first boot to complete and check the selected image/settings |
| Password rejected | Use the Pi account password configured in Imager, not the hotspot password |
| `Waiting for cache lock` during apt | Let automatic package updates finish; do not delete the package-manager lock files |
| SSH disconnects after reboot | Wait for boot to finish, then reconnect; the IP may have changed |
| SSH works but ROS topics are missing | Check ROS domain/discovery settings and multicast/network access separately |

When troubleshooting, start with a direct SSH connection by IP before debugging hostname discovery or ROS 2.

## 11. Recommended shutdown after a session

From the Pi SSH session:

```bash
sudo poweroff
```

Wait for shutdown to finish before switching off power. To reboot instead:

```bash
sudo reboot
```

The SSH connection closing during either operation is expected.

## Completion checklist

- [ ] Laptop and Raspberry Pi connected to the same hotspot.
- [ ] Ubuntu Server 24.04 LTS, 64-bit installed.
- [ ] SSH connection by IP works.
- [ ] Hostname connection tested, with IP fallback recorded.
- [ ] UTM network checked if using a VM.
- [ ] Credentials kept in private team notes.

The Raspberry Pi is now ready for the ROS 2 Jazzy and TurtleBot3 software setup.

## Official documentation

- [ROBOTIS TurtleBot3 SBC setup](https://emanual.robotis.com/docs/en/platform/turtlebot3/sbc_setup/) — select the ROS 2 Jazzy instructions.
- [Raspberry Pi Imager download](https://www.raspberrypi.com/software/).
- [Raspberry Pi getting started and OS customisation](https://www.raspberrypi.com/documentation/computers/getting-started.html).
- [ROS 2 Jazzy Ubuntu installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html).

This is our team's headless hotspot workflow, based on the official setup documentation and our successful TurtleBot3 installation. Hotspot behavior varies by phone; same-network communication and hostname discovery should be tested before relying on them for a robot demonstration.
