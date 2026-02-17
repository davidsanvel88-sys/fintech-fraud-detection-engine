"""
Fraud Detection Engine — Main Orchestrator.

Entry point for the fraud detection pipeline. Orchestrates:
  1. Configuration loading
  2. Structured logging setup
  3. Dataset ingestion and validation
  4. Rule registration (Strategy Pattern)
  5. Batch transaction evaluation
  6. Alert generation and reporting

Usage:
    python main.py
    python main.py --config path/to/config.yaml
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure the project root is in the Python path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine import FraudEngine
from src.loader import (
    compute_user_device_map,
    dataframe_to_transactions,
    load_dataset,
)
from src.dashboard import generate_dashboard
from src.reporting import generate_json_report, print_console_report
from src.rules import (
    ForeignTxRule,
    HighAmountRule,
    LocationChangeRule,
    NewDeviceRule,
    OddHoursRule,
    UnusualAmountRule,
    VelocityRule,
)
from src.utils import load_config, setup_logging


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace with config path.
    """
    parser = argparse.ArgumentParser(
        description="Fraud Detection Engine — Rule-Based Risk Scoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to the YAML configuration file (default: config.yaml)",
    )
    return parser.parse_args()


def main() -> None:
    """Main execution pipeline for the Fraud Detection Engine."""
    args = parse_arguments()
    start_time = time.time()

    # ── Step 1: Load configuration ──────────────────────────────────────
    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"❌ Configuration error: {exc}")
        sys.exit(1)

    # ── Step 2: Setup structured logging ────────────────────────────────
    logger = setup_logging(config)
    logger.info("=" * 60)
    logger.info("FRAUD DETECTION ENGINE — Starting pipeline")
    logger.info("=" * 60)

    # ── Step 3: Load and validate dataset ───────────────────────────────
    try:
        data_config = config["data"]
        input_file = data_config["input_file"]
        output_file = data_config.get("output_file", "fraud_alerts.json")

        df = load_dataset(input_file)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Dataset loading failed: %s", exc)
        sys.exit(1)

    # ── Step 4: Compute auxiliary data structures ───────────────────────
    user_device_map = compute_user_device_map(df)

    # ── Step 5: Convert DataFrame to Transaction objects ────────────────
    transactions = dataframe_to_transactions(df)
    if not transactions:
        logger.error("No valid transactions to process. Exiting.")
        sys.exit(1)

    # ── Step 6: Initialize the engine and register rules ────────────────
    engine = FraudEngine(config)
    rules_config = config["rules"]

    # Register all business rules — adding a new rule is a single line
    engine.register_rules([
        HighAmountRule(rules_config["high_amount"]),
        OddHoursRule(rules_config["odd_hours"]),
        VelocityRule(rules_config["velocity"]),
        UnusualAmountRule(rules_config["unusual_amount"]),
        LocationChangeRule(rules_config["location_change"]),
        ForeignTxRule(rules_config["foreign_tx"]),
        NewDeviceRule(rules_config["new_device"]),
    ])

    # ── Step 7: Evaluate all transactions ───────────────────────────────
    evaluated = engine.evaluate_all(
        transactions,
        user_device_map=user_device_map,
    )

    # ── Step 8: Extract fraud alerts ────────────────────────────────────
    alerts = engine.get_alerts(evaluated)

    # ── Step 9: Generate reports ────────────────────────────────────────
    generate_json_report(engine, evaluated, alerts, output_file)
    print_console_report(engine, evaluated, alerts)

    # ── Step 9b: Generate interactive dashboard ─────────────────────────
    dashboard_path = generate_dashboard(engine, evaluated, alerts, "dashboard.html")
    logger.info("Interactive dashboard generated: %s", dashboard_path)

    # ── Step 10: Final summary ──────────────────────────────────────────
    elapsed = time.time() - start_time
    logger.info("Pipeline completed in %.2f seconds", elapsed)
    logger.info(
        "Results: %d processed, %d alerts, output: %s",
        len(evaluated),
        len(alerts),
        output_file,
    )


if __name__ == "__main__":
    main()
