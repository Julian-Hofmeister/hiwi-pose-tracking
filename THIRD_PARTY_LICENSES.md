# Third-party licenses

This project uses third-party libraries for RTMPose inference. Our own code
is Apache-2.0. The stack below is intended to be commercially usable, with
one caveat on pretrained weights.

| Component | Version (pinned in Docker) | License | Notes |
|-----------|----------------------------|---------|--------|
| Python | 3.12.3 (Ubuntu 24.04 / ROS2 Jazzy) | PSF | System interpreter; MMPose uses a venv |
| setuptools | 75.8.2 | MIT | Pinned; 82+ drops `pkg_resources` which MMEngine still imports |
| PyTorch / torchvision | 2.4.1+cpu / 0.19.1+cpu | BSD-style | CPU wheels; GPU extra |
| OpenCV (headless) | 4.10.0.84 | Apache-2.0 | Estimator venv |
| MMEngine | 0.10.7 | Apache-2.0 | https://github.com/open-mmlab/mmengine |
| MMCV | 2.2.0 | Apache-2.0 | CPU wheel for torch 2.4 |
| MMDetection | 3.3.0 | Apache-2.0 | Person detector (RTMDet) |
| MMPose (incl. RTMPose) | 1.3.2 | Apache-2.0 | https://github.com/open-mmlab/mmpose |
| xtcocotools | 1.14.3 | Apache-2.0 | MMPose COCO helper; built from source |

Apache-2.0 allows commercial use, modification, and distribution, provided
the license and copyright notices are retained.

## Compatibility patches (Python 3.12)

- `mmdet` 3.3.0 declares `mmcv < 2.2.0`, but the only prebuilt CPU wheel for
  torch 2.4 / cp312 is **mmcv 2.2.0**. The Docker install relaxes that upper
  bound to 2.3.0 in `mmdet/__init__.py`.
- `chumpy` (SMPL helper) is not installed: it does not support Python 3.12 and
  is not required for RTMPose 2D.

## Pretrained checkpoints

Default alias `human` downloads OpenMMLab RTMPose-m + RTMDet-m person weights
at first run (cached under `~/.cache`). The **code and OpenMMLab-released
weight files** are Apache-2.0. The models are typically trained on COCO (and
similar research datasets). COCO image licenses vary; using these weights in a
commercial product should be confirmed with the dataset terms before production
deployment.

Replacement: point `pose_model` / `pose_weights` / `detector_model` /
`detector_weights` at internally trained checkpoints. No ROS node change.

## What is not included

TensorRT / MMDeploy, ncnn, and Jetson-specific runtimes are out of scope for
this phase. They have their own licenses (often Apache-2.0 for MMDeploy).
