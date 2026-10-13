# hiwi-pose-tracking

ROS2 Jazzy node that estimates 2D person poses with RTMPose from one RGB stream
per instance. Several cameras run as several nodes (namespaces), sharing one
YAML for model settings.

## Requirements

- Docker with Linux containers (Ubuntu 24.04 / ROS2 Jazzy image)
- On Windows: Docker Desktop + WSL 2
- Optional: NVIDIA GPU + Container Toolkit (the default image is **CPU**)
- Optional webcam: map `/dev/video0` into the container (Linux)

The ROS node uses **system Python 3.12**. RTMPose runs in `/opt/rtmpose` so
PyTorch/MMPose never share an interpreter with `rclpy`.

## Docker build

From the repository root:

```powershell
docker compose -f docker/docker-compose.yml build
```

Image: `hiwi-pose-tracking:jazzy`. Checkpoints are cached in the Docker volume
`mmpose-cache`.

## Quick start

Synthetic camera + estimator (real RTMPose, first start downloads weights):

```powershell
docker compose -f docker/docker-compose.yml run --rm dev bash -lc "colcon build --symlink-install --packages-up-to rtmpose_ros && source /ws/install/setup.bash && ros2 launch rtmpose_ros mock_camera.launch.py"
```

Other sources:

```bash
ros2 launch rtmpose_ros mock_camera.launch.py source_type:=image
ros2 launch rtmpose_ros mock_camera.launch.py source_type:=video path:=/ws/my.mp4
ros2 launch rtmpose_ros mock_camera.launch.py source_type:=webcam
```

Mock estimator (no MMPose, useful for launch tests):

```bash
ros2 launch rtmpose_ros mock_camera.launch.py backend:=mock
```

`ros2 topic echo` needs `--qos-reliability best_effort` (`sensor_data` QoS).

### Webcam on Windows

Docker Desktop cannot use `/dev/video0`. Capture on the host, estimate in Docker,
watch the overlay in a browser (Explorer does not refresh JPEGs reliably).

Default config uses the faster CPU stack: RTMPose-t + RTMDet-t (~200 ms / ~4–5 FPS).
Alias `human` (RTMPose-m) is slower on CPU (~300–400 ms).

Terminal 1 (Windows — close Camera app and Teams/Zoom):

```powershell
pip install opencv-python
python scripts/webcam_to_jpeg.py --fps 8 --max-width 320
```

Terminal 2:

```powershell
docker compose -f docker/docker-compose.yml run --rm --name hiwi-webcam-test dev bash -lc "colcon build --symlink-install --packages-up-to rtmpose_ros && source /ws/install/setup.bash && ros2 launch rtmpose_ros mock_camera.launch.py source_type:=image path:=/ws/tmp/webcam.jpg fps:=8"
```

Terminal 3 — live overlay:

```powershell
python scripts/watch_preview.py
```

Opens http://127.0.0.1:8765/ and reloads the newest `tmp/live_preview.*.jpg`.
Wait until the log says `pose_estimator ready`, then stand in frame.

If the camera is busy, try `python scripts/webcam_to_jpeg.py --device 1`.

## One node / several nodes

One camera, remaps and namespace:

```bash
ros2 launch rtmpose_ros pose_estimator.launch.py \
  namespace:=camera_1 \
  image_topic:=rgb/image_raw \
  debug_image_topic:=pose/debug_image \
  poses_topic:=pose/poses
```

Three cameras (`camera_1`, `camera_2`, `webcam` from `config/cameras.yaml`).
All instances load `config/rtmpose.yaml`:

```bash
ros2 launch rtmpose_ros multi_camera.launch.py
ros2 launch rtmpose_ros multi_camera.launch.py backend:=mock
```

Each instance is isolated: own process, own RTMPose worker, own topics. Model
files are read-only after the first download.

## Topics (relative)

| Direction | Name          | Type                                |
|-----------|---------------|-------------------------------------|
| Input     | `image`       | `sensor_msgs/Image`                 |
| Output    | `debug_image` | `sensor_msgs/Image` (BGR overlay)   |
| Output    | `poses`       | `human_pose_msgs/PersonPose2DArray` |

Absolute names follow the namespace, e.g. `/camera_1/poses`.

## Parameters

