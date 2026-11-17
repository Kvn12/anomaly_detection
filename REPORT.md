# First Observations

There is a solution and apparently the hyperparameters are not well ajusted, a simple modification in the window_anormaly_ratio produced better results.
Due to that, a study with the fit data, should be conducted to choose better hyperparameters.

Also, looking at the plots, and knowing that only the velocity input is being used, in some data, velocity it is not enough to predict a failure. In the first scenario, the information about failure is apparently only present in the accelerometers. A further study should be conducted on that.

We have points where the velocity and acceleration drops to less than 1, and this triggers the alert. (Fix this)  -> this depends on the zcore_threshold, in one case it did not flagged

Not flagging the second problem -> it might flag it, the problem is to flag more than once on the same on going event. Never flags the second event.

There is the columns of if the machin was working in that time. Maybe use this to avoid flagging in moments that it does not make sense. Only calculate the metrics when the machine was running.

Lots of false positives, in many cases flagging nothing

Lots of false negatives. Probably because of flagging the nothing and not flaggin at all

Change the 0.7, for something around

Use acc, not enough

Combine ACC and Velocity, test other strategy

Only positive variations, not good enough

Do not predict if not running -> check this better -> If there is any sample that was not uptime, does not flag

In some cases, the first, for example, it does not flag, probably because the signal is lower than the fit data. An option would be to save the mean and std for the current data, not only the fit one. If it does not flag based on the fit one, it may flag in the predict.

Keep the last state it flagged, may consider that for the next flags -> if increased considering the last flag.

Increase the stride, overlap. -> 1.5 produced same results -> 3 and 2 produced a little bit worse results

For the cases that have very low signal, analyse if any math operation should be conducted to avoid that, keep in the same scale -> talvez nda a ver essa ideia

## First Modifications to Improve Performance

1. Study data to better ajust hyperparameters manually and look at results and get other insights.
2. Include the is running in the fit proccess.
3. Fix the second alert problem.

## Improvements in the Future

1. Automate this study proccess. Include this in the pipeline somehow, using the labels, dont have labels.
2. Use accelerometer as well.

## Tests performed

1. changed to 0.7 of anomaly ratio, increased accuracy
2. allowed to flag more than once at periods of 24 h -> increased recall, decreased precision
3. Removed times where uptime false in fit, bad results, for now. May need to ajust the zscore threshold.
4. Changed to use only ACC, not enough
5. Does not flag if any uptime in the window (may be careful).

# Challenge Report

## Understanding the Baseline Solution

The given solution is a model that receives a fit data, a timeseries containing Velocity RMS along three axis (mm/s) and Acceleration RMS along three axis (g) signals, the UTC timestamp for each sample and a boolean flag about the machine status (running or not), calculates the features for the velocity input and learns the caracteristics from this signal: Mean and Standart deviation. The features is basically the norm of the velocity vector, composed by the 3 axis signals (X, Y, Z).
After this fit step, it receives, during the prediction fase, the prediction data, for each window, using the weight and the standartd deviation, learnt from the fit data, calculates the zscore for each sample in the window. The zscore is basically a computation of how many standard deviations the point is far from the mean of the dataset, above or below.

The anomaly detection model is basically a decision of how many points, within the window, with more than a threshold value of standard deviations above the mean is considered an anomally. For example, if in the window more than 0.2 samples are more than 3 standard deviations above the mean of the fit data, than this window is considereded an anomally.
This baseline model was run and the metrics were calculated, which are:

Preciosion: 0.263 Recall: 0.172 and F1Score: 0.208
With the predictions being:
True Positives: 5 False Positives: 14 False Negatives: 24

These are not good metrics, which means the model does not perform very good: It Classifies few windows as anomallies (True Positives) and classifies lots of cases as anomallies that are not anomallies (False Positives).

## Baseline Weaknesses

After studying the model and its behaviour within the prediction data, a few reasons for this poor performance could be found:

- The hyperparameters are not well ajusted to the model: a simple change in the `window_anomaly_ratio`from the `model_hyperparameters.yaml` config and it produces better results.
- The alert module does not reports more than one case on anomally per prediciton data: there is lock argument that prevents that from happening.
- In some data, the anomally cannot be seen in the Velocity signal which is what the model sees; it exists only in the Accelerometer one, and this is physically explainable, some types of failures are only detectable in the Acceleration signal and some only in the Velocity.
  - Examples of Failures detectable in each type of signal:
    - Velocity: rotor unbalance, shaft misalignment, mechanical looseness, and others.
    - Acceleration: early roolling-element bearing defects, gear mesh wear, and others.
