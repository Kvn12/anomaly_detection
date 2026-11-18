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

## Baseline Analysis

After studying the model and its behaviour within the prediction data, a few reasons for this poor performance could be considered:

- The hyperparameters are not well ajusted to the dataset: a simple change in the `window_anomaly_ratio`from the `model_hyperparameters.yaml` config and it produced better results.
- The alert module does not report more than one case of anomally per prediciton data: there is a `lock` argument that prevents that from happening. In the requirements of the project, it establishes that another alert should be given after the anomaly period, if it has happened again and increased.
- As observed in some data, the model was alerting a failure at a time of almost no movement, as checked later, was a moment where the flag of machine operation was False (uptimecolumn of the input time series).
- In some data, the anomally cannot be seen in the Velocity signal, which is what the only thing model sees; it exists only in the Accelerometer one, and this is physically explainable, as learnt from a quick research; some types of failures are only detectable in the Acceleration signal and some only in the Velocity. So if the anomaly happening is only detectable in the Acceleration, if the model is not seing it, it will not detect.

  - Examples of Failures detectable in each type of signal:
    - Velocity: rotor unbalance, shaft misalignment, mechanical looseness, and others.
    - Acceleration: early roolling-element bearing defects, gear mesh wear, and others.
- In some cases, it was observed that the anomaly had low intensity, and that intensity was not enough to detect, considering the chosen hyperparameters.

## Methodology

The solution mindset for this challenge was to try using the simplest strategies first, due to the nature of the problem and need of being able to explain the model behaviour over the results; since that, no complex algorithms were used, only clear and explanaible methods.
The investigation process started by looking at the plots with the predicted alerts and trying to understand the reason of the predictions. And right in the beginnig, was observed that the `window_anomaly_ratio` hyperparameter value was very low, and because of that, the model was considering any little disturb in the signal as anomaly, and that, connected with the fact of not alerting again in the same input, the model was not getting the right point of anomaly. With this in mind and looking at the periods where the real anomaly happens, it was observed that the ratio of points over the mean of the signal in the anomaly areas were higher than 0.2, which motived to a manual search for the best value of this hyperparameter for this dataset. This search found out that the best value was 0.7, solving one of the problems. This baseline model with this small change was also tagged in the repository, just for consideration, as `v1.1.0` and produced these metrics:

| Experiment                                   | True Positive | False Positive | False Negative | Precision | Recall | F1-Score |
| -------------------------------------------- | ------------- | -------------- | -------------- | --------- | ------ | -------- |
| Baseline with 0.7 as anomaly ratio (V1.0.0) | 9             | 3              | 20             | 0.750     | 0.310  | 0.439    |

This model was already better than baseline, it detected more True positives and decreased a lot the cases of false negatives, which was responsible for the increase of the Precision metric and the recall, which this last one was still low because of the false negatives. Regarding the F1-Score, it is basically an harmonic mean of these two metrics (Precision and Recall), so the moment that the false negatives are solved, the Recall should increase, bringing togheter the F1-Score.

After this problem appeared to be solved, the next one to be addressed was the single alert one. For this, a new logic was implemented in the `alert_engine` module, which add a cooldown time before sending another anomaly alert. Analysing the data, was observed that when more than one anomaly happened in the same input, it happend more than 1 day apart from it each other. Because of that, as a cooldown, it was chosen 48 hours for this new hyperparameter. When adding this, it was observed an increase of false positives, because in some moments it was alerting, but was not even an increase in the anomaly. Because of that, a new logic was implemented that verifies if this new anomaly has increased over the last alerted one. Some possible solutions were tested, and the best one to address this was `deviation_score`, which is the mean of the positive differences between the `z_score` and the `zscore_threshold`,  so if the new alert has a higher `deviation_score`, it is allowed to alert. To complement this solution, two other hyperparameters were added, and not well explored yet, but at seems, they are the best ones for this data, in the moment. They are the `escalation_margin`and the`recovery_windows`. The first one is to ajust of how much increase in the anomaly that the solution will consider to alert, and the second one is the minimum number of consecutive normal windows to unlock the alert engine after an anomaly, which is very close to the cooldown alert and it is to avoid the realert for the same ongoing problem.

For the solution of the third problem listed before, the implementation was simple, just the addition of a verification in the `anomaly_model`that if the ``uptime`` flag is false, it dos not flag as an anomaly, since the high zscore is due to the fact of the machine not runnning. In this example case, the metric observed by the model has a value to be flagged, but the ideia of the solution is to interpretate if the case of attention is due to a problem or just a moment of operation.



## Performance

## Future Work