`src/rtmpose_ros/config/rtmpose.yaml` (shared by every instance):

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `backend` | `rtmpose` | `rtmpose` (subprocess) or `mock` |
| `device` | `cpu` | `cpu`, `cuda`, or `auto` (CUDA → else CPU) |
| `pose_model` | `rtmpose-t_…_body8-256x192` | MMPose name/alias (`human` = RTMPose-m) |
| `pose_weights` | `''` | Empty = default checkpoint for the model |
| `detector_model` | `rtmdet-t` | Detector override (`''` = person RTMDet-m) |
| `detector_weights` | `''` | Optional detector weights |
| `keypoint_threshold` | `0.3` | Drop keypoints below this score |
| `detection_threshold` | `0.5` | Person detector threshold |
| `publish_debug_image` | `true` | Overlay on `debug_image` |
| `publish_poses` | `true` | Structured poses on `poses` |
| `rtmpose_python` | `/opt/rtmpose/bin/python` | MMPose interpreter |

Camera list: `src/rtmpose_ros/config/cameras.yaml`. Mock camera:
`src/rtmpose_ros/config/image_source.yaml`.

If `device:=cuda` and CUDA is missing, startup fails with a clear error.
`device:=auto` falls back to CPU.

## Messages, coordinates, keypoints

`human_pose_msgs/PersonPose2DArray`:

- `header.stamp` / `header.frame_id` copied from the camera image
- Pixel coordinates: origin **top-left**, x right, y down
- `Keypoint2D[]` is **variable length** (not fixed 17). Schema per frame:
  `skeleton_type` + `keypoint_names` (index = keypoint `id`)
- Empty `poses[]` is valid (no person)
- `person_id` is unique only inside that message — **not** a track id

Default and alias `human` both use **COCO-17**: nose, eyes, ears, shoulders,
elbows, wrists, hips, knees, ankles. Swap models with `pose_model` without
changing the ROS node.

## Tests and measurements

```powershell
docker compose -f docker/docker-compose.yml run --rm dev bash /ws/docker/run-phase6.sh
```

Earlier phase scripts (`run-phase1.sh` … `run-phase5.sh`) still work.
Standalone CLI without ROS:

```bash
/opt/rtmpose/bin/python /ws/scripts/run_rtmpose.py --backend rtmpose --image /path/to.jpg --output /tmp/out.json
```

### Annotate still images (overlay PNG/JPEG)

Put images in `tmp/inbox/` (or pass a single file), then:

```powershell
docker compose -f docker/docker-compose.yml run --rm dev bash -lc "/opt/rtmpose/bin/python /ws/scripts/annotate_poses.py --input /ws/tmp/inbox --output-dir /ws/tmp/out --json"
```

Annotated images land in `tmp/out/` as `*_pose.jpg` (plus optional JSON).
Uses the same fast CPU defaults as `rtmpose.yaml` (RTMPose-t + RTMDet-t).

Runtime probe:

```bash
python3 /ws/scripts/measure_runtime.py --backend mock --seconds 4 --fps 15
python3 /ws/scripts/measure_runtime.py --backend rtmpose --seconds 8 --fps 5 --image /tmp/rtmpose_coco_785.jpg
python3 /ws/scripts/report_instance_memory.py
```

## Performance (CPU Docker, no GPU)

Measured with `run-phase6.sh` on `hiwi-pose-tracking:jazzy` (single instance).
The ROS process RSS is ~180–190 MB. The MMPose worker is a **separate**
process and is much larger once weights are loaded.

| Setup | Resolution | Requested FPS | Input / output FPS | Mean infer | Mean e2e | Dropped |
|-------|------------|---------------|--------------------|------------|----------|---------|
| mock | 640×480 | 15 | 9.9 / 9.9 | 0.1 ms | 7 ms | 0 |
| RTMPose `human` CPU | 640×425 | 5 | 4.0 / 2.1 | 390 ms (p50 349, p95 578) | 511 ms | 19 / 40 |

On CPU, inference is slower than a 5 Hz camera, so latest-frame-wins drops
unread images. That is expected, not a leak.

GPU memory per instance is one model copy. This image reports
`torch.cuda.is_available() == False`. With a GPU, run
`scripts/report_instance_memory.py` while nodes are up.

## Known limitations

- No depth, 3D, multi-camera fusion, or TensorRT in this version
- Default checkpoints are COCO-trained; commercial use of those weights should
  be checked (`THIRD_PARTY_LICENSES.md`)
- `person_id` is not cross-camera tracking
- Three real RTMPose instances load the model three times (RAM/VRAM × N)
- Webcam needs a device mapping; the compose file has it commented out
- Debug overlay skeleton is drawn for COCO-17 edges; other skeletons still
  publish keypoints

## License

Project code: Apache-2.0. Third-party stack: `THIRD_PARTY_LICENSES.md`.
