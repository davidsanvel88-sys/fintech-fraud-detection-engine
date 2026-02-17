"""
Dashboard generator for the Fraud Detection Engine.

Produces a standalone HTML dashboard with interactive charts
powered by Chart.js. The HTML file is fully self-contained —
all data is embedded as JSON, no server required.

Locale: Spanish (MX)
Timezone: America/Mexico_City (UTC-6)
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from src.engine import FraudEngine
from src.loader import Transaction

logger = logging.getLogger("fraud_engine.dashboard")

# Mexico City timezone offset (UTC-6)
MX_TZ = timezone(timedelta(hours=-6))


def _compute_dashboard_data(
    engine: FraudEngine,
    transactions: list[Transaction],
    alerts: list[Transaction],
) -> dict[str, Any]:
    """Compute all metrics and breakdowns needed for the dashboard.

    Args:
        engine: The FraudEngine instance.
        transactions: All evaluated transactions.
        alerts: Transactions that exceeded the alert threshold.

    Returns:
        A dictionary with all chart data and summary metrics.
    """
    total = len(transactions)
    total_alerts = len(alerts)
    fraud_rate = (total_alerts / total * 100) if total > 0 else 0.0
    avg_score = sum(tx.risk_score for tx in transactions) / total if total else 0.0
    max_score = max((tx.risk_score for tx in transactions), default=0)

    # Risk level breakdown
    critical = sum(1 for tx in alerts if engine.classify_risk_level(tx) == "CRITICAL")
    high = total_alerts - critical
    no_alert = total - total_alerts

    # Rule trigger counts
    rule_stats = engine.get_rule_statistics(transactions)

    # Score distribution buckets
    buckets = {"0": 0, "1-25": 0, "26-50": 0, "51-75": 0, "76-100": 0, "101-150": 0, "150+": 0}
    for tx in transactions:
        s = tx.risk_score
        if s == 0:
            buckets["0"] += 1
        elif s <= 25:
            buckets["1-25"] += 1
        elif s <= 50:
            buckets["26-50"] += 1
        elif s <= 75:
            buckets["51-75"] += 1
        elif s <= 100:
            buckets["76-100"] += 1
        elif s <= 150:
            buckets["101-150"] += 1
        else:
            buckets["150+"] += 1

    # Alerts by hour of day
    hour_counts = {str(h): 0 for h in range(24)}
    for tx in alerts:
        hour_counts[str(tx.hour)] = hour_counts.get(str(tx.hour), 0) + 1

    # Alerts by category
    category_counts: dict[str, int] = {}
    for tx in alerts:
        category_counts[tx.category] = category_counts.get(tx.category, 0) + 1

    # Alerts by location
    location_counts: dict[str, int] = {}
    for tx in alerts:
        location_counts[tx.location] = location_counts.get(tx.location, 0) + 1

    # Top 15 riskiest transactions
    sorted_alerts = sorted(alerts, key=lambda x: x.risk_score, reverse=True)[:15]
    top_alerts = [
        {
            "id": tx.transaction_id[:16],
            "user": tx.user_id,
            "amount": tx.amount,
            "score": tx.risk_score,
            "level": engine.classify_risk_level(tx),
            "rules": tx.triggered_rules,
            "hour": tx.hour,
            "location": tx.location,
            "timestamp": tx.timestamp,
        }
        for tx in sorted_alerts
    ]

    # Fraud vs legit by hour
    fraud_by_hour = {h: 0 for h in range(24)}
    legit_by_hour = {h: 0 for h in range(24)}
    for tx in transactions:
        if tx.risk_score >= engine.alert_threshold:
            fraud_by_hour[tx.hour] += 1
        else:
            legit_by_hour[tx.hour] += 1

    # Amount ranges for alerts
    amount_ranges = {"$0-1K": 0, "$1K-5K": 0, "$5K-15K": 0, "$15K-30K": 0, "$30K+": 0}
    for tx in alerts:
        a = tx.amount
        if a < 1000:
            amount_ranges["$0-1K"] += 1
        elif a < 5000:
            amount_ranges["$1K-5K"] += 1
        elif a < 15000:
            amount_ranges["$5K-15K"] += 1
        elif a < 30000:
            amount_ranges["$15K-30K"] += 1
        else:
            amount_ranges["$30K+"] += 1

    # Weekend vs weekday
    weekend_alerts = sum(1 for tx in alerts if tx.is_weekend == 1)
    weekday_alerts = total_alerts - weekend_alerts

    # Timestamp in Mexico City timezone
    now_mx = datetime.now(MX_TZ)
    generated_str = now_mx.strftime("%d de %B de %Y, %H:%M:%S hrs (Centro de México)")
    # Translate month names to Spanish
    month_map = {
        "January": "enero", "February": "febrero", "March": "marzo",
        "April": "abril", "May": "mayo", "June": "junio",
        "July": "julio", "August": "agosto", "September": "septiembre",
        "October": "octubre", "November": "noviembre", "December": "diciembre",
    }
    for eng, esp in month_map.items():
        generated_str = generated_str.replace(eng, esp)

    return {
        "generated_at": generated_str,
        "summary": {
            "total": total,
            "alerts": total_alerts,
            "fraud_rate": round(fraud_rate, 2),
            "avg_score": round(avg_score, 1),
            "max_score": max_score,
            "critical": critical,
            "high": high,
            "no_alert": no_alert,
        },
        "rule_stats": rule_stats,
        "score_distribution": buckets,
        "alerts_by_hour": {int(k): v for k, v in hour_counts.items()},
        "fraud_by_hour": fraud_by_hour,
        "legit_by_hour": legit_by_hour,
        "category_counts": category_counts,
        "location_counts": location_counts,
        "amount_ranges": amount_ranges,
        "weekend_vs_weekday": {"Fin de semana": weekend_alerts, "Entre semana": weekday_alerts},
        "risk_breakdown": {"CR\u00cdTICO": critical, "ALTO": high, "Limpia": no_alert},
        "top_alerts": top_alerts,
    }


def generate_dashboard(
    engine: FraudEngine,
    transactions: list[Transaction],
    alerts: list[Transaction],
    output_path: str = "dashboard.html",
) -> str:
    """Generate a standalone HTML dashboard with interactive charts.

    Args:
        engine: The FraudEngine instance.
        transactions: All evaluated transactions.
        alerts: Transactions that exceeded the alert threshold.
        output_path: File path for the generated HTML dashboard.

    Returns:
        The output file path.
    """
    data = _compute_dashboard_data(engine, transactions, alerts)
    data_json = json.dumps(data, ensure_ascii=False)
    html = _build_html(data_json, data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Dashboard generated: %s", output_path)
    return output_path


def _build_html(data_json: str, data: dict[str, Any]) -> str:
    """Build the complete HTML string for the dashboard."""
    s = data["summary"]

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Motor de Detección de Fraude — Dashboard Ejecutivo</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root {{
  /* Executive palette — deep navy, slate, gold, teal */
  --bg-primary: #0b1120;
  --bg-secondary: #0f1729;
  --bg-card: #141d2f;
  --bg-card-alt: #182338;
  --border: #1e2d45;
  --border-accent: #2a3f5f;
  --text-primary: #e8ecf4;
  --text-secondary: #8899b3;
  --text-muted: #5a6d87;

  /* Executive accent colors */
  --gold: #d4a843;
  --gold-dim: rgba(212,168,67,0.15);
  --teal: #2ec4b6;
  --teal-dim: rgba(46,196,182,0.12);
  --navy: #4a7cce;
  --navy-dim: rgba(74,124,206,0.12);
  --crimson: #dc3545;
  --crimson-dim: rgba(220,53,69,0.12);
  --amber: #e8913a;
  --amber-dim: rgba(232,145,58,0.12);
  --slate-blue: #6c7ea0;
  --steel: #3d5a80;
  --pearl: #c9d6e3;

  /* Gradients */
  --grad-gold: linear-gradient(135deg, #d4a843 0%, #b8892e 100%);
  --grad-navy: linear-gradient(135deg, #4a7cce 0%, #3461a8 100%);
  --grad-teal: linear-gradient(135deg, #2ec4b6 0%, #1fa393 100%);
  --grad-crimson: linear-gradient(135deg, #dc3545 0%, #b82d3a 100%);

  --shadow: 0 2px 16px rgba(0,0,0,0.35);
  --shadow-hover: 0 6px 28px rgba(0,0,0,0.45);
  --radius: 12px;
}}

* {{ margin:0; padding:0; box-sizing:border-box; }}

body {{
  font-family: 'Inter', -apple-system, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
}}
body::before {{
  content: '';
  position: fixed; inset: 0;
  background:
    radial-gradient(ellipse at 15% 10%, rgba(74,124,206,0.06) 0%, transparent 55%),
    radial-gradient(ellipse at 85% 90%, rgba(212,168,67,0.04) 0%, transparent 50%);
  pointer-events: none;
}}

.dash {{ position:relative; z-index:1; padding:20px 24px; max-width:1560px; margin:0 auto; }}

/* ── Header ── */
.hdr {{
  display:flex; align-items:center; justify-content:space-between;
  padding:24px 32px; margin-bottom:22px;
  background: var(--bg-card);
  border:1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  position:relative; overflow:hidden;
}}
.hdr::after {{
  content:''; position:absolute; bottom:0; left:0; right:0; height:2px;
  background: var(--grad-gold);
}}
.hdr-left h1 {{
  font-size:1.55rem; font-weight:800; letter-spacing:-0.3px;
  color: var(--gold);
}}
.hdr-left .sub {{
  font-size:0.82rem; color:var(--text-secondary); margin-top:3px; font-weight:400;
}}
.hdr-right {{
  text-align:right;
}}
.hdr-right .ts {{
  font-size:0.72rem; color:var(--text-muted); font-weight:400;
}}
.hdr-right .badge-live {{
  display:inline-block; padding:4px 14px; border-radius:50px;
  font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:1px;
  background: var(--teal-dim); color:var(--teal); border:1px solid rgba(46,196,182,0.25);
  margin-bottom:6px;
}}

/* ── KPI Row ── */
.kpi {{ display:grid; grid-template-columns:repeat(6,1fr); gap:14px; margin-bottom:22px; }}
@media(max-width:1100px){{ .kpi {{ grid-template-columns:repeat(3,1fr); }} }}
@media(max-width:640px){{ .kpi {{ grid-template-columns:repeat(2,1fr); }} }}

.k {{
  background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius);
  padding:20px 18px; text-align:center; box-shadow:var(--shadow);
  transition: transform .2s, box-shadow .2s, border-color .3s;
  position:relative; overflow:hidden;
}}
.k:hover {{ transform:translateY(-3px); box-shadow:var(--shadow-hover); border-color:var(--border-accent); }}
.k::before {{ content:''; position:absolute; top:0; left:0; right:0; height:2.5px; }}
.k:nth-child(1)::before {{ background:var(--grad-teal); }}
.k:nth-child(2)::before {{ background:var(--grad-crimson); }}
.k:nth-child(3)::before {{ background:var(--grad-crimson); }}
.k:nth-child(4)::before {{ background:var(--grad-gold); }}
.k:nth-child(5)::before {{ background:var(--grad-navy); }}
.k:nth-child(6)::before {{ background:var(--grad-gold); }}

.k-label {{
  font-size:0.65rem; text-transform:uppercase; letter-spacing:1.8px;
  color:var(--text-muted); font-weight:600; margin-bottom:8px;
}}
.k-val {{
  font-size:2rem; font-weight:800; line-height:1; margin-bottom:4px;
  font-variant-numeric: tabular-nums;
}}
.k-sub {{ font-size:0.72rem; color:var(--text-secondary); }}

.k-val.v-teal    {{ color:var(--teal); }}
.k-val.v-crimson {{ color:var(--crimson); }}
.k-val.v-gold    {{ color:var(--gold); }}
.k-val.v-navy    {{ color:var(--navy); }}
.k-val.v-amber   {{ color:var(--amber); }}

/* ── Charts ── */
.grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:16px; margin-bottom:18px; }}
@media(max-width:1024px){{ .grid {{ grid-template-columns:1fr; }} }}

.card {{
  background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius);
  padding:22px 24px; box-shadow:var(--shadow);
  transition: border-color .3s;
}}
.card:hover {{ border-color:var(--border-accent); }}
.card.full {{ grid-column:1/-1; }}

.card-t {{
  font-size:0.85rem; font-weight:700; color:var(--text-secondary);
  text-transform:uppercase; letter-spacing:0.8px; margin-bottom:16px;
  padding-bottom:10px; border-bottom:1px solid var(--border);
  display:flex; align-items:center; gap:8px;
}}
.card-t .dot {{
  width:8px; height:8px; border-radius:50%; display:inline-block;
}}
.cc {{ position:relative; width:100%; height:270px; }}
.cc.tall {{ height:340px; }}

/* ── Table ── */
.tw {{ overflow-x:auto; margin-top:4px; }}
table {{ width:100%; border-collapse:collapse; font-size:0.78rem; }}
th {{
  background: var(--bg-card-alt);
  color:var(--gold); font-weight:600; text-transform:uppercase;
  font-size:0.65rem; letter-spacing:1.2px;
  padding:11px 14px; text-align:left;
  border-bottom:2px solid var(--border-accent);
}}
td {{
  padding:9px 14px; border-bottom:1px solid var(--border);
  color:var(--text-secondary); vertical-align:middle;
}}
tr:hover td {{ background:rgba(74,124,206,0.04); color:var(--text-primary); }}

.badge {{
  display:inline-block; padding:3px 10px; border-radius:50px;
  font-size:0.63rem; font-weight:700; text-transform:uppercase; letter-spacing:0.6px;
}}
.badge.critico {{
  background:var(--crimson-dim); color:#f0616d; border:1px solid rgba(220,53,69,0.3);
}}
.badge.alto {{
  background:var(--amber-dim); color:var(--amber); border:1px solid rgba(232,145,58,0.3);
}}
.rtag {{
  display:inline-block; padding:2px 8px; border-radius:4px;
  font-size:0.62rem; white-space:nowrap;
  background:var(--navy-dim); color:var(--slate-blue);
  border:1px solid rgba(74,124,206,0.18);
  margin:1px 2px;
}}

.foot {{
  text-align:center; padding:20px; color:var(--text-muted);
  font-size:0.7rem; border-top:1px solid var(--border); margin-top:12px;
}}

@keyframes fadeUp {{
  from {{ opacity:0; transform:translateY(14px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
.k, .card {{ animation: fadeUp .45s ease forwards; }}
.k:nth-child(2){{ animation-delay:.04s; }}
.k:nth-child(3){{ animation-delay:.08s; }}
.k:nth-child(4){{ animation-delay:.12s; }}
.k:nth-child(5){{ animation-delay:.16s; }}
.k:nth-child(6){{ animation-delay:.20s; }}
</style>
</head>
<body>
<div class="dash">

<!-- Header -->
<div class="hdr">
  <div class="hdr-left">
    <h1>MOTOR DE DETECCI&Oacute;N DE FRAUDE</h1>
    <div class="sub">Dashboard Ejecutivo &mdash; An&aacute;lisis de Riesgo en Tiempo Real</div>
  </div>
  <div class="hdr-right">
    <div class="badge-live">&#9679; Reporte Generado</div><br>
    <span class="ts">{data["generated_at"]}</span>
  </div>
</div>

<!-- KPIs -->
<div class="kpi">
  <div class="k">
    <div class="k-label">Total Procesado</div>
    <div class="k-val v-teal">{s["total"]:,}</div>
    <div class="k-sub">transacciones analizadas</div>
  </div>
  <div class="k">
    <div class="k-label">Alertas de Fraude</div>
    <div class="k-val v-crimson">{s["alerts"]:,}</div>
    <div class="k-sub">{s["fraud_rate"]}% tasa de fraude</div>
  </div>
  <div class="k">
    <div class="k-label">Alertas Cr&iacute;ticas</div>
    <div class="k-val v-crimson">{s["critical"]}</div>
    <div class="k-sub">puntuaci&oacute;n &ge; 120</div>
  </div>
  <div class="k">
    <div class="k-label">Alertas Altas</div>
    <div class="k-val v-amber">{s["high"]}</div>
    <div class="k-sub">puntuaci&oacute;n 75 &ndash; 119</div>
  </div>
  <div class="k">
    <div class="k-label">Puntuaci&oacute;n Promedio</div>
    <div class="k-val v-navy">{s["avg_score"]}</div>
    <div class="k-sub">en todas las transacciones</div>
  </div>
  <div class="k">
    <div class="k-label">Puntuaci&oacute;n M&aacute;xima</div>
    <div class="k-val v-gold">{s["max_score"]}</div>
    <div class="k-sub">riesgo m&aacute;s alto detectado</div>
  </div>
</div>

<!-- Charts -->
<div class="grid">
  <div class="card">
    <div class="card-t"><span class="dot" style="background:var(--navy)"></span> Distribuci&oacute;n de Puntuaci&oacute;n de Riesgo</div>
    <div class="cc"><canvas id="cScore"></canvas></div>
  </div>
  <div class="card">
    <div class="card-t"><span class="dot" style="background:var(--gold)"></span> Frecuencia de Activaci&oacute;n por Regla</div>
    <div class="cc"><canvas id="cRule"></canvas></div>
  </div>
  <div class="card">
    <div class="card-t"><span class="dot" style="background:var(--crimson)"></span> Alertas por Hora del D&iacute;a</div>
    <div class="cc"><canvas id="cHour"></canvas></div>
  </div>
  <div class="card">
    <div class="card-t"><span class="dot" style="background:var(--teal)"></span> Desglose de Nivel de Riesgo</div>
    <div class="cc"><canvas id="cRisk"></canvas></div>
  </div>
  <div class="card">
    <div class="card-t"><span class="dot" style="background:var(--amber)"></span> Distribuci&oacute;n por Monto de Alerta</div>
    <div class="cc"><canvas id="cAmount"></canvas></div>
  </div>
  <div class="card">
    <div class="card-t"><span class="dot" style="background:var(--steel)"></span> Alertas por Ubicaci&oacute;n</div>
    <div class="cc"><canvas id="cLoc"></canvas></div>
  </div>
  <div class="card">
    <div class="card-t"><span class="dot" style="background:var(--navy)"></span> Fin de Semana vs Entre Semana</div>
    <div class="cc"><canvas id="cWeek"></canvas></div>
  </div>
  <div class="card">
    <div class="card-t"><span class="dot" style="background:var(--gold)"></span> Alertas por Categor&iacute;a</div>
    <div class="cc"><canvas id="cCat"></canvas></div>
  </div>
</div>

<!-- Alerts Table -->
<div class="grid">
  <div class="card full">
    <div class="card-t"><span class="dot" style="background:var(--crimson)"></span> Top 15 Transacciones de Mayor Riesgo</div>
    <div class="tw">
      <table id="tbl">
        <thead><tr>
          <th>ID Transacci&oacute;n</th><th>Usuario</th><th>Fecha y Hora</th>
          <th>Monto</th><th>Ubicaci&oacute;n</th><th>Puntuaci&oacute;n</th>
          <th>Nivel</th><th>Reglas Activadas</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
</div>

<div class="foot">
  Motor de Detecci&oacute;n de Fraude &bull; Dashboard Ejecutivo &bull; Zona Horaria: Centro de M&eacute;xico (UTC-6)
</div>

</div>
<script>
const D={data_json};

/* Chart.js Defaults — Executive theme */
Chart.defaults.color='#8899b3';
Chart.defaults.borderColor='rgba(30,45,69,0.6)';
Chart.defaults.font.family="'Inter',sans-serif";
Chart.defaults.font.size=11;
Chart.defaults.plugins.legend.labels.usePointStyle=true;
Chart.defaults.plugins.legend.labels.pointStyle='circle';
Chart.defaults.plugins.legend.labels.padding=14;
Chart.defaults.plugins.tooltip.backgroundColor='#1a2744';
Chart.defaults.plugins.tooltip.titleColor='#d4a843';
Chart.defaults.plugins.tooltip.bodyColor='#c9d6e3';
Chart.defaults.plugins.tooltip.borderColor='#2a3f5f';
Chart.defaults.plugins.tooltip.borderWidth=1;
Chart.defaults.plugins.tooltip.cornerRadius=8;
Chart.defaults.plugins.tooltip.padding=10;

/* Executive color palette */
const C={{
  navy:'rgba(74,124,206,0.85)',   teal:'rgba(46,196,182,0.85)',
  gold:'rgba(212,168,67,0.85)',   crimson:'rgba(220,53,69,0.85)',
  amber:'rgba(232,145,58,0.85)',  steel:'rgba(61,90,128,0.85)',
  slate:'rgba(108,126,160,0.85)', pearl:'rgba(160,180,200,0.8)',
}};
const P=[C.navy,C.teal,C.gold,C.crimson,C.amber,C.steel,C.slate,C.pearl];
const gridC='rgba(30,45,69,0.4)';

/* 1 — Distribución Score */
new Chart(document.getElementById('cScore'),{{
  type:'bar',
  data:{{
    labels:Object.keys(D.score_distribution),
    datasets:[{{
      label:'Transacciones',
      data:Object.values(D.score_distribution),
      backgroundColor:[C.teal,C.navy,C.steel,C.gold,C.amber,C.crimson,'rgba(180,50,60,0.85)'],
      borderRadius:5, borderSkipped:false,
    }}]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      y:{{beginAtZero:true,grid:{{color:gridC}},ticks:{{font:{{size:10}}}}}},
      x:{{grid:{{display:false}},ticks:{{font:{{size:10}}}}}}
    }}
  }}
}});

/* 2 — Reglas */
new Chart(document.getElementById('cRule'),{{
  type:'bar',
  data:{{
    labels:Object.keys(D.rule_stats),
    datasets:[{{
      label:'Veces activada',
      data:Object.values(D.rule_stats),
      backgroundColor:P.slice(0,Object.keys(D.rule_stats).length),
      borderRadius:5, borderSkipped:false,
    }}]
  }},
  options:{{
    indexAxis:'y', responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{beginAtZero:true,grid:{{color:gridC}}}},
      y:{{grid:{{display:false}},ticks:{{font:{{size:10}}}}}}
    }}
  }}
}});

/* 3 — Alertas por Hora */
new Chart(document.getElementById('cHour'),{{
  type:'line',
  data:{{
    labels:Array.from({{length:24}},(_,i)=>i+':00'),
    datasets:[
      {{
        label:'Alertas de Fraude',
        data:Object.values(D.fraud_by_hour),
        borderColor:C.crimson, backgroundColor:'rgba(220,53,69,0.08)',
        fill:true, tension:.4, pointRadius:3, pointHoverRadius:6,
        pointBackgroundColor:C.crimson, borderWidth:2,
      }},
      {{
        label:'Transacciones Limpias',
        data:Object.values(D.legit_by_hour),
        borderColor:C.teal, backgroundColor:'rgba(46,196,182,0.05)',
        fill:true, tension:.4, pointRadius:2, pointHoverRadius:5,
        pointBackgroundColor:C.teal, borderWidth:2,
      }}
    ]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{position:'top'}}}},
    scales:{{
      y:{{beginAtZero:true,grid:{{color:gridC}}}},
      x:{{grid:{{display:false}},ticks:{{maxRotation:45,font:{{size:9}}}}}}
    }}
  }}
}});

/* 4 — Nivel de Riesgo */
new Chart(document.getElementById('cRisk'),{{
  type:'doughnut',
  data:{{
    labels:Object.keys(D.risk_breakdown),
    datasets:[{{
      data:Object.values(D.risk_breakdown),
      backgroundColor:[C.crimson,C.amber,C.teal],
      borderColor:'var(--bg-card)', borderWidth:3, hoverOffset:8,
    }}]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false, cutout:'60%',
    plugins:{{legend:{{position:'bottom',labels:{{font:{{size:11}}}}}}}}
  }}
}});

/* 5 — Montos */
new Chart(document.getElementById('cAmount'),{{
  type:'bar',
  data:{{
    labels:Object.keys(D.amount_ranges),
    datasets:[{{
      label:'Alertas',
      data:Object.values(D.amount_ranges),
      backgroundColor:[C.teal,C.navy,C.steel,C.amber,C.crimson],
      borderRadius:5, borderSkipped:false,
    }}]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      y:{{beginAtZero:true,grid:{{color:gridC}}}},
      x:{{grid:{{display:false}}}}
    }}
  }}
}});

/* 6 — Ubicación */
const ll=Object.keys(D.location_counts);
new Chart(document.getElementById('cLoc'),{{
  type:'polarArea',
  data:{{
    labels:ll,
    datasets:[{{
      data:Object.values(D.location_counts),
      backgroundColor:P.slice(0,ll.length).map(c=>c.replace('0.85','0.55')),
      borderColor:P.slice(0,ll.length), borderWidth:1,
    }}]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{position:'right',labels:{{font:{{size:10}}}}}}}},
    scales:{{r:{{grid:{{color:gridC}},ticks:{{display:false}}}}}}
  }}
}});

/* 7 — Fin de semana */
new Chart(document.getElementById('cWeek'),{{
  type:'doughnut',
  data:{{
    labels:Object.keys(D.weekend_vs_weekday),
    datasets:[{{
      data:Object.values(D.weekend_vs_weekday),
      backgroundColor:[C.navy,C.gold],
      borderColor:'var(--bg-card)', borderWidth:3, hoverOffset:8,
    }}]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false, cutout:'55%',
    plugins:{{legend:{{position:'bottom'}}}}
  }}
}});

/* 8 — Categoría */
const cl=Object.keys(D.category_counts);
new Chart(document.getElementById('cCat'),{{
  type:'pie',
  data:{{
    labels:cl,
    datasets:[{{
      data:Object.values(D.category_counts),
      backgroundColor:P.slice(0,cl.length),
      borderColor:'rgba(20,29,47,0.9)', borderWidth:2, hoverOffset:8,
    }}]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{position:'bottom',labels:{{font:{{size:11}}}}}}}}
  }}
}});

/* ── Tabla ── */
const tb=document.querySelector('#tbl tbody');
D.top_alerts.forEach(a=>{{
  const bc=a.level==='CRITICAL'?'critico':'alto';
  const lvl=a.level==='CRITICAL'?'CR\\u00cdTICO':'ALTO';
  const rh=a.rules.map(r=>`<span class="rtag">${{r}}</span>`).join('');
  tb.innerHTML+=`
    <tr>
      <td style="font-family:monospace;font-size:.72rem;color:var(--text-muted)">${{a.id}}&hellip;</td>
      <td style="font-weight:600">${{a.user}}</td>
      <td>${{a.timestamp}}</td>
      <td style="color:var(--teal);font-weight:700">${{a.amount.toLocaleString('es-MX',{{style:'currency',currency:'MXN'}})}}</td>
      <td>${{a.location}}</td>
      <td style="font-weight:800;color:var(--gold)">${{a.score}}</td>
      <td><span class="badge ${{bc}}">${{lvl}}</span></td>
      <td><div style="display:flex;flex-wrap:wrap;gap:3px">${{rh}}</div></td>
    </tr>`;
}});
</script>
</body>
</html>"""
