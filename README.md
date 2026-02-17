# 🛡️ Fraud Detection Engine

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458?logo=pandas&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?logo=pytest)
![SOLID](https://img.shields.io/badge/Design-SOLID%20Principles-orange)

> **Production-grade, config-driven fraud detection engine** built with SOLID principles and the Strategy Pattern for real-time transaction risk scoring.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Business Rules](#business-rules)
- [Output Examples](#output-examples)
- [Testing](#testing)
- [Skills Demonstrated](#skills-demonstrated)

---

## 🔍 Overview

This engine processes financial transactions from a CSV dataset, evaluates each against a configurable set of fraud detection rules, and produces structured alert reports in both JSON and console formats. Designed as a **senior portfolio project**, it demonstrates real-world engineering practices used in fintech risk management systems.

### Key Design Decisions

- **Strategy Pattern** for rules: each rule is an independent class, enabling hot-swappable fraud logic
- **Configuration-driven thresholds**: all parameters live in `config.yaml`, not in code
- **Fail-safe processing**: corrupt transactions are logged and skipped, never crashing the pipeline
- **Rich console output**: executive summaries with color-coded risk indicators

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py                                │
│                   (Pipeline Orchestrator)                      │
└──────────┬───────────────────────────────────────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐ ┌──────────────┐
│ config   │ │  loader.py   │
│  .yaml   │ │  (CSV → TX)  │
└──────────┘ └──────┬───────┘
                    │
                    ▼
           ┌────────────────┐
           │   engine.py    │  ← Registers & orchestrates rules
           │  (FraudEngine) │
           └───────┬────────┘
                   │
     ┌─────────────┼─────────────────────────┐
     ▼             ▼             ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│HighAmount│ │OddHours  │ │Velocity  │ │  ...N    │  ← Strategy Pattern
│  Rule    │ │  Rule    │ │  Rule    │ │  Rules   │     (rules.py)
└──────────┘ └──────────┘ └──────────┘ └──────────┘
                   │
                   ▼
           ┌────────────────┐
           │ reporting.py   │  → fraud_alerts.json
           │ (JSON + Rich)  │  → Console Summary
           └────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **7 Business Rules** | High amount, odd hours, velocity, unusual ratio, location change, foreign TX, new device |
| ⚙️ **Config-Driven** | All thresholds in `config.yaml` — zero code changes needed |
| 🧩 **Strategy Pattern** | Add new rules without modifying the engine |
| 📊 **Rich Console Output** | Color-coded panels, tables, and risk indicators |
| 📄 **JSON Reports** | Structured alerts with timestamps and risk levels |
| 🛡️ **Fail-Safe** | Corrupt data is logged and skipped — never crashes |
| 🧪 **Comprehensive Tests** | 20+ unit & integration tests with pytest |
| 📝 **Type-Safe** | Full type hints with `dataclasses` |

---

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Setup

```bash
# Clone or navigate to the project directory
cd fraud_detection_engine

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

---

## 💻 Usage

### Run the Engine

```bash
# Default configuration
python main.py

# Custom configuration file
python main.py --config path/to/custom_config.yaml
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --tb=short
```

---

## ⚙️ Configuration

All thresholds and parameters are externalized in `config.yaml`:

```yaml
rules:
  high_amount:
    threshold: 15000    # Amount above this triggers alert
    points: 50

  velocity:
    min_hours: 0.17     # Less than ~10 minutes between transactions
    points: 40

alerting:
  risk_score_threshold: 75    # Minimum score for FRAUD ALERT
  critical_threshold: 120     # Score above this = CRITICAL
```

**To adjust sensitivity**, simply edit `config.yaml` — no code changes needed.

---

## 📏 Business Rules

| Rule | Condition | Points |
|------|-----------|--------|
| `HighAmountRule` | `amount > 15,000` | +50 |
| `OddHoursRule` | Transaction between 22:00–05:00 | +30 |
| `VelocityRule` | < 10 min since last transaction | +40 |
| `UnusualAmountRule` | Amount > 3x user average | +35 |
| `LocationChangeRule` | Location changed within 2 hours | +30 |
| `ForeignTxRule` | Foreign location detected | +25 |
| `NewDeviceRule` | Device ≠ user's most frequent | +20 |

**Alert Threshold:** `risk_score ≥ 75` → **FRAUD ALERT**  
**Risk Levels:** `75–119` = **HIGH** | `≥ 120` = **CRITICAL**

---

## 📤 Output Examples

### Console Report (Rich)

```
╭──────────────────────────────────────────────────────────────╮
│         🛡️  FRAUD DETECTION ENGINE — REPORT                  │
├──────────────────────────────────────────────────────────────┤
│  Total Processed   :  2,101                                  │
│  Alerts Generated  :  87  (4.14%)                            │
│  Average Score     :  42.3                                   │
│  Most Active Rule  :  HighAmountRule                         │
│                                                              │
│  CRITICAL Alerts   :  12                                     │
│  HIGH Alerts       :  75                                     │
╰──────────────────────────────────────────────────────────────╯
```

### JSON Report (`fraud_alerts.json`)

```json
{
  "generated_at": "2023-12-01T10:30:00+00:00",
  "total_processed": 2101,
  "total_alerts": 87,
  "fraud_rate_pct": 4.14,
  "alerts": [
    {
      "transaction_id": "abc-123",
      "user_id": "user-42",
      "timestamp": "2023-06-01 02:30:00",
      "amount": 25000.0,
      "risk_score": 155,
      "triggered_rules": [
        "HighAmountRule: +50",
        "OddHoursRule: +30",
        "VelocityRule: +40",
        "UnusualAmountRule: +35"
      ],
      "risk_level": "CRITICAL"
    }
  ]
}
```

---

## 🧪 Testing

The project includes comprehensive test coverage:

```bash
# Run all tests with verbose output
pytest tests/ -v

# Expected output:
# tests/test_rules.py::TestHighAmountRule::test_triggers_above_threshold      PASSED
# tests/test_rules.py::TestHighAmountRule::test_does_not_trigger_below        PASSED
# tests/test_rules.py::TestOddHoursRule::test_triggers_during_odd_hours      PASSED
# ...
# tests/test_engine.py::TestBatchEvaluation::test_batch_processes_all        PASSED
# tests/test_engine.py::TestAlertGeneration::test_risk_level_classification  PASSED
# ============= 20+ passed =============
```

---

## 🎯 Skills Demonstrated

This project was designed to showcase **senior-level engineering capabilities** for recruiters and hiring managers:

| Skill Area | Demonstrated By |
|------------|----------------|
| **Python OOP** | Abstract base classes, dataclasses, inheritance |
| **SOLID Principles** | Strategy Pattern, Open/Closed, Single Responsibility |
| **Pandas** | DataFrame manipulation, groupby operations, data validation |
| **Rule Engines** | Configurable, extensible rule evaluation system |
| **Config-Driven Design** | YAML-based configuration with runtime validation |
| **Unit Testing** | pytest with fixtures, boundary testing, integration tests |
| **Error Handling** | Fail-safe processing, structured logging, graceful degradation |
| **Type Safety** | Comprehensive type hints, dataclasses, typed interfaces |
| **Production Patterns** | Logging, CLI arguments, JSON reporting, console UX |
| **Clean Code** | Google-style docstrings, clear naming, modular architecture |

---

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">
  <strong>Built with ❤️ for Fintech Risk Management</strong>
</p>
