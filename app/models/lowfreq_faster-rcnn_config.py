
# the new config inherits the base configs to highlight the necessary modification
_base_ = 'origin/faster_rcnn_r50_fpn_1x_coco.py'

# 2. model settings

# explicitly over-write all the `num_classes` field from default 80 to 5.
model = dict(
    roi_head=dict(
        bbox_head=dict(num_classes=2)))
