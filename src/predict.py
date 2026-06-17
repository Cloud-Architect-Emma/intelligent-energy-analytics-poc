"""
predict.py – Two-stage AI prediction engine
Stage A: scipy.stats.linregress  (trend model)
Stage B: sklearn RandomForestClassifier  (tier prediction)
Mirrors ai_batch_predict.py logic, callable as a module.
"""
import math
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from scipy import stats as sp
from sklearn.ensemble import RandomForestClassifier

TIER_THRESHOLDS = {"LOW":(0,400),"MEDIUM":(400,600),"HIGH":(600,900),"CRITICAL":(900,1e9)}
MIN_ML = 4

def _kwh_to_tier(kwh):
    for t,(lo,hi) in TIER_THRESHOLDS.items():
        if lo <= kwh < hi: return t
    return "CRITICAL"

def _season(month):
    return {12:0,1:0,2:0,3:1,4:1,5:1,6:2,7:2,8:2}.get(month,3)

def _trend(kwh_list):
    x = list(range(len(kwh_list)))
    y = kwh_list
    n = len(y)
    if n < 2:
        avg = y[0] if y else 0
        return {"slope":0,"r2":0,"pval":1,"direction":"STABLE",
                "predicted":avg,"lower":avg*0.9,"upper":avg*1.1}
    res   = sp.linregress(x, y)
    slope = float(res.slope); intercept = float(res.intercept)
    r2    = float(res.rvalue**2); pval = float(res.pvalue)
    nx    = n
    pred  = slope*nx + intercept
    tcrit = float(sp.t.ppf(0.975, max(n-2,1)))
    xbar  = sum(x)/n
    sx2   = sum((xi-xbar)**2 for xi in x) or 1
    se    = float(res.stderr) * math.sqrt(1+1/n+(nx-xbar)**2/sx2)
    margin = tcrit * se
    avg = sum(y)/n
    thr = avg*0.02
    direction = "INCREASING" if slope>thr else ("DECREASING" if slope<-thr else "STABLE")
    return {"slope":round(slope,3),"r2":round(r2,4),"pval":round(pval,6),
            "direction":direction,"predicted":round(max(pred,0),2),
            "lower":round(max(pred-margin,0),2),"upper":round(pred+margin,2)}

def _classify(kwh_list, months, devices, temps, trend):
    n = len(kwh_list)
    pred_kwh = trend["predicted"]
    if n < MIN_ML:
        tier = _kwh_to_tier(pred_kwh)
        lo,hi = TIER_THRESHOLDS[tier]
        w = (hi-lo) if hi<1e8 else 400
        conf = round(0.5+0.5*min(abs(pred_kwh-(lo+w/2))/(w/2),1),3)
        return {"tier":tier,"confidence":conf,"method":"RULE_BASED"}

    avg_dc  = sum(d for d in devices if d) / max(1,sum(1 for d in devices if d))
    avg_tmp = sum(t for t in temps  if t) / max(1,sum(1 for t in temps  if t))

    X,y = [],[]
    for i,kwh in enumerate(kwh_list):
        m  = months[i]  if i<len(months)  else 6
        dc = devices[i] if (i<len(devices) and devices[i]) else avg_dc
        tp = temps[i]   if (i<len(temps)   and temps[i])   else avg_tmp
        X.append([kwh, trend["slope"], float(dc), float(tp), float(_season(m)), float(i)])
        y.append(_kwh_to_tier(kwh))

    clf = RandomForestClassifier(n_estimators=50,max_depth=5,random_state=42,class_weight="balanced")
    clf.fit(np.array(X), y)

    nm  = (months[-1]%12)+1 if months else 7
    ndc = devices[-1] if (devices and devices[-1]) else avg_dc
    ntp = (temps[-1]+trend["slope"]*0.1) if (temps and temps[-1]) else avg_tmp
    Xp  = np.array([[pred_kwh, trend["slope"], float(ndc), float(ntp), float(_season(nm)), float(n)]])
    tier = clf.predict(Xp)[0]
    proba = dict(zip(clf.classes_, clf.predict_proba(Xp)[0]))
    return {"tier":tier,"confidence":round(float(proba.get(tier,0.5)),3),"method":"RANDOM_FOREST"}

