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
