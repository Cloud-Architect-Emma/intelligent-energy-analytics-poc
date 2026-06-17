<div align="center">

<img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=28&pause=1000&color=6366F1&center=true&vCenter=true&width=600&lines=⚡+Intelligent+Energy+Analytics;Production-Grade+ML+Pipeline;Real-Time+Predictive+Dashboard" alt="Typing SVG" />

# Intelligent Data Aggregation & Predictive Analytics Engine

**A production-grade, end-to-end data engineering and AI-powered analytics platform**
built entirely with free, open-source tools — no cloud account or credit card required.

<br/>

[![CI](https://github.com/Cloud-Architect-Emma/intelligent-energy-analytics-poc/actions/workflows/ci.yml/badge.svg)](https://github.com/Cloud-Architect-Emma/intelligent-energy-analytics-poc/actions)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![scipy](https://img.shields.io/badge/scipy-1.12-8CAAE6?style=flat-square&logo=scipy&logoColor=white)](https://scipy.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

<br/>

[**🚀 Live Demo**](https://intelligent-energy-analytics-poc.onrender.com) &nbsp;&nbsp;|&nbsp;&nbsp;
[**📖 API Docs**](#-api-reference) &nbsp;&nbsp;|&nbsp;&nbsp;
[**🏗️ Architecture**](#-architecture) &nbsp;&nbsp;|&nbsp;&nbsp;
[**☁️ Deploy**](#-deployment)

<br/>

</div>

---

##  Overview

This project simulates a real-world **utility company analytics platform** — the kind of system an energy provider or IoT analytics firm would build to understand and predict customer behaviour at scale.

| What it does | How |
|---|---|
| Ingests semi-structured telemetry from any source | REST API with full validation |
| Cleans, normalises, and enriches every record | Typed Python processing layer |
| Stores data in a structured warehouse | SQLite (DynamoDB-compatible schema) |
| Predicts next-month energy tier per customer | scipy trend model + sklearn Random Forest |
| Surfaces insights in real time | Interactive Flask dashboard |

> Everything runs **100% locally** and deploys to a **free cloud tier** in one click.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          ENTRY POINTS                            │
│                                                                  │
│     curl / browser              Dashboard UI      Batch jobs     │
│     (HTTP clients)              (Flask + JS)      (/predict)     │
└──────────┬──────────────────────────┬──────────────┬────────────┘
           │                          │              │
           └──────────────────────────▼──────────────┘
                                      │
┌─────────────────────────────────────▼────────────────────────────┐
│                     FLASK REST API   ·   app.py                  │
│                                                                  │
│    POST /ingest     POST /predict     GET /records    GET /health │
└──────────────────────┬──────────────────────┬────────────────────┘
                       │                      │
          ┌────────────▼───────────┐ ┌────────▼──────────────────┐
          │   INGESTION PIPELINE   │ │       AI ENGINE           │
          │      ingest.py         │ │      predict.py           │
          │                        │ │                           │
          │  ▸ snake_case keys     │ │  Stage A — scipy          │
          │  ▸ type coercion       │ │    linregress             │
          │  ▸ tier canonicalise   │ │    slope · R² · CI        │
          │  ▸ field validation    │ │                           │
          │  ▸ UUID + timestamp    │ │  Stage B — RandomForest   │
          └────────────┬───────────┘ │    tier · confidence      │
                       │             └────────┬──────────────────┘
                       │                      │
                       └──────────┬───────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────┐
│                  DATA WAREHOUSE   ·   store.py                   │
│                                                                  │
│   SQLite · Table: customer_telemetry                             │
│   PK: customer_id  ·  SK: timestamp (ISO-8601)                   │
│   Schema mirrors AWS DynamoDB — swap boto3 for cloud deploy      │
└──────────────────────────────────────────────────────────────────┘

  Cross-cutting concerns
  ─────────────────────
  ✦ Input validation & sanitisation        ✦ Idempotent writes
  ✦ Full pipeline audit logging            ✦ GitHub Actions CI/CD
  ✦ One-click Render / Railway deploy      ✦ 11 integration tests
```

---

## Features

###  Data Ingestion API
- `POST /ingest` accepts any semi-structured JSON payload
- Auto-normalises field names from `CamelCase` → `snake_case`
- Canonicalises energy tier labels — `med`, `medium`, `MEDIUM` all map correctly
- Idempotent writes — safe to replay events without duplicates
- Returns structured JSON with `record_id` and `timestamp`

###  Two-Stage AI Prediction Engine

| Stage | Library | What it produces |
|-------|---------|-----------------|
| **A — Trend Model** | `scipy.stats.linregress` | slope, R², p-value, 95% confidence interval |
| **B — Tier Classifier** | `sklearn.RandomForestClassifier` | LOW / MEDIUM / HIGH / CRITICAL + confidence score |

- Trained per-customer on historical kWh, device count, temperature, and season
- Falls back to a deterministic threshold classifier when fewer than 4 records exist
- Generates plain-English recommendations per customer

###  Interactive Real-Time Dashboard
- KPI strip — total records, customers, at-risk count, newly ingested
- Fleet bar chart with tier colour-coding
- Per-customer prediction cards with trend stats, model metadata, and recommendations
- Live ingestion form with instant validation feedback
- Filterable records browser

###  Data Warehouse
- SQLite with a schema identical to AWS DynamoDB's partition/sort key model
- Drop-in swap: replace `store.py` with `boto3` to move to real AWS — zero app changes
- Full pipeline event log for auditability

---

##  Repository Structure

```
intelligent-energy-analytics-poc/
│
├── src/
│   ├── __init__.py
│   ├── app.py            # Flask REST API + real-time dashboard UI
│   ├── ingest.py         # Validation, cleaning & normalisation layer
│   ├── predict.py        # AI engine — linregress + RandomForest
│   └── store.py          # SQLite data warehouse (DynamoDB-compatible)
│
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py  # 11 integration tests
│
├── docs/
│   └── architecture.svg  # Architecture diagram
│
├── .github/
│   └── workflows/
│       └── ci.yml        # GitHub Actions — runs tests on every push
│
├── requirements.txt      # Python dependencies
├── Procfile              # Render / Railway / Heroku process file
├── render.yaml           # One-click Render deploy configuration
├── runtime.txt           # Python 3.11 pin
└── README.md
```

---

##  Quickstart — Run Locally

### Prerequisites
- Python 3.11+
- pip

```bash
# 1. Clone
git clone https://github.com/Cloud-Architect-Emma/intelligent-energy-analytics-poc.git
cd intelligent-energy-analytics-poc

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Run
python -m src.app
```

Open **http://localhost:7860** — the dashboard loads instantly with 18 seeded sample records.

---

##  API Reference

**Base URL:** `http://localhost:7860` (local) · `https://intelligent-energy-analytics-poc.onrender.com` (production)

---

### `GET /health`
Returns server status and record count.

```bash
curl http://localhost:7860/health
```

```json
{
  "status": "ok",
  "records": 18,
  "timestamp": "2024-07-15T10:23:41+00:00"
}
```

---

### `POST /ingest`
Ingest a customer telemetry record.

```bash
curl -X POST http://localhost:7860/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id":       "CUST-042",
    "energy_kwh":        487.3,
    "period_month":      "2024-07",
    "energy_tier":       "medium",
    "region":            "West",
    "device_count":      6,
    "temperature_avg_c": 18.5,
    "notes":             "Summer AC spike"
  }'
```

**201 Created**
```json
{
  "message":      "Record ingested successfully.",
  "record_id":    "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "customer_id":  "CUST-042",
  "period_month": "2024-07",
  "timestamp":    "2024-07-15T10:23:41+00:00"
}
```

**Field reference**

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `customer_id` | string | ✅ | Bare integers auto-prefixed with `CUST-` |
| `energy_kwh` | number | ✅ | Must be ≥ 0 |
| `period_month` | string | ✅ | Format: `YYYY-MM` |
| `energy_tier` | string | ❌ | `low` / `medium` / `high` / `critical` |
| `region` | string | ❌ | Stored as uppercase |
| `device_count` | integer | ❌ | Number of connected meters |
| `temperature_avg_c` | number | ❌ | Average temperature °C |
| `notes` | string | ❌ | Max 500 characters |

---

### `POST /predict`
Run the full AI batch engine across all stored records.

```bash
curl -X POST http://localhost:7860/predict \
  -H "Content-Type: application/json" -d '{}'
```

**200 OK**
```json
{
  "report_metadata": {
    "generated_at": "2024-07-15T10:25:00+00:00",
    "total_customers": 3,
    "total_records": 18,
    "model": "scipy.linregress + sklearn.RandomForestClassifier"
  },
  "customer_predictions": [
    {
      "customer_id": "CUST-002",
      "trend_analysis": {
        "slope_kwh_per_month": 48.16,
        "direction": "INCREASING",
        "r_squared": 0.9978
      },
      "prediction": {
        "predicted_kwh": 961.19,
        "predicted_tier": "CRITICAL",
        "confidence": 0.98,
        "method": "RANDOM_FOREST"
      },
      "recommendation": "Urgent: CUST-002 predicted CRITICAL tier. Immediate outreach required."
    }
  ],
  "fleet_summary": {
    "customers_at_risk": ["CUST-002"],
    "customers_declining": ["CUST-003"]
  }
}
```

---

### `GET /records`

```bash
curl http://localhost:7860/records
curl "http://localhost:7860/records?customer_id=CUST-001"
```

### `GET /customers`

```bash
curl http://localhost:7860/customers
```

---

##  Deployment

### Option 1 — Render.com *(recommended — free)*

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Go to [render.com](https://render.com) → sign in with GitHub
2. **New** → **Web Service** → connect this repo
3. Render auto-detects `render.yaml` — click **Deploy**
4. Live at `https://intelligent-energy-analytics-poc.onrender.com`

> Free tier spins down after 15 min idle. Cold start takes ~30 seconds.

---

### Option 2 — Railway.app

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

---

### Option 3 — Local + public URL via ngrok

```bash
# Terminal 1
python -m src.app

# Terminal 2
ngrok http 7860
```

---

##  Running Tests

```bash
pip install pytest
pytest tests/ -v
```

```
tests/test_pipeline.py::TestIngest::test_valid_payload            PASSED
tests/test_pipeline.py::TestIngest::test_bare_integer_prefixed    PASSED
tests/test_pipeline.py::TestIngest::test_missing_field_raises     PASSED
tests/test_pipeline.py::TestIngest::test_negative_kwh_raises      PASSED
tests/test_pipeline.py::TestIngest::test_bad_period_raises        PASSED
tests/test_pipeline.py::TestIngest::test_tier_normalisation       PASSED
tests/test_pipeline.py::TestPredict::test_kwh_to_tier             PASSED
tests/test_pipeline.py::TestPredict::test_increasing_trend        PASSED
tests/test_pipeline.py::TestPredict::test_decreasing_trend        PASSED
tests/test_pipeline.py::TestPredict::test_batch_pipeline          PASSED
tests/test_pipeline.py::TestPredict::test_prediction_keys         PASSED

11 passed in 3.14s
```

---

##  Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| SQLite over PostgreSQL | Zero infrastructure, instant setup | Not for high-concurrency production writes |
| scipy linregress | Interpretable, fast, no training data needed | Assumes linear growth pattern |
| RandomForest over deep learning | Millisecond training, no GPU required | Lower ceiling accuracy on very large datasets |
| Rule-based fallback | Works from day one with < 4 records | Ignores trend and seasonal signals |
| Flask over FastAPI | Simpler, fewer dependencies | No native async support |
| DynamoDB-compatible schema | Swap to real AWS with zero app changes | Slightly denormalised structure |

---

##  Extending the Project

**Swap SQLite for AWS DynamoDB**
```python
# store.py — drop-in production replacement
import boto3
table = boto3.resource('dynamodb').Table('CustomerTelemetryData')
```

**Add API key authentication**
```python
from functools import wraps
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.headers.get('X-API-Key') != os.environ['API_KEY']:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated
```

**Add seasonality-aware forecasting**
```python
from prophet import Prophet
model = Prophet(yearly_seasonality=True)
model.fit(df)
forecast = model.predict(model.make_future_dataframe(periods=1, freq='MS'))
```

---

##  Tech Stack

| Layer | Technology | Version |
|-------|-----------|:-------:|
| Web framework | Flask | 3.0 |
| Trend model | scipy.stats | 1.12 |
| Tier classifier | scikit-learn | 1.4 |
| Numerical computing | NumPy | 1.26 |
| Data store | SQLite (stdlib) | — |
| Production server | Gunicorn | 21.2 |
| CI / CD | GitHub Actions | — |
| Deployment | Render / Railway | — |
| Language | Python | 3.11 |

---

##  Licence

Distributed under the MIT Licence. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

**Built by [Cloud-Architect-Emma](https://github.com/Cloud-Architect-Emma)**

*Production-grade proof of concept demonstrating data engineering,*
*REST API design, ML pipeline best practices, and cloud-native deployment.*

<br/>

⭐ Star this repo if you found it useful!

</div>
