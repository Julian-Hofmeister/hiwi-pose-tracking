# One 2D joint in image pixels.
#
# id is the index in PersonPose2DArray.keypoint_names for this source's
# skeleton. It is not a tracking id. Different sources may use different
# lengths and layouts; there is no fixed array size in this message.
#
# name repeats keypoint_names[id] so a person message stays readable when
# some joints were dropped (e.g. below a score threshold).
#
# Coordinates: origin at the top-left of the image, x right, y down, pixels.
# score is typically in [0, 1].

uint16 id
string name
float32 x
float32 y
float32 score
