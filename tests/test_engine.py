"""
Integration tests for the FraudEngine.

Tests the full orchestration pipeline: rule registration,
batch evaluation, alert generation, and risk classification.
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.engine import FraudEngine
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


# ── Shared Fixtures ────────────────────────────────────────────────────────

SAMPLE_CONFIG: dict = {
    "data": {"input_file": "test.csv", "output_file": "test_output.json"},
    "rules": {
        "high_amount": {"threshold": 15000, "points": 50},
        "odd_hours": {"start_hour": 22, "end_hour": 5, "points": 30},
        "velocity": {"min_hours": 0.17, "points": 40},
        "unusual_amount": {"ratio_threshold": 3.0, "points": 35},
        "location_change": {"max_hours": 2.0, "points": 30},
        "foreign_tx": {"points": 25},
        "new_device": {"points": 20},
    },
    "alerting": {"risk_score_threshold": 75, "critical_threshold": 120},
    "logging": {"level": "WARNING"},
}


def _make_transaction(**overrides) -> Transaction:
    """Factory helper for creating Transaction fixtures."""
    defaults = {
        "transaction_id": "tx-integration-001",
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


def _build_engine() -> FraudEngine:
    """Build a fully-configured FraudEngine with all rules registered."""
    engine = FraudEngine(SAMPLE_CONFIG)
    rules_config = SAMPLE_CONFIG["rules"]
    engine.register_rules([
        HighAmountRule(rules_config["high_amount"]),
        OddHoursRule(rules_config["odd_hours"]),
        VelocityRule(rules_config["velocity"]),
        UnusualAmountRule(rules_config["unusual_amount"]),
        LocationChangeRule(rules_config["location_change"]),
        ForeignTxRule(rules_config["foreign_tx"]),
        NewDeviceRule(rules_config["new_device"]),
    ])
    return engine


# ── Engine Initialization Tests ────────────────────────────────────────────

class TestEngineInit:
    """Tests for FraudEngine initialization and rule registration."""

    def test_engine_initializes_with_config(self) -> None:
        """Engine should correctly read thresholds from config."""
        engine = FraudEngine(SAMPLE_CONFIG)
        assert engine.alert_threshold == 75
        assert engine.critical_threshold == 120

    def test_all_rules_registered(self) -> None:
        """Engine should have 7 rules after full registration."""
        engine = _build_engine()
        assert len(engine.rules) == 7

    def test_rule_names_are_correct(self) -> None:
        """Each registered rule should have the correct class name."""
        engine = _build_engine()
        rule_names = [r.name for r in engine.rules]
        assert "HighAmountRule" in rule_names
        assert "VelocityRule" in rule_names
        assert "NewDeviceRule" in rule_names


# ── Single Transaction Evaluation Tests ────────────────────────────────────

class TestSingleEvaluation:
    """Tests for evaluating individual transactions."""

    def test_clean_transaction_gets_zero_score(self) -> None:
        """A completely normal transaction should have score 0."""
        engine = _build_engine()
        tx = _make_transaction()
        result = engine.evaluate_transaction(tx, user_device_map={"user-001": "device-main"})
        assert result.risk_score == 0
        assert result.triggered_rules == []

    def test_high_risk_transaction_triggers_multiple_rules(self) -> None:
        """A suspicious transaction should accumulate points from multiple rules."""
        engine = _build_engine()
        tx = _make_transaction(
            amount=20000.0,           # HighAmountRule: +50
            is_odd_hour=1,            # OddHoursRule: +30
            hours_since_last_tx=0.05, # VelocityRule: +40
            amount_vs_avg_ratio=5.0,  # UnusualAmountRule: +35
        )
        result = engine.evaluate_transaction(tx, user_device_map={"user-001": "device-main"})
        assert result.risk_score == 50 + 30 + 40 + 35  # 155
        assert len(result.triggered_rules) == 4

    def test_foreign_transaction_with_new_device(self) -> None:
        """Foreign location + new device should accumulate both scores."""
        engine = _build_engine()
        tx = _make_transaction(
            is_foreign_location=1,    # ForeignTxRule: +25
            device_id="device-new",   # NewDeviceRule: +20
        )
        device_map = {"user-001": "device-main"}
        result = engine.evaluate_transaction(tx, user_device_map=device_map)
        assert result.risk_score == 45  # 25 + 20
        assert len(result.triggered_rules) == 2


# ── Batch Evaluation Tests ─────────────────────────────────────────────────

class TestBatchEvaluation:
    """Tests for batch evaluation of multiple transactions."""

    def test_batch_processes_all_transactions(self) -> None:
        """All transactions should be processed and returned."""
        engine = _build_engine()
        transactions = [
            _make_transaction(transaction_id=f"tx-{i}")
            for i in range(50)
        ]
        results = engine.evaluate_all(transactions, user_device_map={})
        assert len(results) == 50

    def test_batch_handles_mixed_risk_levels(self) -> None:
        """Batch should correctly evaluate transactions with varying risk."""
        engine = _build_engine()
        transactions = [
            _make_transaction(transaction_id="clean", amount=100),
            _make_transaction(transaction_id="risky", amount=20000, is_odd_hour=1),
        ]
        results = engine.evaluate_all(
            transactions,
            user_device_map={"user-001": "device-main"},
        )
        assert results[0].risk_score == 0
        assert results[1].risk_score == 80  # 50 + 30


# ── Alert Generation Tests ─────────────────────────────────────────────────

class TestAlertGeneration:
    """Tests for fraud alert filtering and classification."""

    def test_alerts_filter_by_threshold(self) -> None:
        """Only transactions above alert threshold should be returned."""
        engine = _build_engine()
        transactions = [
            _make_transaction(transaction_id="low"),
            _make_transaction(
                transaction_id="high",
                amount=20000,
                is_odd_hour=1,
                hours_since_last_tx=0.05,
            ),
        ]
        evaluated = engine.evaluate_all(
            transactions,
            user_device_map={"user-001": "device-main"},
        )
        alerts = engine.get_alerts(evaluated)

        assert len(alerts) == 1
        assert alerts[0].transaction_id == "high"

    def test_risk_level_classification(self) -> None:
        """CRITICAL should be assigned for very high scores."""
        engine = _build_engine()
        # Build a transaction that triggers many rules
        tx = _make_transaction(
            amount=20000,                # +50
            is_odd_hour=1,               # +30
            hours_since_last_tx=0.05,    # +40
            amount_vs_avg_ratio=5.0,     # +35
            is_foreign_location=1,       # +25
        )
        engine.evaluate_transaction(tx, user_device_map={"user-001": "device-main"})
        # Score = 50+30+40+35+25 = 180 → CRITICAL (>= 120)
        assert engine.classify_risk_level(tx) == "CRITICAL"

    def test_high_risk_level(self) -> None:
        """HIGH should be assigned for scores between alert and critical thresholds."""
        engine = _build_engine()
        tx = _make_transaction(
            amount=20000,     # +50
            is_odd_hour=1,    # +30
        )
        engine.evaluate_transaction(tx, user_device_map={"user-001": "device-main"})
        # Score = 80 → HIGH (>= 75 but < 120)
        assert engine.classify_risk_level(tx) == "HIGH"


# ── Rule Statistics Tests ──────────────────────────────────────────────────

class TestRuleStatistics:
    """Tests for rule trigger statistics."""

    def test_statistics_count_correctly(self) -> None:
        """Rule statistics should accurately count triggers."""
        engine = _build_engine()
        transactions = [
            _make_transaction(transaction_id="a", amount=20000),           # HighAmountRule
            _make_transaction(transaction_id="b", amount=20000, is_odd_hour=1),  # Both
            _make_transaction(transaction_id="c", is_odd_hour=1),           # OddHoursRule
        ]
        evaluated = engine.evaluate_all(
            transactions,
            user_device_map={"user-001": "device-main"},
        )
        stats = engine.get_rule_statistics(evaluated)
        assert stats["HighAmountRule"] == 2
        assert stats["OddHoursRule"] == 2

    def test_empty_statistics(self) -> None:
        """No triggers should produce empty statistics."""
        engine = _build_engine()
        transactions = [_make_transaction()]
        evaluated = engine.evaluate_all(
            transactions,
            user_device_map={"user-001": "device-main"},
        )
        stats = engine.get_rule_statistics(evaluated)
        assert len(stats) == 0
