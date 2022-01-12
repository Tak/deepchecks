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
"""Handle display of suite result."""
from typing import List, Union

# pylint: disable=protected-access
import sys
import tqdm
from tqdm.notebook import tqdm as tqdm_notebook
import pandas as pd
from IPython.core.display import display, display_html
from IPython import get_ipython
import ipywidgets as widgets

from deepchecks import errors
from deepchecks.utils.ipython import is_widgets_enabled
from deepchecks.utils.strings import get_random_string
from deepchecks.base.check import CheckResult, CheckFailure
from deepchecks.base.display_pandas import dataframe_to_html, display_conditions_table


__all__ = ['display_suite_result', 'ProgressBar']

def _get_check_widget(check_res: CheckResult, unique_id: str) -> widgets.HTML:
    return check_res.get_check_html(False, unique_id, True)
    check_widg = widgets.HTML(check_res.get_check_html(False, unique_id, True))
    return check_widg

def _create_table_widget(df_html: str) -> widgets.HTML:
    table_box = widgets.VBox()
    df_widg = widgets.HTML(df_html)
    table_box.children = [df_widg]
    table_box.add_class('rendered_html')
    table_box.add_class('jp-RenderedHTMLCommon')
    table_box.add_class('jp-RenderedHTML') 
    table_box.add_class('jp-OutputArea-output') 
    return table_box

class ProgressBar:
    """Progress bar for display while running suite."""

    def __init__(self, name, length):
        """Initialize progress bar."""
        shared_args = {'total': length, 'desc': name, 'unit': ' Check', 'leave': False, 'file': sys.stdout}
        if is_widgets_enabled():
            self.pbar = tqdm_notebook(**shared_args, colour='#9d60fb')
        else:
            # Normal tqdm with colour in notebooks produce bug that the cleanup doesn't remove all characters. so
            # until bug fixed, doesn't add the colour to regular tqdm
            self.pbar = tqdm.tqdm(**shared_args, bar_format=f'{{l_bar}}{{bar:{length}}}{{r_bar}}')

    def set_text(self, text):
        """Set current running check."""
        self.pbar.set_postfix(Check=text)

    def close(self):
        """Close the progress bar."""
        self.pbar.close()

    def inc_progress(self):
        """Increase progress bar value by 1."""
        self.pbar.update(1)


def get_display_exists_icon(exists: bool):
    if exists:
        return '<div style="text-align: center">Yes</div>'
    return '<div style="text-align: center">No</div>'


