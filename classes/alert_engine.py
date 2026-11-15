from .interface import AlertDecision, PredictOutput
import datetime


class AlertEngine:
    def __init__(
        self,
    ):
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
                <= datetime.timedelta(hours=24)
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
