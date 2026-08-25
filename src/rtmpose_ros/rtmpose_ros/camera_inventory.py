"""Load the multi-camera inventory. No ROS publishers/subscribers."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_camera_inventory(path: str | Path) -> list[dict]:
    """Return camera dicts with namespace, frame_id, and optional remaps."""
    data = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    cameras = data.get('cameras') or []
    if not isinstance(cameras, list) or not cameras:
        raise ValueError(f'No cameras listed in {path}')
    parsed = []
    seen = set()
    for raw in cameras:
        namespace = str(raw['namespace']).strip().strip('/')
        if not namespace:
            raise ValueError('camera namespace must not be empty')
        if namespace in seen:
            raise ValueError(f'duplicate camera namespace: {namespace}')
        seen.add(namespace)
        parsed.append(
            {
                'namespace': namespace,
                'frame_id': str(raw.get('frame_id') or f'{namespace}_optical_frame'),
                'image_topic': str(raw.get('image_topic') or 'image'),
                'debug_image_topic': str(raw.get('debug_image_topic') or 'debug_image'),
                'poses_topic': str(raw.get('poses_topic') or 'poses'),
            }
        )
    return parsed
