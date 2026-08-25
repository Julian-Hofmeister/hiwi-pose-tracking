from std_msgs.msg import Header

from rtmpose_ros.message_converter import result_to_pose_array
from rtmpose_ros.models import (
    COCO_17_KEYPOINT_NAMES,
    BoundingBox2D,
    Keypoint2D,
    PersonPose2D,
    PoseEstimationResult,
)


def _header() -> Header:
    header = Header()
    header.stamp.sec = 9
    header.stamp.nanosec = 8
    header.frame_id = 'camera_optical_frame'
    return header


def test_converter_maps_coco_person_and_header() -> None:
    result = PoseEstimationResult(
        image_width=640,
        image_height=480,
        skeleton_type='coco_17',
        model_name='human',
        keypoint_names=COCO_17_KEYPOINT_NAMES,
        poses=(
            PersonPose2D(
                person_id=0,
                score=0.8,
                bounding_box=BoundingBox2D(x=10.0, y=20.0, width=100.0, height=200.0, score=0.9),
                keypoints=(
                    Keypoint2D(id=0, x=50.0, y=60.0, score=0.95, name='nose'),
                    Keypoint2D(id=5, x=40.0, y=90.0, score=0.7, name='left_shoulder'),
                ),
            ),
        ),
    )
    msg = result_to_pose_array(result, _header())

    assert msg.header.stamp.sec == 9
    assert msg.header.stamp.nanosec == 8
    assert msg.header.frame_id == 'camera_optical_frame'
    assert msg.image_width == 640
    assert msg.image_height == 480
    assert msg.skeleton_type == 'coco_17'
    assert msg.model_name == 'human'
    assert list(msg.keypoint_names) == list(COCO_17_KEYPOINT_NAMES)
    assert len(msg.poses) == 1
    person = msg.poses[0]
    assert person.person_id == 0
    assert person.has_bounding_box
    assert person.bounding_box.width == 100.0
    assert len(person.keypoints) == 2
    assert person.keypoints[0].name == 'nose'
    assert person.keypoints[1].id == 5


def test_converter_accepts_variable_keypoint_counts() -> None:
    hand = PoseEstimationResult(
        image_width=32,
        image_height=32,
        skeleton_type='hand_21',
        model_name='hand',
        keypoint_names=tuple(f'k{i}' for i in range(21)),
        poses=(
            PersonPose2D(
                person_id=0,
                score=1.0,
                keypoints=tuple(
                    Keypoint2D(id=i, x=float(i), y=1.0, score=1.0, name=f'k{i}')
                    for i in range(21)
                ),
            ),
        ),
    )
    sparse = PoseEstimationResult(
        image_width=32,
        image_height=32,
        skeleton_type='custom_4',
        model_name='custom',
        keypoint_names=('head', 'hand_l', 'hand_r', 'torso'),
        poses=(
            PersonPose2D(
                person_id=1,
                score=0.5,
                keypoints=(
                    Keypoint2D(id=0, x=1.0, y=2.0, score=0.9, name='head'),
                    Keypoint2D(id=3, x=3.0, y=4.0, score=0.8, name='torso'),
                ),
            ),
        ),
    )

    hand_msg = result_to_pose_array(hand, _header())
    sparse_msg = result_to_pose_array(sparse, _header())

    assert len(hand_msg.keypoint_names) == 21
    assert len(hand_msg.poses[0].keypoints) == 21
    assert len(sparse_msg.keypoint_names) == 4
    assert len(sparse_msg.poses[0].keypoints) == 2
    assert sparse_msg.poses[0].keypoints[1].id == 3
    assert sparse_msg.poses[0].keypoints[1].name == 'torso'


def test_converter_empty_poses_is_valid() -> None:
    result = PoseEstimationResult(
        image_width=16,
        image_height=12,
        skeleton_type='coco_17',
        model_name='empty',
        poses=(),
    )
    msg = result_to_pose_array(result, _header())

    assert list(msg.poses) == []
    assert list(msg.keypoint_names) == list(COCO_17_KEYPOINT_NAMES)
    assert msg.header.frame_id == 'camera_optical_frame'


def test_converter_missing_bbox_is_flagged() -> None:
    result = PoseEstimationResult(
        image_width=8,
        image_height=8,
        skeleton_type='custom_1',
        model_name='x',
        keypoint_names=('pt',),
        poses=(
            PersonPose2D(
                person_id=0,
                score=0.1,
                keypoints=(Keypoint2D(id=0, x=1.0, y=2.0, score=0.2, name='pt'),),
            ),
        ),
    )
    msg = result_to_pose_array(result, _header())
    assert not msg.poses[0].has_bounding_box


def test_converter_maps_zero_one_and_many_people_with_scores() -> None:
    def person(person_id: int, score: float) -> PersonPose2D:
        return PersonPose2D(
            person_id=person_id,
            score=score,
            bounding_box=BoundingBox2D(x=1.0, y=2.0, width=3.0, height=4.0, score=score),
            keypoints=(
                Keypoint2D(id=0, x=8.0, y=9.0, score=score, name='nose'),
            ),
        )

    empty = PoseEstimationResult(
        image_width=10, image_height=10, skeleton_type='coco_17', model_name='t', poses=()
    )
    one = PoseEstimationResult(
        image_width=10,
        image_height=10,
        skeleton_type='coco_17',
        model_name='t',
        poses=(person(0, 0.42),),
    )
    many = PoseEstimationResult(
        image_width=10,
        image_height=10,
        skeleton_type='coco_17',
        model_name='t',
        poses=(person(0, 0.9), person(1, 0.5), person(2, 0.1)),
    )

    empty_msg = result_to_pose_array(empty, _header())
    one_msg = result_to_pose_array(one, _header())
    many_msg = result_to_pose_array(many, _header())

    assert list(empty_msg.poses) == []
    assert len(one_msg.poses) == 1
    assert abs(one_msg.poses[0].score - 0.42) < 1e-5
    assert abs(one_msg.poses[0].keypoints[0].score - 0.42) < 1e-5
    assert [p.person_id for p in many_msg.poses] == [0, 1, 2]
    assert [round(p.score, 1) for p in many_msg.poses] == [0.9, 0.5, 0.1]

