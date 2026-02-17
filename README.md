# 🛡️ Motor de Detección de Fraude — Fintech

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458?logo=pandas&logoColor=white)
![License](https://img.shields.io/badge/Licencia-MIT-green)
![Tests](https://img.shields.io/badge/Tests-32%20Passing-brightgreen?logo=pytest)
![SOLID](https://img.shields.io/badge/Diseño-Principios%20SOLID-orange)

> **Motor de detección de fraude de nivel producción**, config-driven, construido con principios SOLID y el Strategy Pattern para evaluar riesgo transaccional en tiempo real.

---

## 📋 Tabla de Contenido

- [Descripción General](#-descripción-general)
- [Arquitectura](#️-arquitectura)
- [Características](#-características)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Configuración](#️-configuración)
- [Reglas de Negocio](#-reglas-de-negocio)
- [Ejemplos de Salida](#-ejemplos-de-salida)
- [Dashboard Ejecutivo](#-dashboard-ejecutivo)
- [Testing](#-testing)
- [Habilidades Demostradas](#-habilidades-demostradas)

---

## 🔍 Descripción General

Este motor procesa transacciones financieras desde un dataset CSV, evalúa cada una contra un conjunto configurable de reglas de detección de fraude, y genera reportes de alertas en formato JSON, consola enriquecida y un **dashboard ejecutivo interactivo**. Diseñado como un **proyecto de portafolio senior**, demuestra prácticas de ingeniería aplicadas en sistemas de gestión de riesgo fintech del mundo real.

### Decisiones de Diseño Clave

- **Strategy Pattern** para reglas: cada regla es una clase independiente, permitiendo lógica de fraude intercambiable
- **Umbrales config-driven**: todos los parámetros viven en `config.yaml`, no en el código
- **Procesamiento fail-safe**: transacciones corruptas se loggean y se omiten, nunca detienen el pipeline
- **Salida enriquecida en consola**: resúmenes ejecutivos con indicadores de riesgo a color
- **Dashboard interactivo**: 8 gráficos Chart.js con paleta ejecutiva y zona horaria Centro de México

---

## 🏗️ Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py                                │
│                 (Orquestador del Pipeline)                     │
└──────────┬───────────────────────────────────────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐ ┌──────────────┐
│ config   │ │  loader.py   │
│  .yaml   │ │ (CSV → TX)   │
└──────────┘ └──────┬───────┘
                    │
                    ▼
           ┌────────────────┐
           │   engine.py    │  ← Registra y orquesta reglas
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
     ┌──────────────────────────┐
     │ reporting.py             │  → fraud_alerts.json
     │ dashboard.py             │  → dashboard.html
     │ (JSON + Rich + Chart.js) │  → Reporte en Consola
     └──────────────────────────┘
```

---

## ✨ Características

| Característica | Descripción |
|----------------|-------------|
| 🎯 **7 Reglas de Negocio** | Monto alto, horario inusual, velocidad, ratio atípico, cambio de ubicación, TX extranjera, dispositivo nuevo |
| ⚙️ **Config-Driven** | Todos los umbrales en `config.yaml` — cero cambios en código |
| 🧩 **Strategy Pattern** | Agregar nuevas reglas sin modificar el motor |
| 📊 **Dashboard Ejecutivo** | HTML interactivo con 8 gráficos Chart.js y paleta ejecutiva |
| 📄 **Reportes JSON** | Alertas estructuradas con timestamps y niveles de riesgo |
| 🖥️ **Consola Rich** | Paneles a color, tablas y previews de alertas top |
| 🛡️ **Fail-Safe** | Datos corruptos se loggean y omiten — nunca crashea |
| 🧪 **32 Tests** | Tests unitarios e integración con pytest |
| 📝 **Type-Safe** | Type hints completos con `dataclasses` |

---

## 🚀 Instalación

### Prerrequisitos

- Python 3.10 o superior
- pip como gestor de paquetes

### Configuración

```bash
# Clonar el repositorio
git clone https://github.com/davidsanvel88-sys/fintech-fraud-detection-engine.git
cd fintech-fraud-detection-engine

# Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate         # Windows
# source venv/bin/activate    # macOS/Linux

# Instalar dependencias
pip install -r requirements.txt
```

---

## 💻 Uso

### Ejecutar el Motor

```bash
# Configuración por defecto
python main.py

# Archivo de configuración personalizado
python main.py --config ruta/a/config_custom.yaml
```

El motor genera automáticamente:
- `fraud_alerts.json` — Reporte estructurado de alertas
- `dashboard.html` — Dashboard ejecutivo interactivo (abrir en navegador)
- Resumen ejecutivo en consola con Rich

### Ejecutar Tests

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Con salida resumida
python -m pytest tests/ -v --tb=short
```

---

## ⚙️ Configuración

Todos los umbrales y parámetros están externalizados en `config.yaml`:

```yaml
rules:
  high_amount:
    threshold: 15000    # Monto superior a este activa la alerta
    points: 50

  velocity:
    min_hours: 0.17     # Menos de ~10 minutos entre transacciones
    points: 40

alerting:
  risk_score_threshold: 75    # Puntuación mínima para ALERTA DE FRAUDE
  critical_threshold: 120     # Puntuación superior = CRÍTICO
```

**Para ajustar la sensibilidad**, simplemente edita `config.yaml` — sin cambios en código.

---

## 📏 Reglas de Negocio

| Regla | Condición | Puntos |
|-------|-----------|--------|
| `HighAmountRule` | `monto > 15,000` | +50 |
| `OddHoursRule` | Transacción entre 22:00–05:00 | +30 |
| `VelocityRule` | < 10 min desde última transacción | +40 |
| `UnusualAmountRule` | Monto > 3x promedio del usuario | +35 |
| `LocationChangeRule` | Cambio de ubicación en < 2 horas | +30 |
| `ForeignTxRule` | Ubicación extranjera detectada | +25 |
| `NewDeviceRule` | Dispositivo ≠ más frecuente del usuario | +20 |

**Umbral de alerta:** `risk_score ≥ 75` → **ALERTA DE FRAUDE**  
**Niveles de riesgo:** `75–119` = **ALTO** | `≥ 120` = **CRÍTICO**

---

## 📤 Ejemplos de Salida

### Reporte en Consola (Rich)

```
╭──────────────────────────────────────────────────────────────╮
│     🛡️  MOTOR DE DETECCIÓN DE FRAUDE — REPORTE               │
├──────────────────────────────────────────────────────────────┤
│  Total Procesado      :  2,101                                │
│  Alertas Generadas    :  39  (1.86%)                          │
│  Puntuación Promedio  :  16.8                                 │
│  Regla Más Activa     :  HighAmountRule                       │
│                                                               │
│  Alertas CRÍTICAS     :  17                                   │
│  Alertas ALTAS        :  22                                   │
╰──────────────────────────────────────────────────────────────╯
```

### Reporte JSON (`fraud_alerts.json`)

```json
{
  "generated_at": "2026-02-17T12:59:48+00:00",
  "total_processed": 2101,
  "total_alerts": 39,
  "fraud_rate_pct": 1.86,
  "alerts": [
    {
      "transaction_id": "1ec55761-3047-...",
      "user_id": "0468ca67",
      "timestamp": "2023-07-15 02:30:00",
      "amount": 43826.90,
      "risk_score": 135,
      "triggered_rules": [
        "HighAmountRule: +50",
        "OddHoursRule: +30",
        "UnusualAmountRule: +35",
        "NewDeviceRule: +20"
      ],
      "risk_level": "CRITICAL"
    }
  ]
}
```

---

## 📊 Dashboard Ejecutivo

El motor genera automáticamente un **dashboard HTML interactivo** (`dashboard.html`) con las siguientes visualizaciones:

| # | Gráfico | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | Distribución de Puntuación | Barras | Histograma de risk scores |
| 2 | Frecuencia por Regla | Barras horizontales | Veces que se activó cada regla |
| 3 | Alertas por Hora | Línea | Patrón temporal fraude vs legítimas |
| 4 | Nivel de Riesgo | Donut | CRÍTICO vs ALTO vs Limpia |
| 5 | Distribución por Monto | Barras | Rangos de monto en alertas |
| 6 | Alertas por Ubicación | Área polar | Distribución geográfica |
| 7 | Semana vs Fin de Semana | Donut | Patrón de días |
| 8 | Alertas por Categoría | Pie | Distribución por comercio |

**Características del dashboard:**
- 🎨 Paleta ejecutiva (navy, dorado, teal, crimson)
- 🕐 Zona horaria Centro de México (UTC-6)
- 📱 Diseño responsive
- 🖱️ Hover con animaciones y tooltips interactivos
- 📋 Tabla Top 15 transacciones de mayor riesgo

---

## 🧪 Testing

El proyecto incluye cobertura de tests completa con **32 tests**:

```bash
# Ejecutar todos los tests con salida verbose
python -m pytest tests/ -v

# Resultado esperado:
# tests/test_rules.py::TestHighAmountRule::test_triggers_above_threshold      PASSED
# tests/test_rules.py::TestHighAmountRule::test_does_not_trigger_below        PASSED
# tests/test_rules.py::TestOddHoursRule::test_triggers_during_odd_hours       PASSED
# ...
# tests/test_engine.py::TestBatchEvaluation::test_batch_processes_all         PASSED
# tests/test_engine.py::TestAlertGeneration::test_risk_level_classification   PASSED
# ============= 32 passed =============
```

---

## 🎯 Habilidades Demostradas

Este proyecto fue diseñado para demostrar **capacidades de ingeniería de nivel senior** para reclutadores y hiring managers:

| Área | Demostrada Mediante |
|------|---------------------|
| **Python OOP** | Clases abstractas, dataclasses, herencia |
| **Principios SOLID** | Strategy Pattern, Open/Closed, Responsabilidad Única |
| **Pandas** | Manipulación de DataFrames, operaciones groupby, validación |
| **Motor de Reglas** | Sistema de evaluación configurable y extensible |
| **Diseño Config-Driven** | Configuración YAML con validación en tiempo de ejecución |
| **Testing Unitario** | pytest con fixtures, pruebas de frontera, integración |
| **Manejo de Errores** | Procesamiento fail-safe, logging estructurado, degradación graceful |
| **Type Safety** | Type hints completos, dataclasses, interfaces tipadas |
| **Patrones de Producción** | Logging, argumentos CLI, reportes JSON, dashboard interactivo |
| **Código Limpio** | Docstrings Google-style, naming claro, arquitectura modular |

---

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT.

---

<p align="center">
  <strong>Construido con ❤️ para Gestión de Riesgo Fintech</strong><br>
  <sub>David Emanuel Velez — 2026</sub>
</p>
