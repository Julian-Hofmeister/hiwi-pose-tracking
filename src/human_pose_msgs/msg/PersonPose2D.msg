# One detected person in a single camera frame.
#
# person_id is unique only inside this PersonPose2DArray. It is not a
# stable track id and must not be compared across cameras or frames.
#
# keypoints is a variable-length list. A COCO-17 source may publish 17
# entries, a whole-body source 133, a hand source 21, or any subset after
# score filtering. Use Keypoint2D.id / name together with the parent
# message's keypoint_names and skeleton_type to interpret the joints.
#
# If has_bounding_box is false, bounding_box is unset (zeros) and must
# be ignored.

int32 person_id
float32 score
bool has_bounding_box
BoundingBox2D bounding_box
Keypoint2D[] keypoints
