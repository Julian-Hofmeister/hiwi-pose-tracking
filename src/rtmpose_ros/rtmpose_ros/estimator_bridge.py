"""Run RTMPose in the MMPose venv via a long-lived subprocess."""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

from rtmpose_ros.inference import PoseEstimator, PoseEstimatorConfig
from rtmpose_ros.models import PoseEstimationResult, result_from_dict

_MAGIC = b'RTM1'
_HEADER = struct.Struct('>4sIII')


class SubprocessPoseEstimator(PoseEstimator):
    """Client for ``inference_worker``. The model is loaded once in the child."""

    def __init__(
        self,
        config: PoseEstimatorConfig,
        python_executable: str = '/opt/rtmpose/bin/python',
    ) -> None:
        super().__init__(config)
        if not Path(python_executable).is_file():
            raise RuntimeError(
                f'RTMPose Python not found: {python_executable}. '
                'Build the Docker image that provides /opt/rtmpose.'
            )
        package_root = Path(__file__).resolve().parent.parent
        env = os.environ.copy()
        env['PYTHONPATH'] = str(package_root) + os.pathsep + env.get('PYTHONPATH', '')
        env['PYTHONUNBUFFERED'] = '1'
        command = [
            python_executable,
            '-m',
            'rtmpose_ros.inference_worker',
            '--backend', config.backend,
            '--device', config.device,
            '--pose-model', config.pose_model,
            '--pose-weights', config.pose_weights,
            '--detector-model', config.detector_model,
            '--detector-weights', config.detector_weights,
            '--keypoint-threshold', str(config.keypoint_threshold),
            '--detection-threshold', str(config.detection_threshold),
        ]
        self._proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            env=env,
        )
        ready = self._read_payload()
        if 'error' in ready:
            self.close()
            raise RuntimeError(ready['error'])
        if not ready.get('ready'):
            self.close()
            raise RuntimeError(f'inference worker did not start: {ready}')

    def estimate(self, image: np.ndarray) -> PoseEstimationResult:
        if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
            raise ValueError('Expected a BGR uint8 image with shape (H, W, 3)')
        if self._proc.poll() is not None:
            raise RuntimeError('inference worker process has exited')
        height, width = int(image.shape[0]), int(image.shape[1])
        payload = np.ascontiguousarray(image).tobytes()
        header = _HEADER.pack(_MAGIC, height, width, len(payload))
        assert self._proc.stdin is not None
        self._proc.stdin.write(header)
        self._proc.stdin.write(payload)
        self._proc.stdin.flush()
        response = self._read_payload()
        if 'error' in response:
            raise RuntimeError(response['error'])
        return result_from_dict(response)

    def close(self) -> None:
        if self._proc.stdin:
            try:
                self._proc.stdin.close()
            except Exception:  # noqa: BLE001
                pass
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()

    def _read_payload(self) -> dict:
        assert self._proc.stdout is not None
        header = _read_exact(self._proc.stdout, _HEADER.size)
        magic, _height, _width, nbytes = _HEADER.unpack(header)
        if magic != _MAGIC:
            raise RuntimeError('invalid response from inference worker')
        raw = _read_exact(self._proc.stdout, nbytes)
        return json.loads(raw.decode('utf-8'))


def _read_exact(stream, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        piece = stream.read(remaining)
        if not piece:
            raise RuntimeError('inference worker closed the pipe')
        chunks.append(piece)
        remaining -= len(piece)
    return b''.join(chunks)
