## Vibration Anomaly Detection — Report

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
- The alert module initially allowed only one alert type during each prediction period. A lock prevented repeated alerts, even when a new anomalous event included a significant escalation. So some new events within the same input were being missed.
- In some observations, the model flagged a period with almost no movement, this period had `uptime = False` , which indicates that the machine was not operating. The model flagged as anomaly a period that the machine was not running, which does not make sense.
- In some cases, an anomaly was visible in the acceleration signal but not in velocity, which is the only signal used by the baseline model, so the model is not seing the event. And, as learnt from a quick research, it makes sense: some types of failures are only detectable in the Acceleration signal and some only in the Velocity. So different failure types produce different vibration signatures:

  - Examples of Failures detectable in each type of signal:
    - Velocity: rotor unbalance, shaft misalignment, mechanical looseness, and others.
    - Acceleration: early roolling-element bearing defects, gear mesh wear, and others.
- In some cases, the anomaly had low intensity, and was not detected with the selected hyperparameter.

## Methodology

Due to the nature of the problem and need of being able to explain the model behaviour over the results, the approach was to improve the current model and keep the solution as simple and interpretable as possible.

The investigation process started by looking at the plots with the predicted alerts and the true incident periods and trying to understand the reason of the predictions. It was observed that the `window_anomaly_ratio` hyperparameter value was too low, and because of that, the model was considering any small disturbance in the signal as anomaly, and that, connected with the fact of not alerting again in the same input, the model was not getting the right point of anomaly.

With this in mind and looking at the periods where the real anomaly happens, it was observed that the ratio of points over the mean of the signal in the anomaly areas were higher than 20%, which motived to a manual search for the best value of this hyperparameter for this dataset. This search found 0.7 to be the best value, solving one of the problems. Increasing the ratio reduced false positives and missed incident periods. This baseline model with this small change was also tagged in the repository, just for consideration, as `v1.1.0` and produced these metrics:

| Experiment                                   | True Positive | False Positive | False Negative | Precision | Recall | F1-Score |
| -------------------------------------------- | ------------- | -------------- | -------------- | --------- | ------ | -------- |
| Baseline with 0.7 as anomaly ratio (V1.0.0) | 9             | 3              | 20             | 0.750     | 0.310  | 0.439    |

This model perfomed better than baseline: it detected more True positives and decreased the cases of false negatives, increasing precision and recall, which was still low because some real incidents were missed. Regarding the F1-Score, it is basically an harmonic mean of these two metrics (Precision and Recall), so the moment that the false negatives are solved, the Recall should increase, bringing together the F1-Score.

The next problem to be addressed was the single alert one. For this, a new logic was implemented in the `alert_engine` module using a cooldown period before sending another anomaly alert and an escalation score. After analysing the data, it was observed that when more than one anomaly occurred in the same input, it happened more than one day apart from the others. Therefore, the cooldown was set to 48 hours. When this cooldown was added, an increase in false positives was observed because, at some points, an alert was being triggered even though the anomaly had not increased. Because of that, a new logic was implemented to verify whether the new anomaly had increased compared with the last alerted one. Several possible solutions were tested, such as the `z_score`, and the best approach found was `deviation_score`, which is the mean of the positive differences between `z_score` and `zscore_threshold`. Thus, a new alert is allowed only when the new alert has a higher `deviation_score`.

 To complement this solution, two additional hyperparameters were added. They have not yet been thoroughly explored, but they currently appear to be the best choices for this data. They are `escalation_margin` and `recovery_windows`. The first adjusts how much the anomaly must increase for the solution to trigger an alert, while the second defines the minimum number of consecutive normal windows required to unlock the alert engine after an anomaly. This second mechanism is similar to the cooldown alert and is intended to avoid re-alerting for the same ongoing issue.

For the third problem, the implementation was simple: a check was added to the `anomaly_model` to prevent a window from being flagged as anomalous when the `uptime` flag is false. This avoids false anomalies, as a high z-score may occur simply because the machine is not running. In this example, the metric observed by the model would normally trigger an anomaly, but the purpose of the solution is to determine whether the condition is caused by a machine problem or is merely a normal operating state.

The model developed until here, with all this modifications, was tagged in this repo as `v2.0.0`, and its performance will be discussed in the next section.

To address the domain anomaly problem, the `anomaly_model` was extended to incorporate accelerometer and apply the same fitting and feature-extraction process to acceleration as to velocity, it now stores the mean and standard deviation of the acceleration-vector magnitude as model weights. Initial tests applied the same detection logic and hyperparameters to both signals, allowing either to flag a window. This increased false positives, suggesting that the acceleration hyperparameters require further tuning or that a different fusion strategy should be explored. This model was tagged as `v2.1.0` and it contains the acceleration new hyperparams support, but its values  were raised to limit their influence on predictions; as a result, its performance remained the same as `v2.0.0`.

CHECK THIS:

