# -*- coding: utf-8 -*-
"""
String Mismatch
***************

This page provides an overview for using and understanding the "String Mismatch" check.

**Structure:**

* `What is the purpose of the check? <#what-is-the-purpose-of-the-check>`__
* `Run check <#run-the-check>`__
* `Define a condition <#define-a-condition>`__


What is the purpose of the check?
=================================
String Mismatch works on a single dataset, and it looks for mismatches in each string column in the data. Finding
mismatches in strings is helpful for identifying errors in the data. For example, if your data is aggregated from
multiple sources, it might have the same values but with a little variation in the formatting, like a leading uppercase.
In this case, the model's ability to learn may be impaired since it will see categories that are supposed to be the
same, as different categories.

How String Mismatch Defined?
----------------------------
To recognize string mismatch, we transform each string to it's base form. The base form is the string with only its
alphanumeric characters in lowercase. (For example "Cat-9?!" base form is "cat9"). If two strings have the same base
form, they are considered to be the same.

"""

#%%
# Run the Check
# =========

from deepchecks.tabular.checks import StringMismatch
import pandas as pd

data = {'col1': ['Deep', 'deep', 'deep!!!', '$deeP$', 'earth', 'foo', 'bar', 'foo?']}
df = pd.DataFrame(data=data)
result = StringMismatch().run(df)

#%%
# Define a Condition
# ==================

check = StringMismatch().add_condition_no_variants()
result = check.run(df)
result.show(show_additional_outputs=False)