def display_suite_result(suite_name: str, results: List[Union[CheckResult, CheckFailure]]):
    """Display results of suite in IPython."""
    if len(results) == 0:
        display_html(f"""<h1>{suite_name}</h1><p>Suite is empty.</p>""", raw=True)
        return
    if 'google.colab' in str(get_ipython()):
        unique_id = ''
    else:
        unique_id = get_random_string()
    is_widgets = is_widgets_enabled()
    if is_widgets:
        tab = widgets.Tab()
        condition_tab = widgets.VBox()
        condition_tab.add_class('rendered_html')
        condition_tab.add_class('jp-RenderedHTMLCommon')
        condition_tab.add_class('jp-RenderedHTML') 
        condition_tab.add_class('jp-OutputArea-output')
        checks_wo_tab = widgets.VBox()
        others_tab = widgets.VBox()
        tab.children = [condition_tab, checks_wo_tab, others_tab]
        tab.set_title(0, 'Checks With Conditions')
        tab.set_title(1, 'Checks Without Conditions')
        tab.set_title(2, 'Checks Without Output')
    checks_with_conditions = []
    checks_wo_conditions = []
    display_table: List[CheckResult] = []
    others_table = []

    for result in results:
        if isinstance(result, CheckResult):
            if result.have_conditions():
                checks_with_conditions.append(result)
                if result.have_display():
                    display_table.append(result)
            elif result.have_display():
                checks_wo_conditions.append(result)
            if not result.have_display():
                others_table.append([result.get_header(), 'Nothing found', 2])
        elif isinstance(result, CheckFailure):
            msg = result.exception.__class__.__name__ + ': ' + str(result.exception)
            name = result.header
            others_table.append([name, msg, 1])
        else:
            # Should never reach here!
            raise errors.DeepchecksValueError(
                f"Expecting list of 'CheckResult'|'CheckFailure', but got {type(result)}."
            )

    display_table = sorted(display_table, key=lambda it: it.priority)

    light_hr = '<hr style="background-color: #eee;border: 0 none;color: #eee;height: 1px;">'
    if is_widgets:
        bold_hr = ''
    else:
        bold_hr = '<hr style="background-color: black;border: 0 none;color: black;height: 1px;">'

    icons = """
    <span style="color: green;display:inline-block">\U00002713</span> /
    <span style="color: red;display:inline-block">\U00002716</span> /
    <span style="color: orange;font-weight:bold;display:inline-block">\U00000021</span>
    """

    check_names = list(set(it.check.name() for it in results))
    prologue = (
        f"The suite is composed of various checks such as: {', '.join(check_names[:3])}, etc..."
        if len(check_names) > 3
        else f"The suite is composed of the following checks: {', '.join(check_names)}."
    )

    suite_creation_example_link = (
        'https://docs.deepchecks.com/en/stable/examples/guides/create_a_custom_suite.html'
        '?utm_source=suite_output&utm_medium=referral&utm_campaign=display_link'
    )

    # suite summary
    display_html(
        f"""
        <h1 id="summary_{unique_id}">{suite_name}</h1>
        <p>
            {prologue}<br>
            Each check may contain conditions (which will result in pass / fail / warning, represented by {icons})
            as well as other outputs such as plots or tables.<br>
            Suites, checks and conditions can all be modified (see the
            <a href={suite_creation_example_link}>Create a Custom Suite</a> tutorial).
        </p>
        {bold_hr}
        """,
        raw=True
    )
    
    if checks_with_conditions:
        cond_html_h2 = '<h2>Conditions Summary</h2>'
        cond_html_table = display_conditions_table(checks_with_conditions, unique_id)
        if is_widgets:
            h2_widget = widgets.HTML(cond_html_h2)
            condition_tab_children = [h2_widget, _create_table_widget(cond_html_table)]
        else:
            display_html(cond_html_h2 + cond_html_table, raw=True)
    else:
        not_found_text = '<p>No conditions defined on checks in the suite.</p>'
        if is_widgets:
                condition_tab_children = [widgets.HTML(not_found_text)]
        else:
            display_html(not_found_text, raw=True)

    outputs_h2 = f'{bold_hr}<h2>Additional Outputs</h2>'
    if is_widgets:
        condition_tab_children.append(widgets.HTML(outputs_h2))
    else:
        display_html(outputs_h2, raw=True)
    if display_table:
        for i, r in enumerate(display_table):
            if is_widgets:
                condition_tab_children.append(_get_check_widget(r, unique_id))
            else:
                r.show(show_conditions=False, unique_id=unique_id)
            if i < len(display_table) - 1:
                if is_widgets:
                    condition_tab_children.append(widgets.HTML(light_hr))
                else:
                    display_html(light_hr, raw=True)
    else:
        no_output_text = '<p>No outputs to show.</p>'
        if is_widgets:
            condition_tab_children.append(widgets.HTML(no_output_text))
        else:
            display_html(no_output_text, raw=True)

    if is_widgets:
        condition_tab.children = condition_tab_children

    if others_table:
        others_table = pd.DataFrame(data=others_table, columns=['Check', 'Reason', 'sort'])
        others_table.sort_values(by=['sort'], inplace=True)
        others_table.drop('sort', axis=1, inplace=True)
        others_h2 = f'{bold_hr}<h2>Other Checks That Weren\'t Displayed</h2>'
        others_df = dataframe_to_html(others_table.style.hide_index())
        if is_widgets:
            h2_widget = widgets.HTML(others_h2)
            others_tab.children = [h2_widget, _create_table_widget(others_df)]
        else:
            display_html(others_h2 + others_df, raw=True)
    if is_widgets:
        display(tab)
    else:
        display_html(f'<br><a href="#summary_{unique_id}" style="font-size: 14px">Go to top</a>', raw=True)
