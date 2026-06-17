# Intelligent Energy Analytics POC

A production-grade data ingestion and AI-powered predictive analytics platform built entirely with free, open-source tools.

[![CI](https://github.com/Cloud-Architect-Emma/intelligent-energy-analytics-poc/actions/workflows/ci.yml/badge.svg)](https://github.com/Cloud-Architect-Emma/intelligent-energy-analytics-poc/actions)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Overview

End-to-end data engineering and ML pipeline for customer energy telemetry.

- Ingest semi-structured telemetry from multiple source systems
- Clean and validate data through a typed processing layer
- Store records in a structured SQLite data warehouse
- Predict next-month energy usage tiers using a two-stage AI model
- Surface insights through an interactive real-time dashboard

---

## Architecture
ENTRY POINTS

HTTP Clients / Dashboard UI / Batch Runner

|

FLASK REST API (app.py)

POST /ingest | POST /predict | GET /records | GET /health

|                          |

INGESTION PIPELINE           AI ENGINE

(ingest.py)                  (predict.py)

snake_case keys            Stage A: scipy linregress
type coercion              Stage B: sklearn RandomForest
field validation           tier + confidence score

|                          |

+----------+---------------+

|

DATA WAREHOUSE (store.py - SQLite)

PK: customer_id  SK: timestamp

Schema mirrors AWS DynamoDB


---

## Features

### Data Ingestion API
- POST /ingest accepts flexible semi-structured JSON
- Normalises CamelCase keys to snake_case
- Canonicalises tiers: med to MEDIUM, crit to CRITICAL
- Idempotent writes with UUID record IDs

### AI Prediction Engine

| Stage | Library | Output |
|-------|---------|--------|
| A Trend Model | scipy.stats.linregress | slope, R2, 95% CI |
| B Tier Classifier | sklearn RandomForestClassifier | LOW / MEDIUM / HIGH / CRITICAL |

### Interactive Dashboard
- KPI cards, fleet bar chart, per-customer trend cards
- Live ingestion form and filterable records browser

---

## Repository Structure
intelligent-energy-analytics-poc/

|-- src/

|   |-- app.py        # Flask REST API + dashboard

|   |-- ingest.py     # Validation and cleaning

|   |-- predict.py    # AI engine

|   +-- store.py      # SQLite warehouse

|-- tests/

|   +-- test_pipeline.py

|-- docs/

|   +-- architecture.svg

|-- .github/workflows/ci.yml

|-- render.yaml

|-- requirements.txt

+-- Procfile

---

## Quickstart

```bash
git clone https://github.com/Cloud-Architect-Emma/intelligent-energy-analytics-poc.git
cd intelligent-energy-analytics-poc
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.app
```

Open http://localhost:7860

---

## API Reference

### GET /health
```bash
curl http://localhost:7860/health
```

### POST /ingest
```bash
curl -X POST http://localhost:7860/ingest \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"CUST-042\",\"energy_kwh\":487.3,\"period_month\":\"2024-07\"}"
```

| Field | Required | Notes |
|-------|----------|-------|
| customer_id | YES | integers prefixed with CUST- |
| energy_kwh | YES | must be >= 0 |
| period_month | YES | YYYY-MM format |
| energy_tier | NO | low / medium / high / critical |
| region | NO | stored uppercase |
| device_count | NO | integer |
| temperature_avg_c | NO | float |

### POST /predict
```bash
curl -X POST http://localhost:7860/predict -H "Content-Type: application/json" -d "{}"
```

### GET /records
```bash
curl http://localhost:7860/records
curl "http://localhost:7860/records?customer_id=CUST-001"
```

---

## Deployment

### Render.com (free)
1. Go to render.com and sign in with GitHub
2. New > Web Service > select this repo
3. Render detects render.yaml automatically
4. Deploy - live at https://intelligent-energy-analytics-poc.onrender.com

### Railway
```bash
npm install -g @railway/cli
railway login && railway init && railway up
```

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

11 tests, all passing.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Web framework | Flask | 3.0 |
| Trend model | scipy.stats | 1.12 |
| Tier classifier | scikit-learn | 1.4 |
| Numerical | NumPy | 1.26 |
| Data store | SQLite | stdlib |
| Server | Gunicorn | 21.2 |
| CI/CD | GitHub Actions | - |
| Language | Python | 3.11 |

---

## License

MIT

---

Built by [Cloud-Architect-Emma](https://github.com/Cloud-Architect-Emma)
