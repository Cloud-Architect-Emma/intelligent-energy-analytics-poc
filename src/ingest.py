"""
ingest.py – Data validation and cleaning layer (mirrors lambda_ingest.py logic)
"""
import re, uuid, math
from datetime import datetime, timezone
from decimal import Decimal

VALID_TIERS = {"low":"LOW","medium":"MEDIUM","med":"MEDIUM","high":"HIGH","hi":"HIGH","critical":"CRITICAL","crit":"CRITICAL"}
REQUIRED    = ["customer_id","energy_kwh","period_month"]

def _snake(text):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(text))
    return re.sub(r"[\s\-]+","_",s).lower()

def normalise_keys(raw):
    return {_snake(k): v for k, v in raw.items()}

def validate_and_clean(raw: dict) -> dict:
    data = normalise_keys(raw)
    missing = [f for f in REQUIRED if f not in data or data[f] in (None,"")]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    cid = str(data["customer_id"]).strip()
    if cid.isdigit():
        cid = f"CUST-{cid}"

    try:
        kwh = float(data["energy_kwh"])
    except (TypeError, ValueError):
        raise ValueError(f"energy_kwh must be numeric, got: {data['energy_kwh']!r}")
    if kwh < 0:
        raise ValueError(f"energy_kwh must be >= 0, got: {kwh}")

    pm = str(data["period_month"]).strip()
    try:
        datetime.strptime(pm, "%Y-%m")
    except ValueError:
        raise ValueError(f"period_month must be YYYY-MM, got: {pm!r}")

    tier = None
    if data.get("energy_tier"):
        tier = VALID_TIERS.get(str(data["energy_tier"]).strip().lower(), str(data["energy_tier"]).upper())

    temp = None
    if data.get("temperature_avg_c") is not None:
        try: temp = float(data["temperature_avg_c"])
        except: pass

    dc = None
    if data.get("device_count") is not None:
        try: dc = int(data["device_count"])
        except: pass

    region = str(data["region"]).strip().upper() if data.get("region") else None
    notes  = str(data["notes"]).strip()[:500]    if data.get("notes")   else None

    return {
        "customer_id":      cid,
        "energy_kwh":       kwh,
        "period_month":     pm,
        "energy_tier":      tier,
        "temperature_avg_c": temp,
        "device_count":     dc,
        "region":           region,
        "notes":            notes,
    }
