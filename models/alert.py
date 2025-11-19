"""
Alert domain model for notifications and triggers.
"""

from sqlalchemy import Column, String, Float, Integer, Text, DateTime
from sqlalchemy.orm import validates
from models.base import BaseModel
from datetime import datetime, timezone


class Alert(BaseModel):
    """
    Alert model for price and indicator-based notifications.
    Supports various alert types and trigger conditions.
    """

    __tablename__ = "alerts"

    symbol = Column(String(20), nullable=False, index=True)
    alert_type = Column(String(30), nullable=False, index=True)  # PRICE, INDICATOR, RISK, NEWS
    trigger_condition = Column(String(50), nullable=False)  # ABOVE, BELOW, CROSSES_ABOVE, CROSSES_BELOW, EQUALS
    threshold_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=True)
    message = Column(Text, nullable=False)
    priority = Column(String(10), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    is_active = Column(Integer, nullable=False, default=1)  # Boolean as int
    is_triggered = Column(Integer, nullable=False, default=0)  # Boolean as int
    triggered_date = Column(DateTime, nullable=True)
    notification_sent = Column(Integer, nullable=False, default=0)  # Boolean as int
    alert_metadata = Column(Text, nullable=True)  # JSON string for additional data

    @validates('alert_type')
    def validate_alert_type(self, key: str, value: str) -> str:
        """
        Validate alert type.

        Args:
            key: Field name
            value: Alert type value

        Returns:
            Validated value

        Raises:
            ValueError: If alert type is invalid
        """
        valid_types = ["PRICE", "INDICATOR", "RISK", "NEWS", "PORTFOLIO"]
        if value not in valid_types:
            raise ValueError(f"Invalid alert_type. Must be one of {valid_types}")
        return value

    @validates('priority')
    def validate_priority(self, key: str, value: str) -> str:
        """
        Validate priority level.

        Args:
            key: Field name
            value: Priority value

        Returns:
            Validated value

        Raises:
            ValueError: If priority is invalid
        """
        valid_priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if value not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of {valid_priorities}")
        return value

    def check_trigger(self, current_value: float, previous_value: float = None) -> bool:
        """
        Check if alert should be triggered based on conditions.

        Args:
            current_value: Current value to check
            previous_value: Previous value for crossing checks

        Returns:
            True if alert should be triggered
        """
        self.current_value = current_value

        if not self.is_active or self.is_triggered:
            return False

        triggered = False

        if self.trigger_condition == "ABOVE":
            triggered = current_value > self.threshold_value
        elif self.trigger_condition == "BELOW":
            triggered = current_value < self.threshold_value
        elif self.trigger_condition == "EQUALS":
            triggered = abs(current_value - self.threshold_value) < 0.01
        elif self.trigger_condition == "CROSSES_ABOVE" and previous_value is not None:
            triggered = (previous_value <= self.threshold_value and
                        current_value > self.threshold_value)
        elif self.trigger_condition == "CROSSES_BELOW" and previous_value is not None:
            triggered = (previous_value >= self.threshold_value and
                        current_value < self.threshold_value)

        return triggered

    def trigger(self) -> None:
        """Mark alert as triggered."""
        self.is_triggered = 1
        self.triggered_date = datetime.now(timezone.utc)

    def mark_notification_sent(self) -> None:
        """Mark notification as sent."""
        self.notification_sent = 1

    def reset(self) -> None:
        """Reset alert to allow re-triggering."""
        self.is_triggered = 0
        self.triggered_date = None
        self.notification_sent = 0
        self.current_value = None

    def deactivate(self) -> None:
        """Deactivate the alert."""
        self.is_active = 0

    def activate(self) -> None:
        """Activate the alert."""
        self.is_active = 1

    def __repr__(self) -> str:
        """String representation of alert."""
        return (f"<Alert(id={self.id}, type='{self.alert_type}', "
                f"symbol='{self.symbol}', triggered={bool(self.is_triggered)})>")
