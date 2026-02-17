"""
Utility module for the Fraud Detection Engine.

Provides structured logging setup, configuration loading, and
common formatting helpers used across the project.
"""

import logging
import sys
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """Load and validate the YAML configuration file.

    Args:
        config_path: Path to the YAML configuration file.
            Defaults to 'config.yaml' in the current working directory.

    Returns:
        A dictionary containing all configuration parameters.

    Raises:
        FileNotFoundError: If the config file does not exist.
        yaml.YAMLError: If the config file contains invalid YAML.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    _validate_config(config)
    return config


def _validate_config(config: dict[str, Any]) -> None:
    """Validate that all required configuration sections are present.

    Args:
        config: The parsed configuration dictionary.

    Raises:
        ValueError: If a required section or key is missing.
    """
    required_sections = ["data", "rules", "alerting", "logging"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: '{section}'")

    required_rules = [
        "high_amount", "odd_hours", "velocity",
        "unusual_amount", "location_change", "foreign_tx", "new_device",
    ]
    for rule in required_rules:
        if rule not in config["rules"]:
            raise ValueError(f"Missing rule configuration: 'rules.{rule}'")


def setup_logging(config: dict[str, Any]) -> logging.Logger:
    """Configure structured logging for the application.

    Sets up a root logger with formatted console output.
    The log level, format, and date format are read from config.

    Args:
        config: The full application configuration dictionary.

    Returns:
        A configured Logger instance for the fraud detection engine.
    """
    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    log_format = log_config.get(
        "format",
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    date_format = log_config.get("date_format", "%Y-%m-%d %H:%M:%S")

    # Clear existing handlers to avoid duplicate output on re-runs
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    handler.setFormatter(formatter)

    logger = logging.getLogger("fraud_engine")
    logger.setLevel(log_level)
    logger.addHandler(handler)
    logger.propagate = False

    return logger


def format_currency(amount: float) -> str:
    """Format a numeric amount as a currency string.

    Args:
        amount: The monetary value to format.

    Returns:
        A formatted string like '$15,000.00'.
    """
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format a float as a percentage string.

    Args:
        value: The value to format (e.g., 0.0414 → '4.14%').

    Returns:
        A formatted percentage string.
    """
    return f"{value:.2f}%"
