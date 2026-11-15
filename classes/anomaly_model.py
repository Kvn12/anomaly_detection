from pathlib import Path

import numpy as np
import yaml

from .interface import ModelParams, PredictOutput, TimeSeries, Weights

DEFAULT_PARAMS_PATH = Path("hyperparameters/model_hyperparams.yaml")


def load_model_params(path: Path = DEFAULT_PARAMS_PATH) -> ModelParams:
    """Load model hyperparameters from YAML. Falls back to ModelParams defaults if file missing."""
    if not path.exists():
        return ModelParams()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return ModelParams(**data)


class AnomalyModel:
    def __init__(self, params_path: Path | None = None):
        self.weights_a = Weights()
        self.weights_v = Weights()
        self.params = load_model_params(params_path or DEFAULT_PARAMS_PATH)
        self.last_deviation_ratio_v = 0.0

    def _featuring(self, samples: TimeSeries) -> np.ndarray:
        if not samples.data:
            return np.array([], dtype=float)

        ordered = sorted(samples.data, key=lambda p: p.timestamp)

        vel = np.array([(p.vel_x, p.vel_y, p.vel_z) for p in ordered], dtype=float)
        acc = np.array([(p.acc_x, p.acc_y, p.acc_z) for p in ordered], dtype=float)

        return np.linalg.norm(acc, axis=1), np.linalg.norm(vel, axis=1)

    def fit(self, fitting_samples: TimeSeries) -> None:
        # uptime_samples = TimeSeries(
        #     data=[sample for sample in fitting_samples.data if sample.uptime]
        # )
        # if not uptime_samples.data:
        #     raise ValueError("Cannot fit: no samples with uptime=True")

        # X = self._featuring(uptime_samples)
        Xa, Xv = self._featuring(fitting_samples)

        self.weights_a = Weights(
            fitted=True,
            mean=round(Xa.mean(), 3),
            std=round(Xa.std(), 3),
        )
        self.weights_v = Weights(
            fitted=True,
            mean=round(Xv.mean(), 3),
            std=round(Xv.std(), 3),
        )

    def _zscore(self, X: np.ndarray) -> np.ndarray:
        Xa, Xv = X
        w_a = self.weights_a
        w_v = self.weights_v
        return np.abs((Xa - w_a.mean) / w_a.std), np.abs((Xv - w_v.mean) / w_v.std)
        # return (Xa - w_a.mean) / w_a.std, (Xv - w_v.mean) / w_v.std

    def _window_deviation_ratio(self, X: np.ndarray) -> float:
        z_a, z_v = self._zscore(X)
        anomalous_points_a = z_a > self.params.z_threshold
        anomalous_points_v = z_v > self.params.z_threshold
        return float(np.sum(anomalous_points_a) / len(z_a)), float(np.sum(anomalous_points_v) / len(z_v))

    def predict(self, samples: TimeSeries) -> PredictOutput:
        if not self.weights_a.fitted or not self.weights_v.fitted:
            raise RuntimeError("Model not fitted")
        if not samples.data:
            raise ValueError("Cannot predict on empty TimeSeries")

        X = self._featuring(samples)
        deviation_ratio_a, deviation_ratio_v = self._window_deviation_ratio(X)
        # is_anomalous = False
        # if deviation_ratio_a >= self.params.window_anomaly_ratio or deviation_ratio_v >= self.params.window_anomaly_ratio:
        #     is_anomalous = True
        is_anomalous = deviation_ratio_v >= self.params.window_anomaly_ratio
        # if is_anomalous and (deviation_ratio_v >= self.last_deviation_ratio_v):
        #     self.last_deviation_ratio_v = deviation_ratio_v
        #     is_anomalous = True
        # else:
        #     is_anomalous = False

        if any(not sample.uptime for sample in samples.data):
            is_anomalous = False

        return PredictOutput(
            anomaly_status=is_anomalous,
            timestamp=samples.data[-1].timestamp,
        )
