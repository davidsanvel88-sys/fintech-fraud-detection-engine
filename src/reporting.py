"""
Reporting module for the Fraud Detection Engine.

Generates structured JSON output files and rich console summaries
with color-coded risk indicators and formatted tables.
"""

import io
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.engine import FraudEngine
from src.loader import Transaction

logger = logging.getLogger("fraud_engine.reporting")

# Force UTF-8 output to avoid Windows cp1252 encoding errors with rich
_utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_utf8_stdout, force_terminal=True)


def generate_json_report(
    engine: FraudEngine,
    transactions: list[Transaction],
    alerts: list[Transaction],
    output_path: str,
) -> dict[str, Any]:
    """Generate a structured JSON report of all fraud alerts.

    The report includes metadata (timestamp, totals, fraud rate)
    and a detailed list of each alerted transaction.

    Args:
        engine: The FraudEngine instance (used for risk classification).
        transactions: All evaluated transactions.
        alerts: Transactions that exceeded the alert threshold.
        output_path: File path to write the JSON report.

    Returns:
        The report dictionary (also written to disk).
    """
    total_processed = len(transactions)
    total_alerts = len(alerts)
    fraud_rate = (total_alerts / total_processed * 100) if total_processed > 0 else 0.0

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_processed": total_processed,
        "total_alerts": total_alerts,
        "fraud_rate_pct": round(fraud_rate, 2),
        "alerts": [],
    }

    for tx in alerts:
        alert_entry = {
            "transaction_id": tx.transaction_id,
            "user_id": tx.user_id,
            "timestamp": tx.timestamp,
            "amount": tx.amount,
            "risk_score": tx.risk_score,
            "triggered_rules": tx.triggered_rules,
            "risk_level": engine.classify_risk_level(tx),
        }
        report["alerts"].append(alert_entry)

    # Sort alerts by risk_score descending for readability
    report["alerts"].sort(key=lambda x: x["risk_score"], reverse=True)

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("JSON report written to: %s", output_path)
    return report


def print_console_report(
    engine: FraudEngine,
    transactions: list[Transaction],
    alerts: list[Transaction],
) -> None:
    """Print a rich, color-coded executive summary to the console.

    Displays a formatted panel with key metrics, followed by a
    table showing the top triggered rules.

    Args:
        engine: The FraudEngine instance (used for rule statistics).
        transactions: All evaluated transactions.
        alerts: Transactions that exceeded the alert threshold.
    """
    total = len(transactions)
    total_alerts = len(alerts)
    fraud_rate = (total_alerts / total * 100) if total > 0 else 0.0
    avg_score = (
        sum(tx.risk_score for tx in transactions) / total
        if total > 0
        else 0.0
    )

    # Get rule statistics
    rule_stats = engine.get_rule_statistics(transactions)
    most_active_rule = next(iter(rule_stats), "N/A")

    # Build the summary panel
    console.print()
    summary_lines = [
        f"  [bold cyan]Total Processed[/bold cyan]   :  [white]{total:,}[/white]",
        f"  [bold yellow]Alerts Generated[/bold yellow]  :  [bold red]{total_alerts:,}[/bold red]  [dim]({fraud_rate:.2f}%)[/dim]",
        f"  [bold cyan]Average Score[/bold cyan]     :  [white]{avg_score:.1f}[/white]",
        f"  [bold cyan]Most Active Rule[/bold cyan]  :  [bold magenta]{most_active_rule}[/bold magenta]",
    ]

    # Risk distribution
    critical_count = sum(
        1 for tx in alerts if engine.classify_risk_level(tx) == "CRITICAL"
    )
    high_count = total_alerts - critical_count
    summary_lines.append("")
    summary_lines.append(
        f"  [bold red]CRITICAL Alerts[/bold red]   :  [bold red]{critical_count}[/bold red]"
    )
    summary_lines.append(
        f"  [bold yellow]HIGH Alerts[/bold yellow]       :  [bold yellow]{high_count}[/bold yellow]"
    )

    panel_content = "\n".join(summary_lines)
    console.print(
        Panel(
            panel_content,
            title="[bold white]🛡️  FRAUD DETECTION ENGINE — REPORT[/bold white]",
            subtitle="[dim]Powered by Rule-Based Risk Scoring[/dim]",
            border_style="bright_blue",
            padding=(1, 2),
        )
    )

    # Rule breakdown table
    if rule_stats:
        console.print()
        table = Table(
            title="📊 Rule Trigger Breakdown",
            border_style="bright_blue",
            header_style="bold bright_cyan",
            show_lines=True,
        )
        table.add_column("Rule", style="bold white", min_width=22)
        table.add_column("Triggers", style="bold yellow", justify="right")
        table.add_column("% of Total", style="dim", justify="right")

        for rule_name, count in rule_stats.items():
            pct = (count / total * 100) if total > 0 else 0.0
            table.add_row(rule_name, f"{count:,}", f"{pct:.1f}%")

        console.print(table)

    # Top 10 highest-risk alerts preview
    if alerts:
        console.print()
        alert_table = Table(
            title="🚨 Top 10 Highest-Risk Transactions",
            border_style="red",
            header_style="bold red",
            show_lines=True,
        )
        alert_table.add_column("Transaction ID", style="dim", max_width=20)
        alert_table.add_column("User", style="white")
        alert_table.add_column("Amount", style="bold green", justify="right")
        alert_table.add_column("Score", style="bold yellow", justify="right")
        alert_table.add_column("Level", justify="center")
        alert_table.add_column("Rules Triggered", style="dim", max_width=40)

        sorted_alerts = sorted(alerts, key=lambda x: x.risk_score, reverse=True)[:10]
        for tx in sorted_alerts:
            risk_level = engine.classify_risk_level(tx)
            level_style = "bold red" if risk_level == "CRITICAL" else "bold yellow"
            level_text = Text(risk_level, style=level_style)
            rules_str = ", ".join(tx.triggered_rules)

            alert_table.add_row(
                tx.transaction_id[:16] + "…",
                tx.user_id,
                f"${tx.amount:,.2f}",
                str(tx.risk_score),
                level_text,
                rules_str,
            )

        console.print(alert_table)

    console.print()
    console.print(
        "[bold green]✅ Report generation complete.[/bold green]"
    )
    console.print()
