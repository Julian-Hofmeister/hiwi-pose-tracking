"""Report GPU / process memory for pose-estimator worker processes.

Each camera instance owns its own RTMPose subprocess. GPU memory therefore
grows roughly linearly with the number of instances. This script does not
start nodes; run it while they are up, or use it to record that CUDA is
missing (current workstation Docker image).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _run(command: list[str]) -> str:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    output = (result.stdout or '') + (result.stderr or '')
    return output.strip()


def main() -> int:
    print('=== cuda / nvidia-smi ===')
    smi = shutil.which('nvidia-smi')
    if smi is None:
        print('nvidia-smi: not found (no GPU passthrough in this environment)')
    else:
        print(_run([
            smi,
            '--query-compute-apps=pid,process_name,used_gpu_memory',
            '--format=csv',
        ]) or '(no compute apps)')
        print(_run([smi, '--query-gpu=name,memory.used,memory.total', '--format=csv']))

    venv_python = Path(os.environ.get('RTMPOSE_VENV', '/opt/rtmpose')) / 'bin' / 'python'
    if venv_python.is_file():
        print('=== torch.cuda ===')
        print(_run([
            str(venv_python),
            '-c',
            'import torch; print("cuda_available", torch.cuda.is_available()); '
            'print("device_count", torch.cuda.device_count()); '
            'print("current_allocated_bytes", '
            'int(torch.cuda.memory_allocated()) if torch.cuda.is_available() else 0)',
        ]))
    else:
        print(f'torch: rtmpose venv missing at {venv_python}')

    print('=== inference_worker RSS (host /proc) ===')
    found = False
    proc = Path('/proc')
    if proc.is_dir():
        for cmdline_path in proc.glob('*/cmdline'):
            try:
                cmdline = cmdline_path.read_bytes().replace(b'\x00', b' ').decode('utf-8', 'ignore')
            except OSError:
                continue
            if not any(token in cmdline for token in ('inference_worker', 'pose_estimator', 'image_source')):
                continue
            status_path = cmdline_path.parent / 'status'
            try:
                text = status_path.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            rss = next((line.split(':', 1)[1].strip() for line in text.splitlines() if line.startswith('VmRSS:')), '')
            print(f'pid={cmdline_path.parent.name} rss={rss} cmdline={cmdline[:120]}')
            found = True
    if not found:
        print('no pose_estimator / inference_worker process running')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
