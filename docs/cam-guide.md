# Phone camera guide — scrcpy → v4l2loopback → browser

How the attendance app gets a camera feed from the phone.

```
phone camera → scrcpy → /dev/video2 (PhoneCam) → browser getUserMedia → jsQR → POST /scan
```

## 0. What must already be true

```bash
lsmod | grep v4l2loopback                 # module loaded
v4l2-ctl --list-devices                   # must list: PhoneCam → /dev/video2
```

If `PhoneCam` is missing, load the module (config already persisted in
`/etc/modprobe.d/v4l2loopback-phonecam.conf`):

```bash
sudo modprobe v4l2loopback
```

## 1. Connect the phone

```bash
adb devices
```

Expected: one line ending in `device`. Over Wi-Fi:

```bash
adb connect <phone-ip>:5555
```

`unauthorized` means: accept the USB-debugging prompt on the phone.

## 2. Inspect the cameras (once per phone)

```bash
scrcpy --list-cameras
scrcpy --list-encoders
```

Example on the vivo V2440:

```
--camera-id=0  (back,  4096x3072, fps={15,20,24,30})
--camera-id=1  (front, 3264x2448, fps={15,20,24,30})
```

That 4096×3072 is why `--camera-size` is mandatory (see Troubleshooting).

## 3. Start the virtual camera

Landscape, the proven baseline:

```bash
scrcpy --video-source=camera --camera-size=1280x720 --camera-fps=30 \
       --v4l2-sink=/dev/video2 --no-playback
```

- `--camera-size=1280x720` — never drop this; the default native size breaks the encoder
- `--camera-fps=30` — 15 saves Wi-Fi bandwidth if the picture stutters
- `--v4l2-sink=/dev/video2` — writes frames into the loopback device
- `--no-playback` — no extra scrcpy window; remove it if you also want the mirror

Leave the terminal open for the whole demo.

## 4. Verify the feed before opening the browser

```bash
fuser -v /dev/video2          # must list the scrcpy process
```

Frame test (only while the browser is NOT using the device):

```bash
ffmpeg -f v4l2 -i /dev/video2 -frames:v 1 -y /tmp/frame.jpg
```

A file with non-zero size = real frames. Do not run this while `/scan` is open:
`v4l2loopback` uses `exclusive_caps=1`, so a second reader steals the stream.

## 5. Orientation

`--capture-orientation` accepts `0`, `90`, `180`, `270`, or `flip` + one of those.
`flip` = mirror horizontally, applied before the rotation.

| What you want | Add this flag | Output |
|---|---|---|
| Landscape, normal | *(nothing)* | 1280×720 |
| Landscape, upside down | `--capture-orientation=180` | 1280×720 |
| Landscape, mirrored | `--capture-orientation=flip0` | 1280×720 |
| Landscape, mirrored + upside down | `--capture-orientation=flip180` | 1280×720 |
| Portrait | `--capture-orientation=90` | 720×1280 |
| Portrait, other way | `--capture-orientation=270` | 720×1280 |
| Portrait, mirrored | `--capture-orientation=flip90` | 720×1280 |
| Portrait, mirrored other way | `--capture-orientation=flip270` | 720×1280 |

Full portrait command:

```bash
scrcpy --video-source=camera --camera-size=1280x720 --camera-fps=30 \
       --capture-orientation=90 --v4l2-sink=/dev/video2 --no-playback
```

Full landscape-upside-down command:

```bash
scrcpy --video-source=camera --camera-size=1280x720 --camera-fps=30 \
       --capture-orientation=180 --v4l2-sink=/dev/video2 --no-playback
```

`--angle` is **not** the flag for this — it rotates the scrcpy window, not the stream
that goes into the loopback.

## 6. Start the app and allow the camera

```bash
cd ~/repo/python-finals
venv/bin/python app.py
```

Open `http://127.0.0.1:5000/scan` and allow the camera **once**.

Brave: tune icon left of the URL → Site settings → Camera → Allow.
Or `brave://settings/content/camera`.

`http://127.0.0.1:5000` and `http://localhost:5000` are different origins — an allow
on one does not apply to the other.

The page prefers a device labelled `PhoneCam`; with scrcpy running it shows the phone.
With scrcpy stopped it silently falls back to the laptop camera.

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `IllegalArgumentException` in `MediaCodec.native_configure`, `Demuxer error` | default camera size 4096×3072 exceeds the MTK encoder | keep `--camera-size=1280x720` |
| `CAM ERROR: check browser permissions` | browser denied the camera for this origin | allow camera in site settings, reload |
| `CAM ERROR: scrcpy issue` | `/dev/video2` exists but nothing writes to it | start scrcpy with `--v4l2-sink` |
| `CAM ERROR: device cam issue` | no camera, or the requested device cannot be opened | check `v4l2-ctl --list-devices`, restart scrcpy |
| `UNKNOWN CODE` | a QR was decoded, but its text is not a student token | scan `qr/<idno>.png` instead |
| `ALREADY RECORDED` | that student already scanned today | expected — `UNIQUE(student_id, day)` |
| `ffmpeg` seems to hang on `/dev/video2` | no writer attached to the loopback | start scrcpy first, never test the device before it |
| video blank, `fuser` empty | scrcpy exited or the phone disconnected | rerun the command, check `adb devices` |

## 8. Stop

`Ctrl+C` in the scrcpy terminal, then confirm:

```bash
fuser -v /dev/video2     # empty output = stopped
```

Closing scrcpy does not close the browser; `/scan` simply falls back to the
laptop camera on the next load.

## 9. Notes

- 720p over Wi-Fi adb is fine for QR decoding; 1080p is untested on this encoder.
- The loopback device is created at boot (`exclusive_caps=1`, label `PhoneCam`).
- A kernel update on Tumbleweed must bring a matching `v4l2loopback-kmp-default`
  in the same transaction, or the module disappears.
