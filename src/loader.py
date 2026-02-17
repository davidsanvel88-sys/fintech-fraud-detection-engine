"""
Data loader module for the Fraud Detection Engine.

Handles CSV ingestion, schema validation, type coercion,
and conversion of raw rows into typed Transaction records.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger("fraud_engine.loader")


@dataclass
class Transaction:
    """Immutable representation of a single financial transaction.

    All fields map directly to columns in the fraud detection dataset.
    This dataclass enforces type safety and provides a clean interface
    for rule evaluation.
    """

    transaction_id: str
    user_id: str
    timestamp: str
    amount: float
    merchant: str
    category: str
    location: str
    is_fraud: int
    hour: int
    day_of_week: int
    is_weekend: int
    month: int
    is_odd_hour: int
    user_avg_amount: float
    amount_vs_avg_ratio: float
    hours_since_last_tx: float
    location_changed: int
    is_foreign_location: int
    device_id: str

    # Populated during engine processing — not part of the raw data
    risk_score: int = field(default=0, init=False)
    triggered_rules: list[str] = field(default_factory=list, init=False)


# Expected columns in the source CSV
REQUIRED_COLUMNS: list[str] = [
    "transaction_id", "user_id", "timestamp", "amount", "merchant",
    "category", "location", "is_fraud", "hour", "day_of_week",
    "is_weekend", "month", "is_odd_hour", "user_avg_amount",
    "amount_vs_avg_ratio", "hours_since_last_tx", "location_changed",
    "is_foreign_location", "device_id",
]


def load_dataset(file_path: str) -> pd.DataFrame:
    """Load the CSV dataset and validate its schema.

    Args:
        file_path: Path to the fraud detection CSV file.

    Returns:
        A validated pandas DataFrame ready for processing.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If required columns are missing from the dataset.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path.resolve()}")

    logger.info("Loading dataset from: %s", path.resolve())
    df = pd.read_csv(path)

    # Schema validation — ensure all required columns are present
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    logger.info(
        "Dataset loaded successfully — %d rows, %d columns",
        len(df), len(df.columns),
    )
    return df


def dataframe_to_transactions(df: pd.DataFrame) -> list[Transaction]:
    """Convert a validated DataFrame into a list of Transaction objects.

    Each row is converted individually. Rows with missing or corrupt
    data are logged as warnings and skipped rather than halting execution.

    Args:
        df: A validated pandas DataFrame with all required columns.

    Returns:
        A list of Transaction dataclass instances.
    """
    transactions: list[Transaction] = []
    skipped = 0

    for idx, row in df.iterrows():
        try:
            tx = Transaction(
                transaction_id=str(row["transaction_id"]),
                user_id=str(row["user_id"]),
                timestamp=str(row["timestamp"]),
                amount=float(row["amount"]),
                merchant=str(row["merchant"]),
                category=str(row["category"]),
                location=str(row["location"]),
                is_fraud=int(row["is_fraud"]),
                hour=int(row["hour"]),
                day_of_week=int(row["day_of_week"]),
                is_weekend=int(row["is_weekend"]),
                month=int(row["month"]),
                is_odd_hour=int(row["is_odd_hour"]),
                user_avg_amount=float(row["user_avg_amount"]),
                amount_vs_avg_ratio=float(row["amount_vs_avg_ratio"]),
                hours_since_last_tx=float(row["hours_since_last_tx"]),
                location_changed=int(row["location_changed"]),
                is_foreign_location=int(row["is_foreign_location"]),
                device_id=str(row["device_id"]),
            )
            transactions.append(tx)
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Skipping corrupt row at index %d: %s", idx, exc)
            skipped += 1

    if skipped > 0:
        logger.warning("Total rows skipped due to data issues: %d", skipped)

    logger.info("Converted %d rows into Transaction objects", len(transactions))
    return transactions


def compute_user_device_map(df: pd.DataFrame) -> dict[str, str]:
    """Compute the most frequently used device_id per user.

    This mapping is used by NewDeviceRule to detect when a transaction
    originates from an unfamiliar device.

    Args:
        df: The raw DataFrame with 'user_id' and 'device_id' columns.

    Returns:
        A dictionary mapping user_id → most frequent device_id.
    """
    device_map: dict[str, str] = {}
    grouped = df.groupby("user_id")["device_id"]

    for user_id, devices in grouped:
        most_common = devices.mode()
        if len(most_common) > 0:
            device_map[str(user_id)] = str(most_common.iloc[0])

    logger.info(
        "Built user-device map for %d users", len(device_map),
    )
    return device_map
