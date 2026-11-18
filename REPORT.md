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

# Vibration Anomaly Detection — Report

## Understanding the Baseline Solution

The provided solution uses a model that receives fitted data in the form of a time series containing velocity and acceleration RMS signals along three axes, UTC timestamps for each sample, and a boolean machine-status flag indicating whether the machine is running. The model calculates features for the velocity signal and learns their caracteristics using the mean and standard deviation. The feature is the norm of the velocity vector (magnitude), calculated from the X, Y and Z axis signals:
				Velocity magnitude = √(Vx² + Vy² + Vz²)
After the fitting step, the model receives prediction data, during the prediction phase. For each window, it uses the mean and standard deviation learned from the fitted data to calculate the z-score of every sample, which is a computation of how many standard deviations a sample is from the mean.

The anomaly detection model basically determines wheter a window contains an anomaly based on the proportion of samples exceeding the a z-score threshold. For example,  a window is considered anomalous if more than 20% of its samples (`window_anomaly_ratio` hyperparameter) have more than 3 standard deviations (`z_threshold` hyperparameter) over the mean of the fitted data.
This baseline model, tagged in this repository as `V1.0.0`,  produced the following metrics:

| Experiment        | True Positive | False Positive | False Negative | Precision | Recall | F1-Score |
| ----------------- | ------------- | -------------- | -------------- | --------- | ------ | -------- |
| Baseline (V1.0.0) | 5             | 14             | 24             | 0.263     | 0.172  | 0.208    |

These metrics indicate poor performance and tell us what are the problems with this model: It classifies few windows as anomallies (5 True Positives, misses 24) and classifies as anomallies lots of cases that are not (14 False Positives).

## Baseline Analysis

After studying the model and its behaviour within the prediction data, several reasons for this poor performance could be identified:

- The hyperparameters were not well ajusted for the dataset: Changing the `window_anomaly_ratio` in`model_hyperparameters.yaml` increased the results.
- The alert module initially allowed only one alert type during each prediction period. A lock prevented repeated alerts, even when the same ongoing state included a significant escalation, project .
- In some observations, the model flagged a period with almost no movement. This period had `uptime = False` , which indicates that the machine was not operating.
- In some cases, an anomaly was visible in the acceleration signal but not in velocity, which is the only signal used by the baseline model. And as learnt from a quick research; some types of failures are only detectable in the Acceleration signal and some only in the Velocity. So Different failure types produce different vibration signatures:

  - Examples of Failures detectable in each type of signal:
    - Velocity: rotor unbalance, shaft misalignment, mechanical looseness, and others.
    - Acceleration: early roolling-element bearing defects, gear mesh wear, and others.
- In some cases, the anomaly had low intensity, and was not detected with the selected hyperparameter.

## Methodology

Due to the nature of the problem and need of being able to explain the model behaviour over the results, the approach was to improve the results and keep the solution as simple and interpretable as possible.

The investigation process started by looking at the plots with the predicted alerts and the true incident periods and trying to understand the reason of the predictions. It was observed that the `window_anomaly_ratio` hyperparameter value was too low, and because of that, the model was considering any small disturbance in the signal as anomaly, and that, connected with the fact of not alerting again in the same input, the model was not getting the right point of anomaly. 

With this in mind and looking at the periods where the real anomaly happens, it was observed that the ratio of points over the mean of the signal in the anomaly areas were higher than 20%, which motived to a manual search for the best value of this hyperparameter for this dataset. This search found 0.7 to be the best value, solving one of the problems. Increasing the ratio reduced false positives and missed incident periods. This baseline model with this small change was also tagged in the repository, just for consideration, as `v1.1.0` and produced these metrics:

| Experiment                                   | True Positive | False Positive | False Negative | Precision | Recall | F1-Score |
| -------------------------------------------- | ------------- | -------------- | -------------- | --------- | ------ | -------- |
| Baseline with 0.7 as anomaly ratio (V1.0.0) | 9             | 3              | 20             | 0.750     | 0.310  | 0.439    |

This model perfomed better than baseline: it detected more True positives and decreased the cases of false negatives, increasing precision and recall, which was still low because some real incidents were missed. Regarding the F1-Score, it is basically an harmonic mean of these two metrics (Precision and Recall), so the moment that the false negatives are solved, the Recall should increase, bringing togheter the F1-Score.

The next problem to be addressed was the single alert one. For this, a new logic was implemented in the `alert_engine` module using a cooldown period before sending another anomaly alert and an escalation score. After analysing the data, it was observed that when more than one anomaly occurred in the same input, it happened more than one day apart from the others. Therefore, the cooldown was set to 48 hours. When this cooldown was added, an increase in false positives was observed because, at some points, an alert was being triggered even though the anomaly had not increased. Because of that, new logic was implemented to verify whether the new anomaly had increased compared with the last alerted one. Several possible solutions were tested, and the best approach was `deviation_score`, which is the mean of the positive differences between `z_score` and `zscore_threshold`. Thus, a new alert is allowed only when the new alert has a higher `deviation_score`.

 To complement this solution, two additional hyperparameters were added. They have not yet been thoroughly explored, but they currently appear to be the best choices for this data. They are `escalation_margin` and `recovery_windows`. The first adjusts how much the anomaly must increase for the solution to trigger an alert, while the second defines the minimum number of consecutive normal windows required to unlock the alert engine after an anomaly. This second mechanism is similar to the cooldown alert and is intended to avoid re-alerting for the same ongoing issue.

For the third problem, the implementation was simple: a check was added to the `anomaly_model` to prevent a window from being flagged as anomalous when the `uptime` flag is false. This avoids false anomalies, as a high z-score may occur simply because the machine is not running. In this example, the metric observed by the model would normally trigger an anomaly, but the purpose of the solution is to determine whether the condition is caused by a machine problem or is merely a normal operating state.

## Performance

## Future Work