For the last detected problem, a study should have been conducted regarding the data to understand its ranges and limitations. And also, it should have been interesting to use some other formats for the accelerometer, for example, to analyse the data in the frequency domain, with a Fourier Discrete Tranformation, DFT, since the signal does not contain information in the amplitude, it might have in the frequencies on it, although with the given input, aceleromenter in RMS would not produce much improvements, it would need the raw signal. More about this ideia will be discussed in the Future Work section.

Disclaimers: the pipeline hyperparams were changed a little as a testing, but they looked to be condizent with the data and did seen to need to be changed. Some tests were conducted and presented worse metrics than the ones achieved so far. Maybe a more structered tune might be needed for these params, more will be talked in the Future Work section.

During the investigation process, lots of models were tested, with few modifications, which guided the full acknowledge of the problems and gave the insights to solve them. Some tests do not worth mentioning all the details, but their metrics were computed and stored in the `compare_experiment_metrics.ipynb` notebook, which was implemented to facilitate the aggregation and comparison of the metrics generated by the models. All the names of the experiments in there were given relative to their caracteristics, hyperparams or different logic applied.

## Performance

The final best model, with the implementations that were possible to develop, in this challenge period, tagged as `v2.0.0` and with following settings:

- Model Hyperparams:

  - `window_anomaly_ratio = 0.7`;
  - `z_threshold = 3`;
  - `acceleration_z_threshold = 10`;
  - `acceleration_window_anomaly_ratio = 1`;
- Pipeline Hyperparams:

  - `model_window_size_hours = 2`;
  - `window_overlap_hours: 1`;
- Uptime filtering logic implemented, requiring every sample in a window to have
  `uptime = True`;
- Alert Hyperparams (added in the hyperparameters folder):

  - `cooldown_hours = 48`;
  - `escalation_margin = 0.0`;
  - `recovery_windows = 100`;

This model produced the following results:

| Experiment        | True Positive | False Positive | False Negative |       Precision |          Recall |        F1-Score |
| ----------------- | ------------: | -------------: | -------------: | --------------: | --------------: | --------------: |
| Baseline (V1.0.0) |             5 |             14 |             24 |           0.263 |           0.172 |           0.208 |
| v2.0.0            |  **12** |    **3** |   **17** | **0.800** | **0.414** | **0.545** |

Looking at these metrics and the preditcions, we can verify that some problems were resolved and some still persists. The True Positive increased, 5 -> 12, the False Positive and the False Negatives decreased, 14 -> 3, 24 -> 17, respectively.
This best model achieved so far, increased its performance, comparing to the baseline: it is more sensible to some events while avoiding to predict false anomalies, only 3 were done. It is still not a very good model, it misses more than a half of the anomalies, which can be visualized by the recall metric, 0.414.

The great improvement this model brought was the increase of the correct predictions, while decreasing the false ones.

## Future Work

This achieved model, although increased the performance, it still lacks for detection anomalies in the accelerometer domain and the strategies tested so far, did not produced any improvement, only more false negatives. So that, other strategies should be studied with it, a deep analysis to fit data and the predict, to understand what might be the best form to integrate this other input in the decision pipeline and differentiate the normal signal to the disturbed one.

 Another strategy that would be interesting was to convert the signal do the frequency domain, as pointed before. This would be achieved by passing the signal to a Discrete Fourier Transform (DFT) and maybe comparing the highest energy frequencies with the  ones from the fit data, and check if anything different appeared. This strategy looks promissing but it needs some attentions and probably will not work for these input data because of the sampling rate, needing to be careful about the Nyquist frequency, to avoid aliasing and losing the interested signal, and the caracteristics of it, the acelerometer is in RMS, which probably took part of its frequency information. A deeper study need to be conducted to understand the correct behaviour of this operations and also the sampling frequency.

Also, the hyperparameters were chosen manually using the full prediction dataset. A more robust technique would be grouped cross-validation, splitting the data by scenario so that each asset’s windows remain together. This would help select parameters on training scenarios and evaluate them on unseen scenarios, improving its performance and reducing the risk of overfitting.
Also the pipeline hyperparams were changes to test, but not much well explored. Same analysis for them.

Besides that, given more time, further analysis of the input data could reveal opportunities to improve the model, such as evaluating the three axes separately to preserve axis-specific information.
Also, thinking of more complex techniques, such as an autoencoder trained on normal, normalized acceleration and velocity readings, could also be explored, using reconstruction error to identify anomalies.

## Project Notes

For better visualization a notebook, that reads the experiment outputs page and retrieves the final metrics of the model, was created, `compare_experiment_metrics.ipynb`. And also, for visualization, since the `main.py` could not be changed, a copy of it was created, `main_tqdm.py` and a tqdm, library that shows the progress of a iteration, was added to the scenarios iteration. The model works the same way for the main.py and the main_tqdm.py.

 Disclaimer, generative AI was used in this project only for the creation of the compare_experiment_metrics notebook, the tqdm main, to search and fix some implementation bugs, and to review some parts of this report. But the full exploration, analysis and solving strategies were thought by me.
