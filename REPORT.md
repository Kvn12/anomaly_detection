# First Observations



There is the columns of if the machin was working in that time. Maybe use this to avoid flagging in moments that it does not make sense. Only calculate the metrics when the machine was running.

For the cases that have very low signal, analyse if any math operation should be conducted to avoid that, keep in the same scale -> talvez nda a ver essa ideia

## First Modifications to Improve Performance

1. Study data to better ajust hyperparameters manually and look at results and get other insights.

## Improvements in the Future

1. Use accelerometer as well.

## Tests performed

1. changed to 0.7 of anomaly ratio, increased accuracy
2. allowed to flag more than once at periods of 24 h -> increased recall, decreased precision
3. Removed times where uptime false in fit, bad results, for now. May need to ajust the zscore threshold.
4. Changed to use only ACC, not enough
5. Does not flag if any uptime in the window (may be careful).

# Challenge Report

## Understanding the Baseline Solution

The given solution is a model that receives a fit data, a timeseries containing Velocity RMS along three axis (mm/s) and Acceleration RMS along three axis (g) signals, the UTC timestamp for each sample and a boolean flag about the machine status (running or not), calculates the features for the velocity input and learns the caracteristics from this signal: Mean and Standard deviation. The features are basically the norm of the velocity vector, which is composed by the 3 axis signals (X, Y, Z).
After this fit step, it receives, during the prediction fase, the prediction data, for each window, using the weight and the standard deviation, learnt from the fit data, calculates the zscore for each sample in the window, which is basically a computation of how many standard deviations the point is above the mean of the dataset, in this case.

The anomaly detection model is basically a decision of how many points, within the window, with more than a threshold value of standard deviations above the mean are considered an anomally. For example, if there is in the window more than 0.2 samples (`window_anomaly_ratio` hyperparameter) that are more than 3 standard deviations (`z_threshold` hyperparameter) above the mean of the fit data, than this window is considereded to contain an anomally.
This baseline model, tagged in this branch as `V1.0.0`,  was run and the metrics were calculated, which were:

| Experiment        | True Positive | False Positive | False Negative | Precision | Recall | F1-Score |
| ----------------- | ------------- | -------------- | -------------- | --------- | ------ | -------- |
| Baseline (V1.0.0) | 5             | 14             | 24             | 0.263     | 0.172  | 0.208    |

These metrics are not good metrics, and tell us what are the problems with this model: It classifies few windows as anomallies (5 True Positives, misses 24) and classifies as anomallies lots of parts that are not (14 False Positives).

## Baseline Weaknesses

After studying the model and its behaviour within the prediction data, a few reasons for this poor performance could be found:

- The hyperparameters are not well ajusted to the dataset: a simple change in the `window_anomaly_ratio`from the `model_hyperparameters.yaml` config and it produces better results.
- The alert module does not report more than one case as anomally per prediciton data: there is a `lock` argument that prevents that from happening and in the requirements of the project, it should alert again after the anomaly period if it has increased.
- In some data, the anomally cannot be seen in the Velocity signal, which is what the model sees; it exists only in the Accelerometer one, and this is physically explainable, as learnt from a quick research; some types of failures are only detectable in the Acceleration signal and some only in the Velocity.
  - Examples of Failures detectable in each type of signal:
    - Velocity: rotor unbalance, shaft misalignment, mechanical looseness, and others.
    - Acceleration: early roolling-element bearing defects, gear mesh wear, and others.
- TALK ABOUT THE PREDICTIONS IN MOMENTS THAT THE MACHINE IS NOT ON?
- CHECK THIS In some cases, the first, for example, it does not flag, probably because the signal is lower than the fit data. An option would be to save the mean and std for the current data, not only the fit one. If it does not flag based on the fit one, it may flag in the predict.