def _recommend(cid, trend, pred):
    tier = pred["tier"]; d = trend["direction"]; s = trend["slope"]; c = pred["confidence"]
    msg  = {"CRITICAL":f"🚨 URGENT: {cid} predicted CRITICAL tier (>900 kWh). Immediate outreach required.",
            "HIGH":    f"⚠️  ATTENTION: {cid} predicted HIGH tier. Efficiency consultation recommended.",
            "MEDIUM":  f"✅ {cid} stable in MEDIUM tier. Continue standard monitoring.",
            "LOW":     f"💡 {cid} LOW usage – strong candidate for renewable energy upsell."}[tier]
    trend_msg = (f" Usage trending UP +{s:.1f} kWh/month." if d=="INCREASING"
                 else f" Usage trending DOWN {s:.1f} kWh/month – efficiency improving."
                 if d=="DECREASING" else " Usage is stable.")
    conf_msg = f" (Confidence: {c:.0%})" + (" – limited history, ingest more data for accuracy." if c<0.65 else ".")
    return msg + trend_msg + conf_msg

def analyse_customer(customer_id, records):
    """Full pipeline for one customer. records = list of dicts from store."""
    records = sorted(records, key=lambda r: r.get("period_month",""))
    kwh   = [float(r["energy_kwh"]) for r in records if r.get("energy_kwh") is not None]
    if not kwh:
        return None
    tiers   = [r.get("energy_tier","MEDIUM") or "MEDIUM" for r in records]
    devices = [r.get("device_count") for r in records]
    temps   = [r.get("temperature_c") or r.get("temperature_avg_c") for r in records]
    months  = []
    for r in records:
        pm = r.get("period_month","2024-01")
        try: months.append(int(pm.split("-")[1]))
        except: months.append(6)
    periods = [r.get("period_month","") for r in records if r.get("period_month")]
    avg = sum(kwh)/len(kwh)
    trend = _trend(kwh)
    pred  = _classify(kwh, months, devices, temps, trend)
    rec   = _recommend(customer_id, trend, pred)
    return {
        "customer_id": customer_id,
        "record_count": len(records),
        "date_range": {"first": periods[0] if periods else "?", "last": periods[-1] if periods else "?"},
        "historical_summary": {
            "avg_kwh":  round(avg,2),
            "min_kwh":  round(min(kwh),2),
            "max_kwh":  round(max(kwh),2),
            "std_kwh":  round(math.sqrt(sum((v-avg)**2 for v in kwh)/len(kwh)),2),
            "most_common_tier": Counter(tiers).most_common(1)[0][0],
        },
        "trend_analysis": {
            "slope_kwh_per_month": trend["slope"],
            "direction":           trend["direction"],
            "r_squared":           trend["r2"],
            "p_value":             trend["pval"],
        },
        "prediction": {
            "predicted_kwh":   trend["predicted"],
            "kwh_lower_bound": trend["lower"],
            "kwh_upper_bound": trend["upper"],
            "predicted_tier":  pred["tier"],
            "confidence":      pred["confidence"],
            "method":          pred["method"],
        },
        "recommendation": rec,
    }

def run_batch(records):
    """Run the full fleet analysis. records = all rows from store.scan_all()."""
    from collections import defaultdict
    groups = defaultdict(list)
    for r in records:
        groups[r["customer_id"]].append(r)
    predictions = []
    for cid, recs in sorted(groups.items()):
        result = analyse_customer(cid, recs)
        if result:
            predictions.append(result)
    tier_dist = Counter(p["prediction"]["predicted_tier"] for p in predictions)
    at_risk   = [p["customer_id"] for p in predictions if p["prediction"]["predicted_tier"] in ("HIGH","CRITICAL")]
    declining = [p["customer_id"] for p in predictions if p["trend_analysis"]["direction"]=="DECREASING"]
    return {
        "report_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_customers": len(predictions),
            "total_records":   len(records),
            "model": "scipy.linregress + sklearn.RandomForestClassifier",
        },
        "customer_predictions": predictions,
        "fleet_summary": {
            "tier_distribution":  dict(tier_dist),
            "customers_at_risk":  at_risk,
            "customers_declining": declining,
        },
    }
