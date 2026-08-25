#!/bin/bash
set -eo pipefail

VENV="${RTMPOSE_VENV:-/opt/rtmpose}"
TEST_IMAGE="${RTMPOSE_TEST_IMAGE:-/tmp/rtmpose_coco_785.jpg}"
COCO_URL="https://raw.githubusercontent.com/open-mmlab/mmpose/main/tests/data/coco/000000000785.jpg"

if [ ! -x "$VENV/bin/python" ]; then
  echo "MMPose venv not found at $VENV" >&2
  exit 1
fi

if [ ! -f "$TEST_IMAGE" ]; then
  wget -q -O "$TEST_IMAGE" "$COCO_URL"
fi

echo "=== versions ==="
"$VENV/bin/python" - <<'PY'
import torch
import mmcv
import mmengine
import mmdet
import mmpose
print("python", __import__("sys").version.split()[0])
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda_device", torch.cuda.get_device_name(0))
print("mmcv", mmcv.__version__)
print("mmengine", mmengine.__version__)
print("mmdet", mmdet.__version__)
print("mmpose", mmpose.__version__)
PY

echo "=== mock inference ==="
"$VENV/bin/python" /ws/scripts/run_rtmpose.py --backend mock --image "$TEST_IMAGE" --output /tmp/mock_result.json
python3 - <<'PY'
import json
result = json.load(open("/tmp/mock_result.json"))
assert result["model_name"] == "mock"
assert len(result["poses"]) == 1
print("mock ok, keypoints", len(result["poses"][0]["keypoints"]))
PY

echo "=== rtmpose cpu inference ==="
"$VENV/bin/python" /ws/scripts/run_rtmpose.py \
  --backend rtmpose \
  --device cpu \
  --pose-model human \
  --image "$TEST_IMAGE" \
  --output /tmp/rtmpose_result.json
python3 - <<'PY'
import json
result = json.load(open("/tmp/rtmpose_result.json"))
print("model", result["model_name"])
print("size", result["image_width"], "x", result["image_height"])
print("persons", len(result["poses"]))
if result["poses"]:
    person = result["poses"][0]
    print("keypoints", len(person["keypoints"]))
    print("bbox", person["bounding_box"])
    assert person["keypoints"], "expected keypoints for a person in the sample image"
    assert person["bounding_box"] is not None
print("rtmpose cpu ok")
PY

echo "=== pytest with real weights ==="
export PYTHONPATH=/ws/src/rtmpose_ros
export RUN_RTMPOSE_INFERENCE=1
export RTMPOSE_TEST_IMAGE="$TEST_IMAGE"
"$VENV/bin/python" -m pytest /ws/src/rtmpose_ros/test/test_rtmpose_estimator.py /ws/src/rtmpose_ros/test/test_mock_estimator.py -q
