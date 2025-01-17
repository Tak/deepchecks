# -*- coding: utf-8 -*-
"""
Confusion Matrix
****************

This notebooks provides an overview for using and understanding the confusion matrix check.

**Structure:**

* `What is the purpose of the check? <#what-is-the-purpose-of-the-check>`__
* `Generate data & model <#generate-data-and-model>`__
* `Run the check <#run-the-check>`__

What is the purpose of the check? 
=================================
The confusion matrix check outputs a confusion matrix for both classification problems
and object detection problems. In object detection problems, some predictions do not
overlap on any label and can be classified as not found in the confusion matrix.
"""

#%%
# Generate Data and Model
# ------------------------
# We generate a sample dataset of 128 images from the `COCO dataset <https://cocodataset.org/#home>`__,
# and using the `YOLOv5 model <https://github.com/ultralytics/yolov5>`__.

from deepchecks.vision.datasets.detection import coco

yolo = coco.load_model(pretrained=True)
train_ds = coco.load_dataset(object_type='VisionData')

#%%
# Run the check
# -------------

from deepchecks.vision.checks.performance import ConfusionMatrixReport

check = ConfusionMatrixReport(categories_to_display=20)
check.run(train_ds, yolo)
