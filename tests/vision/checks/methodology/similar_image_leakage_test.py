# ----------------------------------------------------------------------------
# Copyright (C) 2021 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""Test functions of the VISION train test label drift."""
from copy import copy

from hamcrest import assert_that, equal_to

import numpy as np
from deepchecks.vision.checks import SimilarImageLeakage
from deepchecks.vision.utils.test_utils import get_modified_dataloader
from tests.checks.utils import equal_condition_result

from torch.utils.data import DataLoader
from PIL import Image


def test_no_similar_object_detection(coco_train_visiondata, coco_test_visiondata):
    # Arrange
    train, test = coco_train_visiondata, coco_test_visiondata
    check = SimilarImageLeakage()

    # Act
    result = check.run(train, test)

    # Assert
    assert_that(result.value, equal_to([]))


def test_no_similar_classification(mnist_dataset_train, mnist_dataset_test):
    # Arrange
    train, test = mnist_dataset_train, mnist_dataset_test
    check = SimilarImageLeakage()

    # Act
    result = check.run(train, test)

    # Assert
    # TODO: uncomment when sensitivity problem is fixed
    # assert_that(result.value, equal_to([]))


def test_all_identical_object_detection(coco_train_visiondata):
    # Arrange
    train, test = coco_train_visiondata, coco_train_visiondata
    check = SimilarImageLeakage()

    # Act
    result = check.run(train, test)

    # Assert
    assert_that(set(result.value), equal_to(set(list(zip(range(64), range(64))))))


def test_similar_object_detection(coco_train_visiondata, coco_test_visiondata):
    # Arrange
    train, test = coco_train_visiondata, coco_test_visiondata
    check = SimilarImageLeakage()
    test = copy(test)

    def get_modification_func():
        other_dataset = train.data_loader.dataset

        def mod_func(orig_dataset, idx):
            if idx in range(5):
                data, label = other_dataset[idx]
                return Image.fromarray(np.clip(np.array(data, dtype=np.uint16) + 50, 0, 255).astype(np.uint8)), label
            if idx == 30:  # Also test something that is not in the same order
                data, label = other_dataset[0]
                return Image.fromarray(np.clip(np.array(data, dtype=np.uint16) + 50, 0, 255).astype(np.uint8)), label
            else:
                return orig_dataset[idx]

        return mod_func

    test._data_loader = get_modified_dataloader(test, get_modification_func())

    # Act
    result = check.run(train, test)

    # Assert
    assert_that(set(result.value), equal_to(set(zip(range(5), range(5))).union({(0, 30)})))


def test_train_test_condition_pass(coco_train_visiondata, coco_test_visiondata):
    # Arrange
    train, test = coco_train_visiondata, coco_test_visiondata
    condition_value = 5
    check = SimilarImageLeakage().add_condition_similar_images_not_more_than(condition_value)

    # Act
    result = check.run(train_dataset=train,
                       test_dataset=test)
    condition_result, *_ = check.conditions_decision(result)

    # Assert
    assert_that(condition_result, equal_condition_result(
        is_pass=True,
        name=f'Number of similar images between train and test is not greater than {condition_value}'
    ))


def test_train_test_condition_fail(coco_train_visiondata, coco_test_visiondata):
    # Arrange
    train, test = coco_train_visiondata, coco_train_visiondata
    condition_value = 5
    check = SimilarImageLeakage().add_condition_similar_images_not_more_than(condition_value)

    # Act
    result = check.run(train_dataset=train,
                       test_dataset=test)
    condition_result, *_ = check.conditions_decision(result)

    # Assert
    assert_that(condition_result, equal_condition_result(
        is_pass=False,
        name=f'Number of similar images between train and test is not greater than {condition_value}',
        details='Number of similar images between train and test datasets: 64'
    ))
