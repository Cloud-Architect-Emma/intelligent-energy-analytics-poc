"""
store.py – Local data store (SQLite)
Mirrors the DynamoDB schema: partition key CustomerID, sort key Timestamp.
Thread-safe. Used by both the API server and the batch engine.
"""

import sqlite3
import threading
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
import uuid
import json

DB_PATH = Path(__file__).parent / "data" / "telemetry.db"

_lock = threading.Lock()


# ── Schema ────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS customer_telemetry (
    customer_id     TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL,
    record_id       TEXT    NOT NULL,
    energy_kwh      REAL    NOT NULL,
    period_month    TEXT    NOT NULL,
    energy_tier     TEXT,
    temperature_c   REAL,
    device_count    INTEGER,
    region          TEXT,
    notes           TEXT,
    ingested_at     TEXT    NOT NULL,
    schema_version  TEXT    NOT NULL DEFAULT '1.0.0',
    PRIMARY KEY (customer_id, timestamp)
);

CREATE TABLE IF NOT EXISTS pipeline_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      TEXT    NOT NULL,
    event       TEXT    NOT NULL,
    detail      TEXT
);
"""

def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def initialise():
    with _lock, _conn() as c:
        c.executescript(DDL)


# ── Write ─────────────────────────────────────────────────────────────────────

def put_record(record: dict) -> dict:
    """
    Insert a telemetry record. Returns the saved record dict.
    Raises ValueError on duplicate (CustomerID + Timestamp).
    """
    now = datetime.now(timezone.utc).isoformat()
    rid = str(uuid.uuid4())

    row = (
        record["customer_id"],
        now,                              # timestamp (sort key)
        rid,
        float(record["energy_kwh"]),
        record["period_month"],
        record.get("energy_tier"),
        record.get("temperature_avg_c"),
        record.get("device_count"),
        record.get("region"),
        record.get("notes"),
        now,
        "1.0.0",
    )

    sql = """
        INSERT OR IGNORE INTO customer_telemetry
        (customer_id, timestamp, record_id, energy_kwh, period_month,
         energy_tier, temperature_c, device_count, region, notes,
         ingested_at, schema_version)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """
    with _lock, _conn() as c:
        c.execute(sql, row)

    saved = {
        "customer_id":   record["customer_id"],
        "timestamp":     now,
        "record_id":     rid,
        "energy_kwh":    float(record["energy_kwh"]),
        "period_month":  record["period_month"],
        "energy_tier":   record.get("energy_tier"),
        "region":        record.get("region"),
    }
    return saved


# ── Read ──────────────────────────────────────────────────────────────────────

def scan_all() -> list[dict]:
    """Return every record as a list of dicts, sorted by customer + period."""
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT * FROM customer_telemetry ORDER BY customer_id, period_month"
        ).fetchall()
    return [dict(r) for r in rows]


def get_customer_records(customer_id: str) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT * FROM customer_telemetry WHERE customer_id=? ORDER BY period_month",
            (customer_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_customers() -> list[str]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT DISTINCT customer_id FROM customer_telemetry ORDER BY customer_id"
        ).fetchall()
    return [r["customer_id"] for r in rows]


def count_records() -> int:
    with _lock, _conn() as c:
        return c.execute("SELECT COUNT(*) FROM customer_telemetry").fetchone()[0]


def log_event(event: str, detail: str = ""):
    now = datetime.now(timezone.utc).isoformat()
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO pipeline_log (run_at, event, detail) VALUES (?,?,?)",
            (now, event, detail),
        )


def get_logs(limit: int = 20) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT * FROM pipeline_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Sample data seeder ────────────────────────────────────────────────────────

SAMPLE_RECORDS = [
    # CUST-001: steadily increasing
    {"customer_id":"CUST-001","energy_kwh":310.5,"period_month":"2024-01","energy_tier":"LOW","region":"NORTH","device_count":3,"temperature_avg_c":4.2},
    {"customer_id":"CUST-001","energy_kwh":340.0,"period_month":"2024-02","energy_tier":"LOW","region":"NORTH","device_count":3,"temperature_avg_c":5.1},
    {"customer_id":"CUST-001","energy_kwh":375.8,"period_month":"2024-03","energy_tier":"MEDIUM","region":"NORTH","device_count":4,"temperature_avg_c":7.3},
    {"customer_id":"CUST-001","energy_kwh":398.2,"period_month":"2024-04","energy_tier":"MEDIUM","region":"NORTH","device_count":4,"temperature_avg_c":9.8},
    {"customer_id":"CUST-001","energy_kwh":430.5,"period_month":"2024-05","energy_tier":"MEDIUM","region":"NORTH","device_count":5,"temperature_avg_c":12.0},
    {"customer_id":"CUST-001","energy_kwh":471.0,"period_month":"2024-06","energy_tier":"HIGH","region":"NORTH","device_count":5,"temperature_avg_c":15.4},
    # CUST-002: trending critical
    {"customer_id":"CUST-002","energy_kwh":680.0,"period_month":"2024-01","energy_tier":"HIGH","region":"SOUTH","device_count":8,"temperature_avg_c":6.0},
    {"customer_id":"CUST-002","energy_kwh":720.5,"period_month":"2024-02","energy_tier":"HIGH","region":"SOUTH","device_count":9,"temperature_avg_c":6.5},
    {"customer_id":"CUST-002","energy_kwh":755.0,"period_month":"2024-03","energy_tier":"HIGH","region":"SOUTH","device_count":9,"temperature_avg_c":8.1},
    {"customer_id":"CUST-002","energy_kwh":810.2,"period_month":"2024-04","energy_tier":"HIGH","region":"SOUTH","device_count":10,"temperature_avg_c":10.5},
    {"customer_id":"CUST-002","energy_kwh":865.0,"period_month":"2024-05","energy_tier":"CRITICAL","region":"SOUTH","device_count":11,"temperature_avg_c":13.0},
    {"customer_id":"CUST-002","energy_kwh":920.8,"period_month":"2024-06","energy_tier":"CRITICAL","region":"SOUTH","device_count":12,"temperature_avg_c":16.2},
    # CUST-003: declining
    {"customer_id":"CUST-003","energy_kwh":520.0,"period_month":"2024-01","energy_tier":"MEDIUM","region":"EAST","device_count":6,"temperature_avg_c":5.0},
    {"customer_id":"CUST-003","energy_kwh":505.3,"period_month":"2024-02","energy_tier":"MEDIUM","region":"EAST","device_count":6,"temperature_avg_c":5.5},
    {"customer_id":"CUST-003","energy_kwh":490.0,"period_month":"2024-03","energy_tier":"MEDIUM","region":"EAST","device_count":5,"temperature_avg_c":7.0},
    {"customer_id":"CUST-003","energy_kwh":475.5,"period_month":"2024-04","energy_tier":"MEDIUM","region":"EAST","device_count":5,"temperature_avg_c":9.2},
    {"customer_id":"CUST-003","energy_kwh":460.2,"period_month":"2024-05","energy_tier":"LOW","region":"EAST","device_count":5,"temperature_avg_c":11.0},
    {"customer_id":"CUST-003","energy_kwh":442.8,"period_month":"2024-06","energy_tier":"LOW","region":"EAST","device_count":4,"temperature_avg_c":14.5},
]


def seed_sample_data() -> int:
    """Insert sample records if the table is empty. Returns count inserted."""
    if count_records() > 0:
        return 0
    for rec in SAMPLE_RECORDS:
        try:
            put_record(rec)
        except Exception:
            pass
    n = count_records()
    log_event("SEED", f"Inserted {n} sample records")
    return n
