import os
from pathlib import Path

import pytest
from ament_index_python.packages import get_package_share_directory

from rtmpose_ros.camera_inventory import load_camera_inventory


def _cameras_path() -> Path:
    return Path(get_package_share_directory('rtmpose_ros')) / 'config' / 'cameras.yaml'


def test_shared_inventory_has_three_distinct_namespaces() -> None:
    cameras = load_camera_inventory(_cameras_path())
    namespaces = [camera['namespace'] for camera in cameras]
    assert namespaces == ['camera_1', 'camera_2', 'webcam']
    assert len(set(namespaces)) == 3
    frame_ids = [camera['frame_id'] for camera in cameras]
    assert len(set(frame_ids)) == 3


def test_duplicate_namespace_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / 'cameras.yaml'
    path.write_text(
        'cameras:\n  - namespace: cam\n  - namespace: cam\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='duplicate'):
        load_camera_inventory(path)
