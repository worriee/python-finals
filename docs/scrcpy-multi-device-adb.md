# adb + scrcpy with more than one device

Two phones attached, one adb server. How to target the right one and recover when the list is stale.

## 0. The problem

```bash
error: more than one device/emulator
```

Any adb command that needs a target refuses to guess when two or more transports are attached (USB cable, Wi-Fi adb, emulator). The fix in one line: name the device with `-s`, or drop the extra transport.

## 1. See what is attached

```bash
adb devices -l
```

Realistic output — one Wi-Fi phone plus one USB phone:

```
List of devices attached
192.168.43.7:5555      device product:v2440 model:V2440 device:v2440 transport_id:3
R58M12345AB            device usb:3-2 product:beyond1 model:SM_G973F device:beyond1 transport_id:4
```

The Wi-Fi entry has no `usb:` field — that absence is the quickest way to tell a TCP/IP transport from a cabled one.

Column meanings:

| Column | Meaning |
|---|---|
| serial | what `-s` takes: `<ip>:5555` for TCP/IP, the USB serial otherwise |
| state | `device` = usable; the other states are in the table below |
| `usb:` | bus-port path of the cable |
| `product:` | device product name |
| `model:` | marketing model |
| `device:` | device codename |

| State | What it blocks |
|---|---|
| `device` | nothing — usable |
| `offline` | every command to that transport; usually a stale connection |
| `unauthorized` | everything until the RSA prompt is accepted on the phone |
| `no permissions` | everything; host USB access rules reject the device |

## 2. Target a device

| Selector | Selects |
|---|---|
| `-s <serial>` | exactly the transport with that serial — always legal |
| `-d` | the single USB device; fails when more than one USB device is attached |
| `-e` | the single emulator; fails when more than one emulator is running |

- `-d` with two USB cables attached: `error: more than one device/emulator`.
- `-e` never picks a real phone, even with zero emulators running.
- This applies to every adb subcommand — `shell`, `install`, `tcpip`, `push`, `reboot` — not just `tcpip`.

## 3. Switch one phone to TCP/IP

Single USB device attached:

```bash
adb -d tcpip 5555
```

Several devices attached:

```bash
adb -s <serial> tcpip 5555
```

`<serial>` is the USB serial from `adb devices -l`, not the IP.

Revert to USB:

```bash
adb -s <serial> usb
```

The setting is per device: it survives cable unplugs and `adb kill-server`, and is cleared by reboot or `adb usb`.

## 4. Find the phone's IP

Hotspot case — the phone is the laptop's default gateway:

```bash
ip route | grep ^default
```

The gateway IP printed there is the phone.

Any case — ask the phone itself:

```bash
adb -s <serial> shell ip -4 addr show wlan0 | grep inet
```

Read the `inet` address, drop the `/24`. The IP can change on reconnect, so re-check after every reconnect.

## 5. Connect and run scrcpy

```bash
adb connect <phone-ip>:5555
```

```bash
scrcpy -s <phone-ip>:5555
```

`-s` matters because wireless adb and USB adb are two entries in `adb devices`; without a selector scrcpy stops with the same `more than one device/emulator` error.

Camera feed into the virtual device from the repo doc, with `-s` added:

```bash
scrcpy -s <phone-ip>:5555 --video-source=camera --camera-facing=back --camera-size=1280x720 --camera-fps=30 -S --no-audio --v4l2-sink=/dev/video2 --no-playback
```

## 6. Clean up stale entries

Drop every wireless transport:

```bash
adb disconnect
```

Drop one:

```bash
adb disconnect <ip>:5555
```

Last resort, when the list is nonsense:

```bash
adb kill-server && adb start-server
adb devices
```

A phone that is physically gone still counts as a device: `adb devices` only reports what the adb server last heard. TCP/IP entries never notice the phone leaving, so they sit there until disconnected or the server restarts — and they keep triggering `more than one device/emulator`.

## 7. Scenario matrix

| Situation | What you run | What to expect |
|---|---|---|
| One USB + one Wi-Fi | `adb devices -l`, then `adb -s <serial> tcpip 5555` | two entries; every per-device command needs `-s` |
| Two USB cables | `adb -s <serial> ...` | `-d` fails; pick a serial |
| Phone + emulator | `adb -s <serial> ...` | `-d` picks the USB phone, `-e` picks the emulator |
| Old phone still listed but gone | `adb disconnect <old-ip>:5555` | entry disappears; `scrcpy -s` on it fails fast |
| Phone reconnecting with a new IP | `ip route`, `adb connect <new-ip>:5555` | new serial; the old entry goes stale |

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `more than one device/emulator` | several transports, no selector | add `-s <serial>`, or `adb disconnect` the extra |
| `-d` refuses with two cables | two USB transports | use `-s <serial>` instead |
| `adb connect` refused | phone not in tcpip mode, or wrong IP | run `adb -s <serial> tcpip 5555`, re-check `ip route` |
| device shows `offline` | stale transport or adbd restarting | `adb disconnect <ip>:5555`, reconnect |
| `unauthorized` after switching | the new transport needs a fresh RSA prompt | unlock the phone, accept, re-run |
| scrcpy mirrors the wrong phone | no `-s`, adb picked the other entry | `scrcpy -s <serial>` |
| TCP/IP mode lost after reboot | `tcpip` is not persistent | re-run `adb -s <serial> tcpip 5555`, reconnect |

## 9. Recap

```bash
adb devices -l
adb disconnect
adb -d tcpip 5555
adb connect <phone-ip>:5555
scrcpy -s <phone-ip>:5555
```

`adb -d tcpip 5555` only when exactly one USB device is attached; otherwise use `adb -s <serial> tcpip 5555`.
