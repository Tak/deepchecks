# -*- coding: utf-8 -*-
"""
Train Test Feature Drift
************************

This notebooks provides an overview for using and understanding feature drift check.

**Structure:**

* `What is a feature drift? <#what-is-a-feature-drift>`__
* `Generate data & model <#generate-data-model>`__
* `Run the check <#run-the-check>`__
* `Define a condition <#define-a-condition>`__

What is a feature drift?
========================
Data drift is simply a change in the distribution of data over time. It is
also one of the top reasons of a machine learning model performance degrades
over time.

Causes of data drift include:

* Upstream process changes, such as a sensor being replaced that changes the
  units of measurement from inches to centimeters.
* Data quality issues, such as a broken sensor always reading 0.
* Natural drift in the data, such as mean temperature changing with the seasons.
* Change in relation between features, or covariate shift.

Feature drift is such drift in a single feature in the dataset.

In the context of machine learning, drift between the training set and the
test set will likely make the model to be prone to errors. In other words,
this means that the model was trained on data that is different from the
current test data, thus it will probably make more mistakes predicting the
target variable.

How deepchecks detects feature drift
------------------------------------
There are many methods to detect feature drift. Some of them include
training a classifier that detects which samples come from a known
distribution and defines the drift by the accuracy of this classifier. For
more information, refer to the :doc:`Whole Dataset Drift check
</examples/tabular/checks/distribution/examples/plot_whole_dataset_drift>`.

Other approaches include statistical methods aim to measure difference
between distribution of 2 given sets. We exprimented with various approaches
and found that for detecting drift in a single feature, the following 2
methods give the best results:

* `Population Stability Index (PSI) <https://www.lexjansen.com/wuss/2017/47_Final_Paper_PDF.pdf>`__
* `Wasserstein metric (Earth Movers Distance) <https://en.wikipedia.org/wiki/Wasserstein_metric>`__

For numerical features, the check uses the Earth Movers Distance method
and for the categorical features it uses the PSI. The check calculates drift
between train dataset and test dataset per feature, using these 2 statistical
measures.
"""

#%%
# Generate data & model
# =====================
# Let's generate a mock dataset of 2 categorical and 2 numerical features

import numpy as np
import pandas as pd

np.random.seed(42)

train_data = np.concatenate([np.random.randn(1000,2), np.random.choice(a=['apple', 'orange', 'banana'], p=[0.5, 0.3, 0.2], size=(1000, 2))], axis=1)
test_data = np.concatenate([np.random.randn(1000,2), np.random.choice(a=['apple', 'orange', 'banana'], p=[0.5, 0.3, 0.2], size=(1000, 2))], axis=1)

df_train = pd.DataFrame(train_data, columns=['numeric_without_drift', 'numeric_with_drift', 'categorical_without_drift', 'categorical_with_drift'])
df_test = pd.DataFrame(test_data, columns=df_train.columns)

df_train = df_train.astype({'numeric_without_drift': 'float', 'numeric_with_drift': 'float'})
df_test = df_test.astype({'numeric_without_drift': 'float', 'numeric_with_drift': 'float'})

#%%

df_train.head()

#%%
# Insert drift into test:
# -----------------------
# Now, we insert a synthetic drift into 2 columns in the dataset

df_test['numeric_with_drift'] = df_test['numeric_with_drift'].astype('float') + abs(np.random.randn(1000)) + np.arange(0, 1, 0.001) * 4
df_test['categorical_with_drift'] = np.random.choice(a=['apple', 'orange', 'banana', 'lemon'], p=[0.5, 0.25, 0.15, 0.1], size=(1000, 1))

#%%
# Training a model
# ----------------
# Now, we are building a dummy model (the label is just a random numerical
# column). We preprocess our synthetic dataset so categorical features are
# being encoded with an OrdinalEncoder

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from sklearn.tree import DecisionTreeClassifier

from deepchecks.tabular import Dataset

#%%

model = Pipeline([
    ('handle_cat', ColumnTransformer(
        transformers=[
            ('num', 'passthrough',
             ['numeric_with_drift', 'numeric_without_drift']),
            ('cat',
             Pipeline([
                 ('encode', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)),
             ]),
             ['categorical_with_drift', 'categorical_without_drift'])
        ]
    )),
    ('model', DecisionTreeClassifier(random_state=0, max_depth=2))]
)

#%%

label = np.random.randint(0, 2, size=(df_train.shape[0],))
cat_features = ['categorical_without_drift', 'categorical_with_drift']
df_train['target'] = label
train_dataset = Dataset(df_train, label='target', cat_features=cat_features)

model.fit(train_dataset.data[train_dataset.features], label)

label = np.random.randint(0, 2, size=(df_test.shape[0],))
df_test['target'] = label
test_dataset = Dataset(df_test, label='target', cat_features=cat_features)

#%%
# Run the check
# =============
# Let's run deepchecks' feature drift check and see the results

from deepchecks.tabular.checks import TrainTestFeatureDrift

check = TrainTestFeatureDrift()
result = check.run(train_dataset=train_dataset, test_dataset=test_dataset, model=model)
result

#%%
# Observe the check's output
# --------------------------
# As we see from the results, the check detects and returns the drift score
# per feature. As we expect, the features that were manually manipulated
# to contain a strong drift in them were detected.
#
# In addition to the graphs, each check returns a value that can be controlled
# in order to define expectations on that value (for example, to define that
# the drift score for every feature must be below 0.05).
#
# Let's see the result value for our check

result.value

#%%
# Define a condition
# ==================
# As we can see, we get the drift score for each feature in the dataset, along
# with the feature importance in respect to the model.
#
# Now, we define a condition that enforce each feature's drift score must be
# below 0.1. A condition is deepchecks' way to enforce that results are OK,
# and we don't have a problem in our data or model!

check_cond = check.add_condition_drift_score_not_greater_than(max_allowed_psi_score=0.2, 
                                                              max_allowed_earth_movers_score=0.1)

#%%

result = check_cond.run(train_dataset=train_dataset, test_dataset=test_dataset)
result.show(show_additional_outputs=False)

#%%
# As we see, our condition successfully detects and filters the problematic
# features that contains a drift!
