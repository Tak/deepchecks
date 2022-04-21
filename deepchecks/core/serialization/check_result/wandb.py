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
"""Module containing Wandb serializer for the CheckResult type."""
import typing as t
from collections import OrderedDict

import pandas as pd
import wandb
from wandb.sdk.data_types import WBValue
from pandas.io.formats.style import Styler
from plotly.basedatatypes import BaseFigure

from deepchecks.core.check_result import CheckResult
from deepchecks.core.serialization.abc import ABCDisplayItemsHandler
from deepchecks.core.serialization.abc import WandbSerializer
from deepchecks.core.serialization.common import normalize_value
from deepchecks.core.serialization.common import aggregate_conditions
from deepchecks.core.serialization.common import pretify


__all__ = ['CheckResultSerializer']


class CheckResultSerializer(WandbSerializer[CheckResult]):
    """Serializes any CheckResult instance into Wandb media metadata.

    Parameters
    ----------
    value : CheckResult
        CheckResult instance that needed to be serialized.
    """

    def __init__(self, value: CheckResult, **kwargs):
        self.value = value

    def serialize(self, **kwargs) -> t.Dict[str, WBValue]:
        """Serialize a CheckResult instance into Wandb media metadata.

        Returns
        -------
        Dict[str, WBValue]
        """
        header = self.value.header
        output = OrderedDict()
        conditions_table = self.prepare_conditions_table()

        if conditions_table is not None:
            output[f'{header}/conditions table'] = conditions_table

        for section_name, wbvalue in self.prepare_display():
            output[f'{header}/{section_name}'] = wbvalue

        output[f'{header}/results'] = self.prepare_summary_table()

        return output

    def prepare_summary_table(self) -> wandb.Table:
        """Prepare summary table."""
        check_result = self.value
        metadata = check_result.check.metadata()
        return wandb.Table(
            columns=['header', 'params', 'summary', 'value'],
            data=[[
                check_result.header,
                pretify(metadata['params']),
                metadata['summary'],
                pretify(normalize_value(check_result.value))
            ]],
        )

    def prepare_conditions_table(self) -> t.Optional[wandb.Table]:
        """Prepare conditions table."""
        if self.value.conditions_results:
            df = aggregate_conditions(self.value, include_icon=False)
            return wandb.Table(dataframe=df.data, allow_mixed_types=True)

    def prepare_display(self) -> t.List[t.Tuple[str, WBValue]]:
        """Serialize display items into Wandb media format."""
        return DisplayItemsHandler.handle_display(self.value.display)


class DisplayItemsHandler(ABCDisplayItemsHandler):
    """Auxiliary class to decouple display handling logic from other functionality."""

    @classmethod
    def handle_string(cls, item: str, index: int, **kwargs) -> t.Tuple[str, WBValue]:
        """Handle textual item."""
        return (f'item-{index}-html', wandb.Html(data=item))

    @classmethod
    def handle_dataframe(
        cls,
        item: t.Union[pd.DataFrame, Styler],
        index: int,
        **kwargs
    ) -> t.Tuple[str, WBValue]:
        """Handle dataframe item."""
        if isinstance(item, Styler):
            return (
                f'item-{index}-table',
                wandb.Table(dataframe=item.data.reset_index(), allow_mixed_types=True)
            )
        else:
            return (
                f'item-{index}-table',
                wandb.Table(dataframe=item.reset_index(), allow_mixed_types=True)
            )

    @classmethod
    def handle_callable(cls, item: t.Callable, index: int, **kwargs) -> t.Tuple[str, WBValue]:
        """Handle callable."""
        raise NotImplementedError()

    @classmethod
    def handle_figure(cls, item: BaseFigure, index: int, **kwargs) -> t.Tuple[str, WBValue]:
        """Handle plotly figure item."""
        return f'item-{index}-plot', wandb.Plotly(item)
