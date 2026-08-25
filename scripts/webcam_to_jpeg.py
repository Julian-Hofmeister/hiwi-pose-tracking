"""Grab the Windows webcam and write tmp/webcam.jpg for the Docker node.

Run this on the host (not inside Docker):

    pip install opencv-python
    python scripts/webcam_to_jpeg.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import cv2


def _open_camera(index: int) -> cv2.VideoCapture:
    if sys.platform == 'win32':
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            return cap
    cap = cv2.VideoCapture(index)
    return cap


def main() -> int:
    parser = argparse.ArgumentParser(description='Write webcam frames to a JPEG file.')
    parser.add_argument('--device', type=int, default=0)
    parser.add_argument('--output', default='', help='Default: <repo>/tmp/webcam.jpg')
    parser.add_argument('--fps', type=float, default=8.0)
    parser.add_argument(
        '--max-width',
        type=int,
        default=320,
        help='Downscale before writing (faster CPU pose). 0 = keep capture size.',
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    output = Path(args.output) if args.output else repo / 'tmp' / 'webcam.jpg'
    output.parent.mkdir(parents=True, exist_ok=True)

    cap = _open_camera(args.device)
    if not cap.isOpened():
        raise SystemExit(
            f'Could not open webcam {args.device}. Close the Camera app and Teams/Zoom, '
            'then try --device 1.'
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    period = 1.0 / max(args.fps, 0.5)
    print(
        f'Writing {output} (max_width={args.max_width}) — '
        'stand in view of the camera, Ctrl+C to stop.'
    )
    try:
        while True:
            ok, frame = cap.read()
            if ok:
                if args.max_width > 0 and frame.shape[1] > args.max_width:
                    scale = args.max_width / float(frame.shape[1])
                    frame = cv2.resize(
                        frame,
                        (args.max_width, max(1, int(round(frame.shape[0] * scale)))),
                        interpolation=cv2.INTER_AREA,
                    )
                ok_enc, encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if not ok_enc:
                    continue
                data = encoded.tobytes()
                tmp_path = output.with_name(f'{output.stem}.{time.time_ns()}.part.jpg')
                try:
                    tmp_path.write_bytes(data)
                    os.replace(tmp_path, output)
                except OSError:
                    try:
                        output.write_bytes(data)
                    except OSError:
                        pass
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except OSError:
                        pass
            time.sleep(period)
    except KeyboardInterrupt:
        print('\nstopped')
    finally:
        cap.release()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
