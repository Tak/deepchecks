# ----------------------------------------------------------------------------
# Copyright (C) 2021-2022 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""Module containing class performance check."""
import typing as t
from collections import defaultdict

import pandas as pd
import torch

from deepchecks import CheckFailure
from deepchecks.core import CheckResult, DatasetKind
from deepchecks.core.errors import DeepchecksValueError, DeepchecksProcessError
from deepchecks.utils.performance.error_model import error_model_display_dataframe, model_error_contribution
from deepchecks.utils.single_sample_metrics import per_sample_cross_entropy
from deepchecks.vision.utils.image_properties import default_image_properties, validate_properties
from deepchecks.vision import TrainTestCheck, Context, Batch
from deepchecks.vision.vision_data import TaskType
from deepchecks.vision.metrics_utils.iou_utils import per_sample_mean_iou

__all__ = ['ModelErrorAnalysis']


class ModelErrorAnalysis(TrainTestCheck):
    """Find the properties that best split the data into segments of high and low model error.

    The check trains a regression model to predict the error of the user's model. Then, the properties scoring the
    highest feature importance for the error regression model are selected and the distribution of the error vs the
    property values is plotted. The check results are shown only if the error regression model manages to predict the
    error well enough.

    Parameters
    ----------
    image_properties : List[Dict[str, Any]], default: None
        List of properties. Replaces the default deepchecks properties.
        Each property is dictionary with keys 'name' (str), 'method' (Callable) and 'output_type' (str),
        representing attributes of said method. 'output_type' must be one of 'continuous'/'discrete'
    max_properties_to_show : int , default: 3
        maximal number of properties to show error distribution for.
    min_property_contribution : float , default: 0.15
        minimum feature importance of a property to the error regression model
        in order to show the property.
    min_error_model_score : float , default: 0.5
        minimum r^2 score of the error regression model for displaying the check.
    min_segment_size : float , default: 0.05
        minimal fraction of data that can comprise a weak segment.
    n_display_samples : int , default: 5_000
        number of samples to display in scatter plot.
    random_state : int, default: 42
        random seed for all check internals.
    """

    def __init__(self,
                 image_properties: t.List[t.Dict[str, t.Any]] = None,
                 max_properties_to_show: int = 20,
                 min_property_contribution: float = 0.15,
                 min_error_model_score: float = 0.5,
                 min_segment_size: float = 0.05,
                 n_display_samples: int = 5_000,
                 random_state: int = 42,
                 **kwargs):
        super().__init__(**kwargs)
        self.random_state = random_state
        self.min_error_model_score = min_error_model_score
        self.min_segment_size = min_segment_size
        self.max_properties_to_show = max_properties_to_show
        self.min_property_contribution = min_property_contribution
        self.n_display_samples = n_display_samples
        self._train_properties = None
        self._test_properties = None
        self._train_scores = None
        self._test_scores = None

        if image_properties is None:
            self.image_properties = default_image_properties
        else:
            validate_properties(image_properties)
            self.image_properties = image_properties

    def initialize_run(self, context: Context):
        """Initialize property and score lists."""
        context.assert_task_type(TaskType.CLASSIFICATION, TaskType.OBJECT_DETECTION)
        self._train_properties = defaultdict(list)
        self._test_properties = defaultdict(list)
        self._train_scores = []
        self._test_scores = []

    def update(self, context: Context, batch: Batch, dataset_kind):
        """Accumulate property data of images and scores."""
        if dataset_kind == DatasetKind.TRAIN:
            dataset = context.train
            properties = self._train_properties
            scores = self._train_scores
        elif dataset_kind == DatasetKind.TEST:
            dataset = context.test
            properties = self._test_properties
            scores = self._test_scores
        else:
            raise RuntimeError(
                'Internal Error! Part of code that must '
                'be unreacheable was reached.'
            )

        images = batch.images
        predictions = batch.predictions
        labels = batch.labels

        for single_property in self.image_properties:
            properties[single_property['name']].extend(single_property['method'](images))

        if dataset.task_type == TaskType.CLASSIFICATION:
            def scoring_func(predictions, labels):
                return per_sample_cross_entropy(labels, predictions)
        elif dataset.task_type == TaskType.OBJECT_DETECTION:
            def scoring_func(predictions, labels):
                return per_sample_mean_iou(predictions, labels)
        else:
            raise DeepchecksValueError(f'Should not reach here! Unsupported task type {dataset.task_type}')

        if isinstance(predictions, torch.Tensor):
            predictions = predictions.cpu().detach().numpy()
        if isinstance(labels, torch.Tensor):
            labels = labels.cpu().detach().numpy()

        # get score using scoring_function
        scores.extend(scoring_func(predictions, labels))

    def compute(self, context: Context) -> CheckResult:
        """Find segments that contribute to model error.

        Returns
        -------
        CheckResult:
            value: dictionary of details for each property segment that split the effect on the error of the model
            display: plots of results
        """
        # build dataframe of properties and scores
        train_property_df = pd.DataFrame(self._train_properties).dropna(axis=1, how='all')
        test_property_df = pd.DataFrame(self._test_properties)[train_property_df.columns]

        try:
            error_fi, error_model_predicted = \
                model_error_contribution(train_property_df,
                                         self._train_scores,
                                         test_property_df,
                                         self._test_scores,
                                         train_property_df.columns.to_list(),
                                         [],
                                         min_error_model_score=self.min_error_model_score,
                                         random_state=self.random_state)
        except DeepchecksProcessError as e:
            return CheckFailure(self, e)

        display, value = error_model_display_dataframe(error_fi,
                                                       error_model_predicted,
                                                       test_property_df,
                                                       [],
                                                       self.max_properties_to_show,
                                                       self.min_property_contribution,
                                                       self.n_display_samples,
                                                       self.min_segment_size,
                                                       self.random_state)

        headnote = """<span>
            The following graphs show the distribution of error for top properties that are most useful for
            distinguishing high error samples from low error samples.
        </span>"""
        display = [headnote] + display if display else None

        return CheckResult(value, display=display)
