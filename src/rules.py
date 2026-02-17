"""
Business rules module for the Fraud Detection Engine.

Each rule is implemented as an independent class following the
Strategy Pattern. Rules implement the `FraudRule` abstract base
class and provide an `evaluate()` method that returns a risk score.

Adding a new rule requires ONLY:
  1. Creating a new class that inherits from FraudRule
  2. Registering it in the engine — no modification to existing code.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.loader import Transaction


class FraudRule(ABC):
    """Abstract base class for all fraud detection rules.

    Each concrete rule encapsulates a single business condition
    and returns a point score if the condition is triggered.

    Attributes:
        name: Human-readable name of the rule (auto-derived from class name).
        config: Rule-specific configuration parameters from config.yaml.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the rule with its configuration section.

        Args:
            config: Dictionary with rule-specific thresholds and parameters.
        """
        self.config = config
        self.name: str = self.__class__.__name__

    @abstractmethod
    def evaluate(self, transaction: Transaction, **kwargs: Any) -> int:
        """Evaluate a transaction against this rule.

        Args:
            transaction: The Transaction object to evaluate.
            **kwargs: Additional context (e.g., user_device_map).

        Returns:
            An integer risk score (0 if not triggered, positive if triggered).
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.name}>"


class HighAmountRule(FraudRule):
    """Flags transactions with unusually high monetary amounts.

    Triggers when the transaction amount exceeds the configured
    threshold (default: $15,000).
    """

    def evaluate(self, transaction: Transaction, **kwargs: Any) -> int:
        """Check if amount exceeds the high-amount threshold.

        Args:
            transaction: The Transaction to evaluate.

        Returns:
            Configured points if triggered, 0 otherwise.
        """
        threshold = self.config.get("threshold", 15000)
        points = self.config.get("points", 50)
        if transaction.amount > threshold:
            return points
        return 0


class OddHoursRule(FraudRule):
    """Flags transactions occurring during unusual hours.

    Triggers when the transaction's `is_odd_hour` flag is set
    (typically between 22:00 and 05:00).
    """

    def evaluate(self, transaction: Transaction, **kwargs: Any) -> int:
        """Check if the transaction occurred during odd hours.

        Args:
            transaction: The Transaction to evaluate.

        Returns:
            Configured points if triggered, 0 otherwise.
        """
        points = self.config.get("points", 30)
        if transaction.is_odd_hour == 1:
            return points
        return 0


class VelocityRule(FraudRule):
    """Flags rapid-fire transactions from the same user.

    Triggers when the time since the user's last transaction
    is below the configured minimum (default: 0.17 hours ≈ 10 min).
    """

    def evaluate(self, transaction: Transaction, **kwargs: Any) -> int:
        """Check if transactions are occurring too rapidly.

        Args:
            transaction: The Transaction to evaluate.

        Returns:
            Configured points if triggered, 0 otherwise.
        """
        min_hours = self.config.get("min_hours", 0.17)
        points = self.config.get("points", 40)
        if transaction.hours_since_last_tx < min_hours:
            return points
        return 0


class UnusualAmountRule(FraudRule):
    """Flags transactions significantly higher than the user's average.

    Triggers when the amount-to-average ratio exceeds the configured
    threshold (default: 3.0x the user's average).
    """

    def evaluate(self, transaction: Transaction, **kwargs: Any) -> int:
        """Check if the amount deviates significantly from user average.

        Args:
            transaction: The Transaction to evaluate.

        Returns:
            Configured points if triggered, 0 otherwise.
        """
        ratio_threshold = self.config.get("ratio_threshold", 3.0)
        points = self.config.get("points", 35)
        if transaction.amount_vs_avg_ratio > ratio_threshold:
            return points
        return 0


class LocationChangeRule(FraudRule):
    """Flags transactions with a location change within a short window.

    Triggers when both conditions are met:
      - location_changed == 1
      - hours_since_last_tx < max_hours (default: 2.0)
    """

    def evaluate(self, transaction: Transaction, **kwargs: Any) -> int:
        """Check for suspicious location changes in a short timeframe.

        Args:
            transaction: The Transaction to evaluate.

        Returns:
            Configured points if triggered, 0 otherwise.
        """
        max_hours = self.config.get("max_hours", 2.0)
        points = self.config.get("points", 30)
        if (
            transaction.location_changed == 1
            and transaction.hours_since_last_tx < max_hours
        ):
            return points
        return 0


class ForeignTxRule(FraudRule):
    """Flags transactions originating from a foreign location.

    Triggers when `is_foreign_location` is set to 1.
    """

    def evaluate(self, transaction: Transaction, **kwargs: Any) -> int:
        """Check if the transaction is from a foreign location.

        Args:
            transaction: The Transaction to evaluate.

        Returns:
            Configured points if triggered, 0 otherwise.
        """
        points = self.config.get("points", 25)
        if transaction.is_foreign_location == 1:
            return points
        return 0


class NewDeviceRule(FraudRule):
    """Flags transactions from a device not typically used by the user.

    Compares the transaction's device_id against the user's most
    frequently used device (pre-computed from the dataset).
    """

    def evaluate(self, transaction: Transaction, **kwargs: Any) -> int:
        """Check if the transaction is from an unfamiliar device.

        Args:
            transaction: The Transaction to evaluate.
            **kwargs: Must include 'user_device_map' (dict mapping
                user_id to their most frequent device_id).

        Returns:
            Configured points if triggered, 0 otherwise.
        """
        points = self.config.get("points", 20)
        user_device_map: dict[str, str] = kwargs.get("user_device_map", {})

        known_device = user_device_map.get(transaction.user_id)
        if known_device is None:
            # First transaction for this user — cannot determine novelty
            return 0

        if transaction.device_id != known_device:
            return points
        return 0
