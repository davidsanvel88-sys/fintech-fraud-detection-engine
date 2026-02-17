"""
Fraud Detection Engine — Core Orchestrator.

The FraudEngine class manages rule registration, transaction evaluation,
and risk scoring. It follows the Open/Closed Principle: new rules can be
added by registration without modifying engine logic.
"""

import logging
from typing import Any

from src.loader import Transaction
from src.rules import FraudRule

logger = logging.getLogger("fraud_engine.engine")


class FraudEngine:
    """Central orchestrator that evaluates transactions against registered rules.

    The engine iterates over all registered FraudRule instances, accumulates
    risk scores, and classifies transactions into risk levels.

    Attributes:
        rules: List of registered FraudRule instances.
        alert_threshold: Minimum risk_score to trigger a fraud alert.
        critical_threshold: Score above this level is classified as CRITICAL.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the FraudEngine with alerting configuration.

        Args:
            config: The full application configuration dictionary.
        """
        self.rules: list[FraudRule] = []
        alerting_config = config.get("alerting", {})
        self.alert_threshold: int = alerting_config.get("risk_score_threshold", 75)
        self.critical_threshold: int = alerting_config.get("critical_threshold", 120)
        self._config = config
        logger.info(
            "FraudEngine initialized — alert threshold: %d, critical threshold: %d",
            self.alert_threshold,
            self.critical_threshold,
        )

    def register_rule(self, rule: FraudRule) -> None:
        """Register a new fraud detection rule with the engine.

        Args:
            rule: An instance of a FraudRule subclass.
        """
        self.rules.append(rule)
        logger.info("Registered rule: %s", rule.name)

    def register_rules(self, rules: list[FraudRule]) -> None:
        """Register multiple fraud detection rules at once.

        Args:
            rules: A list of FraudRule subclass instances.
        """
        for rule in rules:
            self.register_rule(rule)

    def evaluate_transaction(
        self,
        transaction: Transaction,
        **kwargs: Any,
    ) -> Transaction:
        """Evaluate a single transaction against all registered rules.

        Each rule is evaluated independently. If a rule raises an exception,
        the error is logged and the rule is skipped (fail-safe behavior).

        Args:
            transaction: The Transaction to evaluate.
            **kwargs: Additional context passed to each rule's evaluate method.

        Returns:
            The same Transaction object, now with populated
            risk_score and triggered_rules fields.
        """
        transaction.risk_score = 0
        transaction.triggered_rules = []

        for rule in self.rules:
            try:
                score = rule.evaluate(transaction, **kwargs)
                if score > 0:
                    transaction.risk_score += score
                    rule_label = f"{rule.name}: +{score}"
                    transaction.triggered_rules.append(rule_label)
            except Exception as exc:
                logger.error(
                    "Rule '%s' failed on tx %s: %s",
                    rule.name,
                    transaction.transaction_id,
                    exc,
                )

        return transaction

    def evaluate_all(
        self,
        transactions: list[Transaction],
        **kwargs: Any,
    ) -> list[Transaction]:
        """Evaluate a batch of transactions against all registered rules.

        Transactions that cause unexpected errors are logged and skipped
        to ensure the engine never halts mid-batch.

        Args:
            transactions: List of Transaction objects to evaluate.
            **kwargs: Additional context passed to rule evaluators.

        Returns:
            The list of evaluated Transaction objects (with scores populated).
        """
        logger.info(
            "Starting batch evaluation — %d transactions, %d rules",
            len(transactions),
            len(self.rules),
        )

        evaluated: list[Transaction] = []
        for tx in transactions:
            try:
                self.evaluate_transaction(tx, **kwargs)
                evaluated.append(tx)
            except Exception as exc:
                logger.error(
                    "Unexpected error processing tx %s: %s",
                    tx.transaction_id,
                    exc,
                )

        logger.info("Batch evaluation complete — %d transactions processed", len(evaluated))
        return evaluated

    def get_alerts(self, transactions: list[Transaction]) -> list[Transaction]:
        """Filter evaluated transactions to return only those above the alert threshold.

        Args:
            transactions: List of already-evaluated Transaction objects.

        Returns:
            A list of Transaction objects where risk_score >= alert_threshold.
        """
        alerts = [tx for tx in transactions if tx.risk_score >= self.alert_threshold]
        logger.warning(
            "Generated %d fraud alerts out of %d transactions (%.2f%%)",
            len(alerts),
            len(transactions),
            (len(alerts) / len(transactions) * 100) if transactions else 0,
        )
        return alerts

    def classify_risk_level(self, transaction: Transaction) -> str:
        """Classify a transaction's risk level based on its score.

        Args:
            transaction: An evaluated Transaction with a populated risk_score.

        Returns:
            'CRITICAL' if score >= critical_threshold, 'HIGH' otherwise.
        """
        if transaction.risk_score >= self.critical_threshold:
            return "CRITICAL"
        return "HIGH"

    def get_rule_statistics(
        self,
        transactions: list[Transaction],
    ) -> dict[str, int]:
        """Compute how many times each rule was triggered across all transactions.

        Args:
            transactions: List of evaluated Transaction objects.

        Returns:
            A dictionary mapping rule names to trigger counts, sorted
            in descending order of frequency.
        """
        rule_counts: dict[str, int] = {}
        for tx in transactions:
            for rule_entry in tx.triggered_rules:
                rule_name = rule_entry.split(":")[0]
                rule_counts[rule_name] = rule_counts.get(rule_name, 0) + 1

        # Sort by count descending
        return dict(sorted(rule_counts.items(), key=lambda x: x[1], reverse=True))
