# GNC network speed testing

## 1. Check the Pi's Wi-Fi band

On **gncrpi**, run:

```bash
iw dev wlan0 link
```

Read `freq:`. **2462 MHz** means 2.4 GHz. **5785 MHz** means 5 GHz. The `tx bitrate` is the negotiated radio link rate. Use the next test to measure throughput delivered to UTM.

## 2. Measure Pi-to-UTM throughput with iperf3

Pause the RealSense stream for a clean baseline. If needed, install `iperf3` on both machines with `sudo apt install iperf3`.

On **UTM**, use `hostname -I` to find the VM's current IP on the hotspot network, then start the server:

```bash
hostname -I
iperf3 -s
```

On **gncrpi**, run the client. Replace the example IP if UTM's address has changed:

```bash
iperf3 -c 10.64.20.40 -t 30
```

Read the final **receiver** line for the whole 30-second test. The shorter lines show individual intervals. The Pi sends and UTM receives, matching the camera's traffic direction.

| Wi-Fi band | Pi frequency | Measured Pi-to-UTM receiver throughput |
|---|---:|---:|
| 2.4 GHz | 2462 MHz | 55.5 Mbps |
| 5 GHz | 5785 MHz | 121 Mbps |

## 3. Measure live Wi-Fi traffic on the Pi

Finish the active `iperf3` test before measuring robot traffic. Start the RealSense stream and UTM detection viewer, then paste the **entire block** on **gncrpi**. The first three lines initialize the counters. Rerun those lines each time you restart the monitor so the first sample covers roughly one second.

```bash
stats=/sys/class/net/wlan0/statistics
rx=$(cat "$stats/rx_bytes")
tx=$(cat "$stats/tx_bytes")

while sleep 1; do
  new_rx=$(cat "$stats/rx_bytes")
  new_tx=$(cat "$stats/tx_bytes")
  awk -v rx="$((new_rx-rx))" -v tx="$((new_tx-tx))" \
    'BEGIN {printf "RX: %6.2f Mbps | TX: %6.2f Mbps | Total: %6.2f Mbps\n",
                   rx*8/1e6, tx*8/1e6, (rx+tx)*8/1e6}'
  rx=$new_rx
  tx=$new_tx
done
```

Press `Ctrl+C` to stop. The monitor estimates traffic rates for all traffic on `wlan0`. Watch **TX** for camera data going toward UTM. To estimate the load added by the viewer, compare TX with the viewer open and closed while keeping the rest of the setup the same.
