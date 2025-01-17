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
"""module contains Mixed Types check."""
from typing import List, Union, Tuple
import pandas as pd

import numpy as np

from deepchecks.core import CheckResult, ConditionResult, ConditionCategory
from deepchecks.tabular import Context, SingleDatasetCheck
from deepchecks.tabular.utils.display_utils import nothing_found_on_columns
from deepchecks.utils.dataframes import select_from_dataframe
from deepchecks.utils.features import N_TOP_MESSAGE, column_importance_sorter_df
from deepchecks.utils.strings import is_string_column, format_percent
from deepchecks.utils.typing import Hashable


__all__ = ['MixedDataTypes']


class MixedDataTypes(SingleDatasetCheck):
    """Detect a small amount of a rare data type within a column, such as few string samples in a mostly numeric column.

    Parameters
    ----------
    columns : Union[Hashable, List[Hashable]] , default: None
        Columns to check, if none are given checks all columns
        except ignored ones.
    ignore_columns : Union[Hashable, List[Hashable]] , default: None
        Columns to ignore, if none given checks based on columns
        variable.
    n_top_columns : int , optional
        amount of columns to show ordered by feature importance (date, index, label are first)
    """

    def __init__(
        self,
        columns: Union[Hashable, List[Hashable], None] = None,
        ignore_columns: Union[Hashable, List[Hashable], None] = None,
        n_top_columns: int = 10,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.columns = columns
        self.ignore_columns = ignore_columns
        self.n_top_columns = n_top_columns

    def run_logic(self, context: Context, dataset_type: str = 'train') -> CheckResult:
        """Run check.

        Returns
        -------
        CheckResult
            DataFrame with rows ('strings', 'numbers') for any column with mixed types.
            numbers will also include hidden numbers in string representation.
        """
        if dataset_type == 'train':
            dataset = context.train
        else:
            dataset = context.test
        features_importance = context.features_importance

        df = select_from_dataframe(dataset.data, self.columns, self.ignore_columns)

        # Result value: { Column Name: {string: pct, numbers: pct}}
        display_dict = {}
        result_dict = {}

        for column_name in df.columns:
            column_data = df[column_name].dropna()
            mix = self._get_data_mix(column_data)
            if mix:
                result_dict[column_name] = mix
                # Format percents for display
                display_dict[column_name] = {k: format_percent(v) for k, v in mix.items()}

        if display_dict:
            df_graph = pd.DataFrame.from_dict(display_dict)
            df_graph = column_importance_sorter_df(df_graph.T, dataset, features_importance,
                                                   self.n_top_columns).T
            display = [N_TOP_MESSAGE % self.n_top_columns, df_graph]
        else:
            display = nothing_found_on_columns(df.columns)

        return CheckResult(result_dict, display=display)

    @classmethod
    def _get_data_mix(cls, column_data: pd.Series) -> dict:
        if is_string_column(column_data):
            return cls._check_mixed_percentage(column_data)
        return {}

    @classmethod
    def _check_mixed_percentage(cls, column_data: pd.Series) -> dict:
        total_rows = column_data.count()

        def is_float(x) -> bool:
            try:
                float(x)
                return True
            except ValueError:
                return False

        nums = sum(column_data.apply(is_float))
        if nums in (total_rows, 0):
            return {}

        # Then we've got a mix
        nums_pct = nums / total_rows
        strs_pct = (np.abs(nums - total_rows)) / total_rows

        return {'strings': strs_pct, 'numbers': nums_pct}

    def add_condition_rare_type_ratio_not_in_range(self, ratio_range: Tuple[float, float] = (0.01, 0.1)):
        """Add condition - Whether the ratio of rarer data type (strings or numbers) is not in the "danger zone".

        The "danger zone" represents the following logic - if the rarer data type is, for example, 30% of the data,
        than the column is presumably supposed to contain both numbers and numeric values. If the rarer data type is,
        for example, less than 1% of the data, than it's presumably a contamination, but a negligible one. In the range
        between, there is a real chance that the rarer data type may represent a problem to model training and
        inference.

        Parameters
        ----------
        ratio_range : Tuple[float, float] , default: (0.01 , 0.1)
            The range between which the ratio of rarer data type in the column is
            considered a problem.
        """
        def condition(result):
            failing_columns = []
            for col, ratios in result.items():
                rarer_ratio = min(ratios['strings'], ratios['numbers'])
                if ratio_range[0] < rarer_ratio < ratio_range[1]:
                    failing_columns.append(col)
            if failing_columns:
                details = f'Found columns with non-negligible quantities of samples with a different data type from ' \
                          f'the majority of samples: {failing_columns}'
                return ConditionResult(ConditionCategory.WARN, details)
            return ConditionResult(ConditionCategory.PASS)

        name = f'Rare data types in column are either more than {format_percent(ratio_range[1])} or less ' \
               f'than {format_percent(ratio_range[0])} of the data'
        return self.add_condition(name, condition)
