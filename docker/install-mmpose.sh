#!/bin/bash
set -eo pipefail

VENV="${RTMPOSE_VENV:-/opt/rtmpose}"

python3 -m venv "$VENV"
"$VENV/bin/pip" install -U pip wheel 'setuptools==75.8.2' packaging ninja numpy cython

"$VENV/bin/pip" install --index-url https://download.pytorch.org/whl/cpu \
    torch==2.4.1 torchvision==0.19.1

"$VENV/bin/pip" install \
    "opencv-python-headless==4.10.0.84" \
    pytest==8.3.5 \
    mmengine==0.10.7

# Prebuilt CPU wheel for torch 2.4 / py3.12. mmdet 3.3.0 declares mmcv<2.2.0;
# the only wheel on this index is 2.2.0, so the version check is patched below.
"$VENV/bin/pip" install mmcv==2.2.0 --only-binary mmcv \
    -f https://download.openmmlab.com/mmcv/dist/cpu/torch2.4.0/index.html

"$VENV/bin/pip" install mmdet==3.3.0
# chumpy is not Python 3.12 compatible and is not required for RTMPose 2D.
"$VENV/bin/pip" install mmpose==1.3.2 --no-deps
"$VENV/bin/pip" install matplotlib pillow json-tricks scipy munkres
"$VENV/bin/pip" install xtcocotools --no-build-isolation

"$VENV/bin/python" - <<'PY'
from pathlib import Path

def relax_mmcv_max(package: str, old: str = "2.2.0", new: str = "2.3.0") -> None:
    matches = list(Path("/opt/rtmpose/lib").rglob(f"{package}/__init__.py"))
    if not matches:
        raise SystemExit(f"could not find {package}/__init__.py")
    path = matches[0]
    text = path.read_text()
    needle = f"mmcv_maximum_version = '{old}'"
    if needle not in text:
        print(f"{package}: no mmcv max pin found, leaving {path}")
        return
    path.write_text(text.replace(needle, f"mmcv_maximum_version = '{new}'"))
    print(f"patched {path}: mmcv max {old} -> {new}")

relax_mmcv_max("mmdet")
relax_mmcv_max("mmpose")
PY

"$VENV/bin/python" - <<'PY'
import torch
import mmcv
import mmengine
import mmdet
import mmpose
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
print("mmcv", mmcv.__version__)
print("mmengine", mmengine.__version__)
print("mmdet", mmdet.__version__)
print("mmpose", mmpose.__version__)
PY
