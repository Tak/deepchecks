# -*- coding: utf-8 -*-
"""
New Category
************
"""

#%%

from deepchecks.tabular.checks.integrity import CategoryMismatchTrainTest
from deepchecks.tabular import Dataset
import pandas as pd

#%%

train_data = {"col1": ["somebody", "once", "told", "me"] * 10}
test_data = {"col1": ["the","world","is", "gonna", "role", "me","I", "I"] * 10}
train = Dataset(pd.DataFrame(data=train_data), cat_features=["col1"])
test = Dataset(pd.DataFrame(data=test_data), cat_features=["col1"])

#%%

CategoryMismatchTrainTest().run(train, test)

#%%

train_data = {"col1": ["a", "b", "a", "c"] * 10, "col2": ['a','b','b','q']*10}
test_data = {"col1": ["a","b","d"] * 10, "col2": ['a', '2', '1']*10}
train = Dataset(pd.DataFrame(data=train_data), cat_features=["col1","col2"])
test = Dataset(pd.DataFrame(data=test_data), cat_features=["col1", "col2"])

#%%

CategoryMismatchTrainTest().run(train, test)
