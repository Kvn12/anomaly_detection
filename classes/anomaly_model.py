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

    def _featuring(
        self, samples: TimeSeries
    ) -> tuple[np.ndarray, np.ndarray]:
        if not samples.data:
            empty = np.array([], dtype=float)
            return empty, empty

        ordered = sorted(samples.data, key=lambda p: p.timestamp)

        vel = np.array([(p.vel_x, p.vel_y, p.vel_z) for p in ordered], dtype=float)
        acc = np.array([(p.acc_x, p.acc_y, p.acc_z) for p in ordered], dtype=float)

        return np.linalg.norm(acc, axis=1), np.linalg.norm(vel, axis=1)

    def fit(self, fitting_samples: TimeSeries) -> None:
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

    def _zscore(
        self, X: tuple[np.ndarray, np.ndarray]
    ) -> tuple[np.ndarray, np.ndarray]:
        Xa, Xv = X
        w_a = self.weights_a
        w_v = self.weights_v
        return np.abs((Xa - w_a.mean) / w_a.std), np.abs((Xv - w_v.mean) / w_v.std)

    def _window_deviation_metrics(
        self, X: tuple[np.ndarray, np.ndarray]
    ) -> tuple[float, float, float]:
        z_a, z_v = self._zscore(X)
        anomalous_points_a = z_a > self.params.z_threshold
        anomalous_points_v = z_v > self.params.z_threshold
        deviation_ratio_a = float(np.mean(anomalous_points_a))
        deviation_ratio_v = float(np.mean(anomalous_points_v))
        # calculate the deviation score as the mean of the excess z-scores above the threshold
        deviation_score = float(
            np.mean(np.maximum(z_v - self.params.z_threshold, 0.0))
        )
        return deviation_ratio_a, deviation_ratio_v, deviation_score

    def predict(self, samples: TimeSeries) -> PredictOutput:
        if not self.weights_a.fitted or not self.weights_v.fitted:
            raise RuntimeError("Model not fitted")
        if not samples.data:
            raise ValueError("Cannot predict on empty TimeSeries")

        X = self._featuring(samples)
        deviation_ratio_a, deviation_ratio_v, deviation_score = self._window_deviation_metrics(X)
        uptime_valid = all(sample.uptime for sample in samples.data)
        is_anomalous = (
            deviation_ratio_v >= self.params.window_anomaly_ratio and uptime_valid
        )

        return PredictOutput(
            anomaly_status=is_anomalous,
            timestamp=samples.data[-1].timestamp,
            deviation_score=deviation_score,
            uptime_valid=uptime_valid,
        )
