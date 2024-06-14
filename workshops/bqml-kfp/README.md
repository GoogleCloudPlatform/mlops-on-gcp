This notebook demonstrates setting up a Kubeflow Pipeline on GCP
using BigQuery ML for the model training and evaluation.

The model itself predicts the distance that a bicycle will be ridden.
Distances longer than 4 hours are important, but these are rare.
So, a Cascade of ML models is trained.

The first model classifies trips into Typical trips and Long trips. Then, we create two training datasets based on the prediction of the first model. Next, we train two regression models to predict distance. Finally, we combine the two models in order to evaluate the Cascade as a whole.

To try the notebook you will need to change its first cell.
So, open the notebook in Cloud AI Platform Notebooks.

This notebook is adapted from the
O'Reilly book: Title: Machine Learning Design Patterns Authors: Valliappa (Lak) Lakshmanan, Sara Robinson, Michael Munn

https://github.com/GoogleCloudPlatform/ml-design-patterns

