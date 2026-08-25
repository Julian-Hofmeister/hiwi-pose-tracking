# All 2D person poses for one camera image.
#
# header.stamp and header.frame_id must match the source sensor_msgs/Image.
#
# Image coordinates: origin top-left, x right, y down, units in pixels.
# image_width / image_height are the pixel size of that image.
#
# skeleton_type names the joint layout for this source, e.g. "coco_17",
# "coco_wholebody", "hand_21", or a custom string. It is not an enum so
# new sources do not require a message change.
#
# keypoint_names is the schema for this source: keypoint_names[i] is the
# joint with id i. Its length is the skeleton size (17, 133, ...), not
# the number of people. A person's Keypoint2D[] may be shorter if some
# joints were omitted.
#
# poses may be empty. An empty array is a valid "no person detected"
# result and must still be published.

std_msgs/Header header
uint32 image_width
uint32 image_height
string skeleton_type
string model_name
string[] keypoint_names
PersonPose2D[] poses
