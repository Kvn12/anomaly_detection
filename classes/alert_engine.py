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
        self.last_alerted_score: float | None = None
        self.consecutive_normal_windows = 0

    def _has_alert(self, prediction: PredictOutput) -> bool:
        return prediction.anomaly_status

    def _no_alert(self, prediction: PredictOutput, message: str) -> AlertDecision:
        return AlertDecision(
            alert=False,
            timestamp=prediction.timestamp,
            message=message,
        )

    def _send_alert(self, prediction: PredictOutput) -> AlertDecision:
        self.locked = True
        self.last_alert_timestamp = prediction.timestamp
        self.last_alerted_score = prediction.deviation_score
        self.consecutive_normal_windows = 0
        return AlertDecision(
            alert=True,
            timestamp=prediction.timestamp,
            message="Abnormal vibration detected.",
        )

    def predict(self, prediction: PredictOutput) -> AlertDecision:
        if not prediction.uptime_valid:
            self.consecutive_normal_windows = 0
            return self._no_alert(prediction, "Machine is not operating.")

        if not self._has_alert(prediction):
            if self.locked:
                self.consecutive_normal_windows += 1
                if self.consecutive_normal_windows >= self.params.recovery_windows:
                    self.last_alerted_score = None
                    self.consecutive_normal_windows = 0
            return self._no_alert(
                prediction,
                "No persistent abnormal vibration.",
            )

        self.consecutive_normal_windows = 0
        if not self.locked:
            return self._send_alert(prediction)

        # check if cooldown period has elapsed 
        cooldown_elapsed = (
            self.last_alert_timestamp is None
            or prediction.timestamp - self.last_alert_timestamp
            > datetime.timedelta(hours=self.params.cooldown_hours)
        )
        # check if the anomaly has escaleted
        score_escalated = (
            self.last_alerted_score is None
            or prediction.deviation_score
            > self.last_alerted_score + self.params.escalation_margin
        )
        if cooldown_elapsed and score_escalated:
            return self._send_alert(prediction)

        return self._no_alert(
            prediction,
            "System already entered abnormal state earlier.",
        )
