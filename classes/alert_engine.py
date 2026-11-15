import datetime
from pathlib import Path

import yaml

from .interface import AlertDecision, AlertParams, PredictOutput

DEFAULT_PARAMS_PATH = Path("hyperparameters/alert_hyperparams.yaml")


def load_alert_params(path: Path = DEFAULT_PARAMS_PATH) -> AlertParams:
    """Load alert hyperparameters from YAML. Falls back to AlertParams defaults if the file is missing."""
    if not path.exists():
        return AlertParams()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return AlertParams(**data)


class AlertEngine:
    def __init__(
        self,
        params_path: Path | None = None,
    ):
        self.params = load_alert_params(params_path or DEFAULT_PARAMS_PATH)
        self.locked = False
        self.last_alert_timestamp: datetime | None = None

    def _has_alert(self, prediction: PredictOutput) -> bool:
        return prediction.anomaly_status

    def predict(self, prediction: PredictOutput) -> AlertDecision:
        if not self._has_alert(prediction):
            return AlertDecision(
                alert=False,
                timestamp=prediction.timestamp,
                message="No persistent abnormal vibration.",
            )

        if self.locked:
            if self.last_alert_timestamp is None:
                self.last_alert_timestamp = prediction.timestamp
            if (
                prediction.timestamp - self.last_alert_timestamp
                <= datetime.timedelta(hours=self.params.cooldown_hours)
            ):
                return AlertDecision(
                    alert=False,
                    timestamp=prediction.timestamp,
                    message="System already entered abnormal state earlier.",
                )

        self.locked = True
        self.last_alert_timestamp = prediction.timestamp
        return AlertDecision(
            alert=True,
            timestamp=prediction.timestamp,
            message="Abnormal vibration detected.",
        )
