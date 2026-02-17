"""
Unit tests for fraud detection rules.

Tests each rule independently with controlled Transaction fixtures.
Every rule has at least 2 tests: one for triggering and one for not triggering.
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.loader import Transaction
from src.rules import (
    ForeignTxRule,
    HighAmountRule,
    LocationChangeRule,
    NewDeviceRule,
    OddHoursRule,
    UnusualAmountRule,
    VelocityRule,
)


def _make_transaction(**overrides) -> Transaction:
    """Factory helper to create a Transaction with sensible defaults.

    Any field can be overridden via keyword arguments.

    Args:
        **overrides: Fields to override in the default Transaction.

    Returns:
        A Transaction instance with the specified overrides.
    """
    defaults = {
        "transaction_id": "tx-001",
        "user_id": "user-001",
        "timestamp": "2023-06-01 12:00:00",
        "amount": 500.0,
        "merchant": "TestMerchant",
        "category": "Services",
        "location": "CDMX",
        "is_fraud": 0,
        "hour": 12,
        "day_of_week": 3,
        "is_weekend": 0,
        "month": 6,
        "is_odd_hour": 0,
        "user_avg_amount": 1000.0,
        "amount_vs_avg_ratio": 0.5,
        "hours_since_last_tx": 24.0,
        "location_changed": 0,
        "is_foreign_location": 0,
        "device_id": "device-main",
    }
    defaults.update(overrides)
    return Transaction(**defaults)


# ────────────────────────────────────────────────────────────────────────────
# HighAmountRule Tests
# ────────────────────────────────────────────────────────────────────────────

class TestHighAmountRule:
    """Tests for HighAmountRule — flags transactions above a monetary threshold."""

    def setup_method(self) -> None:
        self.rule = HighAmountRule({"threshold": 15000, "points": 50})

    def test_triggers_above_threshold(self) -> None:
        """Transaction with amount > threshold should return configured points."""
        tx = _make_transaction(amount=20000.0)
        assert self.rule.evaluate(tx) == 50

    def test_does_not_trigger_below_threshold(self) -> None:
        """Transaction with amount <= threshold should return 0."""
        tx = _make_transaction(amount=5000.0)
        assert self.rule.evaluate(tx) == 0

    def test_does_not_trigger_at_exact_threshold(self) -> None:
        """Amount exactly equal to threshold should NOT trigger (>= vs >)."""
        tx = _make_transaction(amount=15000.0)
        assert self.rule.evaluate(tx) == 0

    def test_custom_threshold(self) -> None:
        """Rule should respect custom threshold from config."""
        rule = HighAmountRule({"threshold": 5000, "points": 60})
        tx = _make_transaction(amount=7000.0)
        assert rule.evaluate(tx) == 60


# ────────────────────────────────────────────────────────────────────────────
# OddHoursRule Tests
# ────────────────────────────────────────────────────────────────────────────

class TestOddHoursRule:
    """Tests for OddHoursRule — flags transactions during unusual hours."""

    def setup_method(self) -> None:
        self.rule = OddHoursRule({"start_hour": 22, "end_hour": 5, "points": 30})

    def test_triggers_during_odd_hours(self) -> None:
        """Transaction with is_odd_hour=1 should return points."""
        tx = _make_transaction(is_odd_hour=1, hour=2)
        assert self.rule.evaluate(tx) == 30

    def test_does_not_trigger_during_normal_hours(self) -> None:
        """Transaction with is_odd_hour=0 should return 0."""
        tx = _make_transaction(is_odd_hour=0, hour=14)
        assert self.rule.evaluate(tx) == 0


# ────────────────────────────────────────────────────────────────────────────
# VelocityRule Tests
# ────────────────────────────────────────────────────────────────────────────

class TestVelocityRule:
    """Tests for VelocityRule — flags rapid-fire transactions."""

    def setup_method(self) -> None:
        self.rule = VelocityRule({"min_hours": 0.17, "points": 40})

    def test_triggers_rapid_transaction(self) -> None:
        """Transaction <10 min after last should trigger."""
        tx = _make_transaction(hours_since_last_tx=0.05)
        assert self.rule.evaluate(tx) == 40

    def test_does_not_trigger_normal_interval(self) -> None:
        """Transaction with large gap should return 0."""
        tx = _make_transaction(hours_since_last_tx=5.0)
        assert self.rule.evaluate(tx) == 0

    def test_boundary_value(self) -> None:
        """Transaction at exactly the threshold should NOT trigger."""
        tx = _make_transaction(hours_since_last_tx=0.17)
        assert self.rule.evaluate(tx) == 0


# ────────────────────────────────────────────────────────────────────────────
# UnusualAmountRule Tests
# ────────────────────────────────────────────────────────────────────────────

class TestUnusualAmountRule:
    """Tests for UnusualAmountRule — flags amounts far above user average."""

    def setup_method(self) -> None:
        self.rule = UnusualAmountRule({"ratio_threshold": 3.0, "points": 35})

    def test_triggers_high_ratio(self) -> None:
        """Ratio above threshold should trigger."""
        tx = _make_transaction(amount_vs_avg_ratio=5.0)
        assert self.rule.evaluate(tx) == 35

    def test_does_not_trigger_normal_ratio(self) -> None:
        """Ratio below threshold should return 0."""
        tx = _make_transaction(amount_vs_avg_ratio=1.5)
        assert self.rule.evaluate(tx) == 0


# ────────────────────────────────────────────────────────────────────────────
# LocationChangeRule Tests
# ────────────────────────────────────────────────────────────────────────────

class TestLocationChangeRule:
    """Tests for LocationChangeRule — flags suspicious location changes."""

    def setup_method(self) -> None:
        self.rule = LocationChangeRule({"max_hours": 2.0, "points": 30})

    def test_triggers_location_change_fast(self) -> None:
        """Location change within time window should trigger."""
        tx = _make_transaction(location_changed=1, hours_since_last_tx=0.5)
        assert self.rule.evaluate(tx) == 30

    def test_does_not_trigger_no_location_change(self) -> None:
        """No location change should return 0 even with fast timing."""
        tx = _make_transaction(location_changed=0, hours_since_last_tx=0.5)
        assert self.rule.evaluate(tx) == 0

    def test_does_not_trigger_slow_location_change(self) -> None:
        """Location change with large time gap should return 0."""
        tx = _make_transaction(location_changed=1, hours_since_last_tx=10.0)
        assert self.rule.evaluate(tx) == 0


# ────────────────────────────────────────────────────────────────────────────
# ForeignTxRule Tests
# ────────────────────────────────────────────────────────────────────────────

class TestForeignTxRule:
    """Tests for ForeignTxRule — flags foreign location transactions."""

    def setup_method(self) -> None:
        self.rule = ForeignTxRule({"points": 25})

    def test_triggers_foreign_location(self) -> None:
        """Foreign location flag should trigger."""
        tx = _make_transaction(is_foreign_location=1)
        assert self.rule.evaluate(tx) == 25

    def test_does_not_trigger_domestic(self) -> None:
        """Domestic transaction should return 0."""
        tx = _make_transaction(is_foreign_location=0)
        assert self.rule.evaluate(tx) == 0


# ────────────────────────────────────────────────────────────────────────────
# NewDeviceRule Tests
# ────────────────────────────────────────────────────────────────────────────

class TestNewDeviceRule:
    """Tests for NewDeviceRule — flags transactions from unfamiliar devices."""

    def setup_method(self) -> None:
        self.rule = NewDeviceRule({"points": 20})
        self.device_map = {"user-001": "device-main"}

    def test_triggers_new_device(self) -> None:
        """Transaction from a different device should trigger."""
        tx = _make_transaction(device_id="device-unknown")
        assert self.rule.evaluate(tx, user_device_map=self.device_map) == 20

    def test_does_not_trigger_known_device(self) -> None:
        """Transaction from the user's main device should return 0."""
        tx = _make_transaction(device_id="device-main")
        assert self.rule.evaluate(tx, user_device_map=self.device_map) == 0

    def test_unknown_user_returns_zero(self) -> None:
        """User with no device history should return 0 (no false positives)."""
        tx = _make_transaction(user_id="unknown-user", device_id="any")
        assert self.rule.evaluate(tx, user_device_map=self.device_map) == 0
