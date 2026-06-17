"""
app.py – Intelligent Data Aggregation & Predictive Analytics Engine
Live Flask server: REST API + full dashboard UI
"""
import json, sys, os
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string

try:
    from src import store, ingest, predict
except ImportError:
    import store, ingest, predict

app = Flask(__name__)
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ── Initialise DB + seed on startup ──────────────────────────────────────────
store.initialise()
seeded = store.seed_sample_data()
if seeded:
    store.log_event("STARTUP", f"Seeded {seeded} sample records")

# =============================================================================
# REST API
# =============================================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"ok","records":store.count_records(),
                    "timestamp":datetime.now(timezone.utc).isoformat()})

@app.route("/ingest", methods=["POST"])
def ingest_record():
    """POST /ingest – validate, clean, store a telemetry record."""
    raw = request.get_json(silent=True)
    if not raw:
        return jsonify({"error":"Bad Request","detail":"Body must be valid JSON"}), 400
    try:
        cleaned = ingest.validate_and_clean(raw)
    except ValueError as e:
        return jsonify({"error":"Validation Failed","detail":str(e)}), 400
    saved = store.put_record(cleaned)
    store.log_event("INGEST", f"CustomerID={saved['customer_id']} Period={saved['period_month']}")
    return jsonify({"message":"Record ingested successfully.",
                    "record_id":saved["record_id"],
                    "customer_id":saved["customer_id"],
                    "timestamp":saved["timestamp"]}), 201

@app.route("/predict", methods=["POST"])
def run_predictions():
    """POST /predict – run the AI batch engine on all stored data."""
    records = store.scan_all()
    if not records:
        return jsonify({"error":"No data","detail":"Ingest some records first."}), 404
    report = predict.run_batch(records)
    ts  = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out = REPORTS_DIR / f"report_{ts}.json"
    out.write_text(json.dumps(report, indent=2))
    store.log_event("PREDICT", f"{report['report_metadata']['total_customers']} customers analysed → {out.name}")
    return jsonify(report), 200

@app.route("/records", methods=["GET"])
def list_records():
    cid = request.args.get("customer_id")
    rows = store.get_customer_records(cid) if cid else store.scan_all()
    return jsonify({"count":len(rows),"records":rows})

@app.route("/customers", methods=["GET"])
def list_customers():
    return jsonify({"customers": store.list_customers()})

@app.route("/logs", methods=["GET"])
def get_logs():
    return jsonify({"logs": store.get_logs(50)})

# =============================================================================
# Dashboard UI
# =============================================================================

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>⚡ Intelligent Energy Analytics POC</title>
<style>
  :root{--bg:#0f172a;--surf:#1e293b;--surf2:#263548;--border:#334155;
    --indigo:#6366f1;--violet:#8b5cf6;--cyan:#06b6d4;--green:#10b981;
    --amber:#f59e0b;--red:#ef4444;--text:#f1f5f9;--muted:#94a3b8;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
  header{background:linear-gradient(135deg,#1e1b4b,#1e293b);border-bottom:1px solid var(--border);
    padding:1.2rem 2rem;display:flex;align-items:center;gap:1rem;}
  header h1{font-size:1.5rem;font-weight:700;background:linear-gradient(90deg,var(--indigo),var(--cyan));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
  header .badge{font-size:.7rem;padding:.2rem .6rem;border-radius:999px;
    background:rgba(99,102,241,.2);color:var(--indigo);border:1px solid var(--indigo);font-weight:600;}
  .layout{display:grid;grid-template-columns:260px 1fr;min-height:calc(100vh - 64px);}
  nav{background:var(--surf);border-right:1px solid var(--border);padding:1.5rem 1rem;}
  nav button{width:100%;text-align:left;background:none;border:none;color:var(--muted);
    padding:.7rem 1rem;border-radius:8px;cursor:pointer;font-size:.9rem;margin-bottom:.3rem;
    display:flex;align-items:center;gap:.7rem;transition:all .15s;}
  nav button:hover,nav button.active{background:rgba(99,102,241,.15);color:var(--text);}
  nav button.active{border-left:3px solid var(--indigo);}
  main{padding:2rem;overflow-y:auto;}
  .page{display:none;} .page.active{display:block;}
  .kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem;margin-bottom:2rem;}
  .kpi{background:var(--surf);border:1px solid var(--border);border-radius:12px;padding:1.2rem;
    border-left:4px solid var(--indigo);}
  .kpi .val{font-size:1.9rem;font-weight:700;color:var(--text);}
  .kpi .lbl{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-top:.3rem;}
  .card{background:var(--surf);border:1px solid var(--border);border-radius:12px;padding:1.5rem;margin-bottom:1.5rem;}
  .card h3{font-size:1rem;font-weight:600;color:var(--cyan);margin-bottom:1rem;display:flex;align-items:center;gap:.5rem;}
  .section-title{font-size:1.1rem;font-weight:700;color:var(--muted);text-transform:uppercase;
    letter-spacing:.08em;margin:1.5rem 0 1rem;border-bottom:1px solid var(--border);padding-bottom:.5rem;}
  textarea,input,select{background:var(--surf2);border:1px solid var(--border);color:var(--text);
    border-radius:8px;padding:.7rem 1rem;font-size:.9rem;font-family:inherit;width:100%;}
  textarea:focus,input:focus{outline:none;border-color:var(--indigo);}
  .btn{display:inline-flex;align-items:center;gap:.5rem;padding:.65rem 1.4rem;border-radius:8px;
    font-weight:600;font-size:.9rem;cursor:pointer;border:none;transition:opacity .15s;}
  .btn:hover{opacity:.85;} .btn:disabled{opacity:.4;cursor:not-allowed;}
  .btn-primary{background:linear-gradient(135deg,var(--indigo),var(--violet));color:#fff;}
  .btn-success{background:linear-gradient(135deg,var(--green),#059669);color:#fff;}
  .btn-amber{background:linear-gradient(135deg,var(--amber),#d97706);color:#fff;}
  .btn-sm{padding:.4rem .9rem;font-size:.8rem;}
  .response-box{background:#0d1117;border:1px solid var(--border);border-radius:8px;padding:1rem;
    font-family:'Fira Code',monospace;font-size:.78rem;color:#a5f3fc;max-height:420px;
    overflow-y:auto;white-space:pre-wrap;line-height:1.6;}
  .status-bar{display:flex;align-items:center;gap:.5rem;padding:.5rem 1rem;border-radius:6px;
    font-size:.82rem;margin-bottom:1rem;}
  .status-bar.ok{background:rgba(16,185,129,.1);border:1px solid var(--green);color:var(--green);}
  .status-bar.err{background:rgba(239,68,68,.1);border:1px solid var(--red);color:var(--red);}
  .status-bar.info{background:rgba(99,102,241,.1);border:1px solid var(--indigo);color:var(--indigo);}
  table{width:100%;border-collapse:collapse;font-size:.85rem;}
  th{text-align:left;padding:.6rem 1rem;background:var(--surf2);color:var(--muted);
    font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;}
  td{padding:.65rem 1rem;border-bottom:1px solid var(--border);vertical-align:middle;}
  tr:hover td{background:rgba(255,255,255,.02);}
  .tier-chip{display:inline-block;padding:.2rem .7rem;border-radius:999px;font-size:.72rem;font-weight:700;}
  .tier-LOW{background:rgba(16,185,129,.15);color:var(--green);}
  .tier-MEDIUM{background:rgba(99,102,241,.15);color:#a5b4fc;}
  .tier-HIGH{background:rgba(245,158,11,.15);color:var(--amber);}
  .tier-CRITICAL{background:rgba(239,68,68,.15);color:var(--red);}
  .dir-INCREASING{color:var(--red);}
  .dir-DECREASING{color:var(--green);}
  .dir-STABLE{color:var(--muted);}
  .progress{height:6px;background:var(--surf2);border-radius:3px;overflow:hidden;margin-top:4px;}
  .progress-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--indigo),var(--cyan));}
  .flex{display:flex;gap:.8rem;align-items:flex-start;flex-wrap:wrap;}
  .alert{padding:.9rem 1.2rem;border-radius:8px;margin-bottom:1rem;font-size:.87rem;}
  .alert-critical{background:rgba(239,68,68,.1);border-left:4px solid var(--red);color:#fca5a5;}
  .alert-warn{background:rgba(245,158,11,.1);border-left:4px solid var(--amber);color:#fcd34d;}
  .chip-sample{background:rgba(6,182,212,.1);color:var(--cyan);font-size:.72rem;
    padding:.15rem .5rem;border-radius:4px;border:1px solid rgba(6,182,212,.3);}
  .spinner{display:inline-block;width:14px;height:14px;border:2px solid transparent;
    border-top-color:currentColor;border-radius:50%;animation:spin .7s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg)}}
  .bar-chart{display:flex;flex-direction:column;gap:.5rem;}
  .bar-row{display:flex;align-items:center;gap:.7rem;font-size:.82rem;}
  .bar-label{width:100px;text-align:right;color:var(--muted);flex-shrink:0;}
  .bar-track{flex:1;background:var(--surf2);border-radius:4px;height:20px;overflow:hidden;position:relative;}
  .bar-fill{height:100%;border-radius:4px;display:flex;align-items:center;padding-left:.5rem;
    font-size:.72rem;font-weight:700;transition:width .6s ease;}
  .bar-val{width:60px;text-align:right;color:var(--text);flex-shrink:0;font-weight:600;}
</style>
</head>
<body>
<header>
  <span style="font-size:1.8rem">⚡</span>
  <h1>Intelligent Energy Analytics POC</h1>
  <span class="badge">LIVE</span>
  <span id="health-dot" style="margin-left:auto;font-size:.8rem;color:var(--muted)">● connecting…</span>
</header>
<div class="layout">
<nav>
  <button class="active" onclick="showPage('overview',this)">🏠 &nbsp;Overview</button>
  <button onclick="showPage('ingest',this)">📡 &nbsp;Ingest Data</button>
  <button onclick="showPage('records',this)">🗄️ &nbsp;Records</button>
  <button onclick="showPage('predict',this)">🤖 &nbsp;AI Predictions</button>
  <button onclick="showPage('logs',this)">📋 &nbsp;Activity Log</button>
  <div style="margin-top:1.5rem;padding:.7rem 1rem;background:rgba(99,102,241,.07);
      border-radius:8px;font-size:.75rem;color:var(--muted)">
    <div style="color:var(--indigo);font-weight:700;margin-bottom:.4rem">API Endpoints</div>
    <div>POST /ingest</div>
    <div>POST /predict</div>
    <div>GET  /records</div>
    <div>GET  /customers</div>
    <div>GET  /health</div>
  </div>
</nav>
<main>

<!-- ═══════════════════════════════ OVERVIEW ═════════════════════════════════ -->
<div id="page-overview" class="page active">
  <div class="section-title">Dashboard</div>
  <div class="kpi-grid">
    <div class="kpi"><div class="val" id="kpi-records">—</div><div class="lbl">📦 Records Stored</div></div>
    <div class="kpi" style="border-left-color:var(--cyan)"><div class="val" id="kpi-customers">—</div><div class="lbl">👥 Customers</div></div>
    <div class="kpi" style="border-left-color:var(--green)"><div class="val" id="kpi-status">—</div><div class="lbl">✅ API Status</div></div>
    <div class="kpi" style="border-left-color:var(--amber)"><div class="val" id="kpi-reports">—</div><div class="lbl">📊 Reports Run</div></div>
  </div>

  <div id="fleet-alerts"></div>

  <div class="card">
    <h3>🏗️ Architecture</h3>
    <pre style="color:var(--muted);font-size:.8rem;line-height:1.9">
  HTTP POST /ingest
       │
       ▼
  Validation & Cleaning Layer  (ingest.py)
  • snake_case normalisation  • type coercion
  • required field checks     • tier canonicalisation
       │
       ▼
  SQLite Data Warehouse  (store.py)  ← mirrors DynamoDB schema
  PK: customer_id   SK: timestamp
       │
       ▼
  AI Batch Engine  (predict.py)
  Stage A: scipy.stats.linregress   → trend slope, R², p-value
  Stage B: sklearn RandomForest     → predicted energy tier
       │
       ▼
  predictive_analysis_report.json  +  Dashboard UI</pre>
  </div>

  <div class="card">
    <h3>📊 Fleet Overview</h3>
    <div id="fleet-chart" class="bar-chart"><div style="color:var(--muted);font-size:.85rem">Run AI Predictions to see fleet data →</div></div>
  </div>
</div>

<!-- ═══════════════════════════════ INGEST ═══════════════════════════════════ -->
<div id="page-ingest" class="page">
  <div class="section-title">Ingest Telemetry Data</div>

  <div class="card">
    <h3>📡 POST /ingest – Send a Payload</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem">
      <div>
        <label style="font-size:.8rem;color:var(--muted);display:block;margin-bottom:.4rem">Customer ID *</label>
        <input id="f-cid" placeholder="e.g. CUST-042" value="CUST-042"/>
      </div>
      <div>
        <label style="font-size:.8rem;color:var(--muted);display:block;margin-bottom:.4rem">Period Month * (YYYY-MM)</label>
        <input id="f-pm" placeholder="2024-07" value="2024-07"/>
      </div>
      <div>
        <label style="font-size:.8rem;color:var(--muted);display:block;margin-bottom:.4rem">Energy kWh *</label>
        <input id="f-kwh" type="number" placeholder="487.3" value="487.3"/>
      </div>
      <div>
        <label style="font-size:.8rem;color:var(--muted);display:block;margin-bottom:.4rem">Energy Tier</label>
        <select id="f-tier">
          <option value="">— optional —</option>
          <option value="low">LOW</option>
          <option value="medium" selected>MEDIUM</option>
          <option value="high">HIGH</option>
          <option value="critical">CRITICAL</option>
        </select>
      </div>
      <div>
        <label style="font-size:.8rem;color:var(--muted);display:block;margin-bottom:.4rem">Region</label>
        <input id="f-region" placeholder="North / South / East / West" value="West"/>
      </div>
      <div>
        <label style="font-size:.8rem;color:var(--muted);display:block;margin-bottom:.4rem">Device Count</label>
        <input id="f-dc" type="number" placeholder="6" value="6"/>
      </div>
      <div>
        <label style="font-size:.8rem;color:var(--muted);display:block;margin-bottom:.4rem">Avg Temperature (°C)</label>
        <input id="f-temp" type="number" placeholder="18.5" value="18.5"/>
      </div>
      <div>
        <label style="font-size:.8rem;color:var(--muted);display:block;margin-bottom:.4rem">Notes</label>
        <input id="f-notes" placeholder="Optional notes…"/>
      </div>
    </div>
    <div class="flex">
      <button class="btn btn-primary" onclick="sendIngest()">📡 Send to /ingest</button>
      <button class="btn btn-amber btn-sm" onclick="randomise()">🎲 Randomise</button>
      <button class="btn btn-sm" style="background:var(--surf2)" onclick="sendRaw()">⌨️ Send Raw JSON</button>
    </div>
  </div>

  <div class="card">
    <h3>⌨️ Raw JSON Payload</h3>
    <textarea id="raw-json" rows="8" placeholder='{"customer_id":"CUST-042","energy_kwh":487.3,"period_month":"2024-07"}'></textarea>
    <div style="margin-top:.8rem" class="flex">
      <button class="btn btn-primary btn-sm" onclick="sendRaw()">📡 Send Raw JSON</button>
      <button class="btn btn-sm" style="background:var(--surf2)" onclick="loadCurlExample()">📋 Load curl example</button>
    </div>
  </div>

  <div class="card">
    <h3>📥 Batch Ingest – Quick Load</h3>
    <p style="font-size:.85rem;color:var(--muted);margin-bottom:1rem">Add 6 more months of history for a customer to power the AI engine.</p>
    <div class="flex">
      <input id="batch-cid" placeholder="Customer ID e.g. CUST-004" style="max-width:220px" value="CUST-004"/>
      <button class="btn btn-success" onclick="batchIngest()">⚡ Ingest 6 months</button>
    </div>
    <div id="batch-status" style="margin-top:.8rem"></div>
  </div>

  <div id="ingest-status"></div>
  <div class="card"><h3>📤 Response</h3><div id="ingest-response" class="response-box">— awaiting request —</div></div>
</div>

<!-- ═══════════════════════════════ RECORDS ═══════════════════════════════════ -->
<div id="page-records" class="page">
  <div class="section-title">Data Warehouse</div>
  <div class="card">
    <h3>🗄️ Records Browser</h3>
    <div class="flex" style="margin-bottom:1rem">
      <input id="filter-cid" placeholder="Filter by Customer ID…" style="max-width:250px"
        oninput="loadRecords()"/>
      <button class="btn btn-primary btn-sm" onclick="loadRecords()">🔍 Refresh</button>
    </div>
    <div id="records-table"><div style="color:var(--muted)">Loading…</div></div>
  </div>
</div>

<!-- ═══════════════════════════════ PREDICT ══════════════════════════════════ -->
<div id="page-predict" class="page">
  <div class="section-title">AI Prediction Engine</div>
  <div class="card">
    <h3>🤖 Run Batch Analysis</h3>
    <p style="font-size:.85rem;color:var(--muted);margin-bottom:1rem">
      Scans all stored records → fits linear trend (scipy) → classifies next-month tier (RandomForest).
    </p>
    <button class="btn btn-primary" onclick="runPredict()" id="predict-btn">🤖 Run AI Predictions</button>
  </div>
  <div id="predict-status"></div>
  <div id="predict-results"></div>
</div>

<!-- ═══════════════════════════════ LOGS ════════════════════════════════════ -->
<div id="page-logs" class="page">
  <div class="section-title">Activity Log</div>
  <div class="card">
    <h3>📋 Pipeline Events</h3>
    <button class="btn btn-sm btn-primary" onclick="loadLogs()" style="margin-bottom:1rem">🔄 Refresh</button>
    <div id="logs-table"><div style="color:var(--muted)">Loading…</div></div>
  </div>
</div>

</main>
</div>

<script>
// ── Utilities ──────────────────────────────────────────────────────────────
function fmt(v){ return v===null||v===undefined?'—':v; }
function fmtKwh(v){ return v!==null&&v!==undefined ? parseFloat(v).toFixed(1)+' kWh' : '—'; }
function fmtPct(v){ return v!==null&&v!==undefined ? (parseFloat(v)*100).toFixed(0)+'%' : '—'; }
function tierChip(t){ return t?`<span class="tier-chip tier-${t}">${t}</span>`:'<span class="tier-chip tier-MEDIUM">?</span>'; }
function dirSpan(d){ return `<span class="dir-${d}">${d==='INCREASING'?'▲':d==='DECREASING'?'▼':'→'} ${d}</span>`; }

function showPage(id,btn){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
  document.getElementById('page-'+id).classList.add('active');
  btn.classList.add('active');
  if(id==='records') loadRecords();
  if(id==='logs') loadLogs();
  if(id==='overview') refreshOverview();
}

async function api(method,path,body){
  const opts={method,headers:{'Content-Type':'application/json'}};
  if(body) opts.body=JSON.stringify(body);
  const r=await fetch(path,opts);
  return {status:r.status,data:await r.json()};
}

function status(elId,msg,type){
  const el=document.getElementById(elId);
  el.innerHTML=`<div class="status-bar ${type}">${msg}</div>`;
}

// ── Health + Overview ──────────────────────────────────────────────────────
let _latestReport=null;
let _reportCount=0;

async function refreshOverview(){
  try{
    const {data}=await api('GET','/health');
    document.getElementById('kpi-records').textContent=data.records;
    document.getElementById('kpi-status').textContent='ONLINE';
    document.getElementById('health-dot').innerHTML='<span style="color:var(--green)">● Live</span>';

    const {data:cd}=await api('GET','/customers');
    document.getElementById('kpi-customers').textContent=cd.customers.length;
    document.getElementById('kpi-reports').textContent=_reportCount;

    if(_latestReport){
      renderFleetAlerts(_latestReport);
      renderFleetChart(_latestReport);
    }
  }catch(e){
    document.getElementById('health-dot').innerHTML='<span style="color:var(--red)">● Offline</span>';
  }
}

function renderFleetAlerts(report){
  const fs=report.fleet_summary;
  let html='';
  if(fs.customers_at_risk&&fs.customers_at_risk.length){
    html+=`<div class="alert alert-critical">🚨 <strong>At-Risk Customers (HIGH/CRITICAL tier predicted):</strong> ${fs.customers_at_risk.join(', ')}</div>`;
  }
  if(fs.customers_declining&&fs.customers_declining.length){
    html+=`<div class="alert alert-warn">📉 <strong>Declining Usage:</strong> ${fs.customers_declining.join(', ')} — consider retention outreach.</div>`;
  }
  document.getElementById('fleet-alerts').innerHTML=html;
}

function renderFleetChart(report){
  const preds=report.customer_predictions;
  if(!preds||!preds.length) return;
  const COLORS={'LOW':'var(--green)','MEDIUM':'var(--indigo)','HIGH':'var(--amber)','CRITICAL':'var(--red)'};
  const maxKwh=Math.max(...preds.map(p=>p.prediction.predicted_kwh));
  let html='';
  preds.forEach(p=>{
    const kwh=p.prediction.predicted_kwh;
    const tier=p.prediction.predicted_tier;
    const pct=Math.round(kwh/Math.max(maxKwh,1)*100);
    html+=`<div class="bar-row">
      <span class="bar-label">${p.customer_id}</span>
      <div class="bar-track">
        <div class="bar-fill" style="width:${pct}%;background:${COLORS[tier]||'var(--indigo)'}">
          ${tierChip(tier)}
        </div>
      </div>
      <span class="bar-val">${kwh.toFixed(0)} kWh</span>
    </div>`;
  });
  document.getElementById('fleet-chart').innerHTML=html;
}

// ── Ingest ─────────────────────────────────────────────────────────────────
async function sendIngest(){
  const payload={
    customer_id:  document.getElementById('f-cid').value,
    energy_kwh:   parseFloat(document.getElementById('f-kwh').value),
    period_month: document.getElementById('f-pm').value,
    energy_tier:  document.getElementById('f-tier').value||undefined,
    region:       document.getElementById('f-region').value||undefined,
    device_count: parseInt(document.getElementById('f-dc').value)||undefined,
    temperature_avg_c: parseFloat(document.getElementById('f-temp').value)||undefined,
    notes:        document.getElementById('f-notes').value||undefined,
  };
  Object.keys(payload).forEach(k=>payload[k]===undefined&&delete payload[k]);
  _sendPayload(payload);
}

async function sendRaw(){
  let payload;
  try{ payload=JSON.parse(document.getElementById('raw-json').value); }
  catch(e){ status('ingest-status','❌ Invalid JSON: '+e.message,'err'); return; }
  _sendPayload(payload);
}

async function _sendPayload(payload){
  status('ingest-status','<span class="spinner"></span> Sending…','info');
  try{
    const {status:s,data}=await api('POST','/ingest',payload);
    const box=document.getElementById('ingest-response');
    box.textContent=JSON.stringify(data,null,2);
    if(s===201){
      status('ingest-status',`✅ Record ingested — ID: ${data.record_id}  |  Customer: ${data.customer_id}`,'ok');
    } else {
      status('ingest-status',`❌ ${s} — ${data.error}: ${data.detail}`,'err');
    }
  }catch(e){ status('ingest-status','❌ Network error: '+e.message,'err'); }
}

function randomise(){
  const customers=['CUST-010','CUST-020','CUST-030','CUST-042','CUST-099'];
  const tiers=['low','medium','high','critical'];
  const regions=['North','South','East','West'];
  const months=['2024-07','2024-08','2024-09','2024-10','2024-11','2024-12'];
  document.getElementById('f-cid').value=customers[Math.floor(Math.random()*customers.length)];
  document.getElementById('f-kwh').value=(200+Math.random()*800).toFixed(1);
  document.getElementById('f-pm').value=months[Math.floor(Math.random()*months.length)];
  document.getElementById('f-tier').value=tiers[Math.floor(Math.random()*tiers.length)];
  document.getElementById('f-region').value=regions[Math.floor(Math.random()*regions.length)];
  document.getElementById('f-dc').value=Math.floor(2+Math.random()*12);
  document.getElementById('f-temp').value=(3+Math.random()*22).toFixed(1);
}

function loadCurlExample(){
  document.getElementById('raw-json').value=JSON.stringify({
    customer_id:"CUST-042",energy_kwh:487.3,period_month:"2024-07",
    energy_tier:"medium",region:"West",device_count:6,temperature_avg_c:18.5,
    notes:"Summer air-conditioning spike"
  },null,2);
}

async function batchIngest(){
  const cid=document.getElementById('batch-cid').value.trim();
  if(!cid){ return; }
  const base=300+Math.random()*300;
  const slope=20+Math.random()*30;
  const months=['2024-01','2024-02','2024-03','2024-04','2024-05','2024-06'];
  let ok=0;
  document.getElementById('batch-status').innerHTML='<span class="spinner"></span> Ingesting…';
  for(let i=0;i<months.length;i++){
    const kwh=base+slope*i+Math.random()*20;
    const tierVal=kwh<400?'low':kwh<600?'medium':kwh<900?'high':'critical';
    const {status:s}=await api('POST','/ingest',{
      customer_id:cid,energy_kwh:Math.round(kwh*10)/10,
      period_month:months[i],energy_tier:tierVal,
      device_count:Math.floor(3+i),temperature_avg_c:Math.round((4+i*2)*10)/10
    });
    if(s===201) ok++;
  }
  document.getElementById('batch-status').innerHTML=
    `<div class="status-bar ok">✅ Inserted ${ok}/6 records for ${cid}</div>`;
  refreshOverview();
}

// ── Records ────────────────────────────────────────────────────────────────
async function loadRecords(){
  const cid=document.getElementById('filter-cid').value.trim();
  const url=cid?`/records?customer_id=${encodeURIComponent(cid)}`:'/records';
  const {data}=await api('GET',url);
  const rows=data.records||[];
  if(!rows.length){
    document.getElementById('records-table').innerHTML=
      '<div style="color:var(--muted);padding:1rem">No records found.</div>';
    return;
  }
  let html=`<div style="color:var(--muted);font-size:.8rem;margin-bottom:.8rem">${rows.length} records</div>
  <div style="overflow-x:auto"><table>
    <thead><tr>
      <th>Customer</th><th>Period</th><th>kWh</th><th>Tier</th>
      <th>Region</th><th>Devices</th><th>Temp °C</th><th>Ingested</th>
    </tr></thead><tbody>`;
  rows.forEach(r=>{
    const ts=r.ingested_at?r.ingested_at.substring(0,19).replace('T',' '):'—';
    html+=`<tr>
      <td><strong>${fmt(r.customer_id)}</strong></td>
      <td>${fmt(r.period_month)}</td>
      <td>${fmtKwh(r.energy_kwh)}</td>
      <td>${tierChip(r.energy_tier)}</td>
      <td>${fmt(r.region)}</td>
      <td>${fmt(r.device_count)}</td>
      <td>${r.temperature_c!=null?parseFloat(r.temperature_c).toFixed(1)+'°C':'—'}</td>
      <td style="font-size:.75rem;color:var(--muted)">${ts}</td>
    </tr>`;
  });
  html+='</tbody></table></div>';
  document.getElementById('records-table').innerHTML=html;
}

// ── Predict ────────────────────────────────────────────────────────────────
async function runPredict(){
  const btn=document.getElementById('predict-btn');
  btn.disabled=true;
  btn.innerHTML='<span class="spinner"></span> Running AI engine…';
  status('predict-status','<span class="spinner"></span> Scanning records and training models…','info');
  document.getElementById('predict-results').innerHTML='';
  try{
    const {status:s,data}=await api('POST','/predict',{});
    if(s!==200){
      status('predict-status','❌ '+data.error+': '+(data.detail||''),'err');
      btn.disabled=false; btn.innerHTML='🤖 Run AI Predictions'; return;
    }
    _latestReport=data; _reportCount++;
    status('predict-status',
      `✅ Analysis complete — ${data.report_metadata.total_customers} customers, `+
      `${data.report_metadata.total_records} records, `+
      `report saved to /reports/`,'ok');
    renderPredictResults(data);
    renderFleetAlerts(data);
    renderFleetChart(data);
    document.getElementById('kpi-reports').textContent=_reportCount;
  }catch(e){ status('predict-status','❌ '+e.message,'err'); }
  btn.disabled=false; btn.innerHTML='🤖 Run AI Predictions';
}

function renderPredictResults(data){
  const preds=data.customer_predictions||[];
  const fs=data.fleet_summary||{};
  let html=`<div class="card">
    <h3>📊 Fleet Summary</h3>
    <div class="flex" style="gap:2rem;flex-wrap:wrap">
      <div><div style="font-size:.75rem;color:var(--muted)">Customers Analysed</div>
        <div style="font-size:1.6rem;font-weight:700">${data.report_metadata.total_customers}</div></div>
      <div><div style="font-size:.75rem;color:var(--muted)">Records Scanned</div>
        <div style="font-size:1.6rem;font-weight:700">${data.report_metadata.total_records}</div></div>
      <div><div style="font-size:.75rem;color:var(--muted)">At Risk</div>
        <div style="font-size:1.6rem;font-weight:700;color:var(--red)">${(fs.customers_at_risk||[]).length}</div></div>
      <div><div style="font-size:.75rem;color:var(--muted)">Declining</div>
        <div style="font-size:1.6rem;font-weight:700;color:var(--green)">${(fs.customers_declining||[]).length}</div></div>
    </div>
  </div>`;

  preds.forEach(p=>{
    const t=p.trend_analysis; const pr=p.prediction; const hs=p.historical_summary;
    const confPct=Math.round(pr.confidence*100);
    html+=`<div class="card">
      <h3>${p.customer_id} &nbsp;<span style="font-size:.8rem;color:var(--muted)">${p.record_count} records &nbsp;|&nbsp; ${p.date_range.first} → ${p.date_range.last}</span></h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem;margin-bottom:1rem">
        <div class="kpi" style="border-left-color:var(--cyan);padding:.8rem">
          <div class="val" style="font-size:1.4rem">${pr.predicted_kwh.toFixed(1)}</div>
          <div class="lbl">Predicted kWh</div>
          <div style="font-size:.72rem;color:var(--muted);margin-top:.2rem">${pr.kwh_lower_bound.toFixed(0)}–${pr.kwh_upper_bound.toFixed(0)} kWh (95% CI)</div>
        </div>
        <div class="kpi" style="border-left-color:var(--violet);padding:.8rem">
          <div class="val" style="font-size:1.4rem">${tierChip(pr.predicted_tier)}</div>
          <div class="lbl">Predicted Tier</div>
          <div style="font-size:.72rem;color:var(--muted);margin-top:.2rem">via ${pr.method.replace('_',' ')}</div>
        </div>
        <div class="kpi" style="border-left-color:var(--green);padding:.8rem">
          <div class="val" style="font-size:1.4rem">${confPct}%</div>
          <div class="lbl">Confidence</div>
          <div class="progress" style="margin-top:.5rem"><div class="progress-fill" style="width:${confPct}%"></div></div>
        </div>
        <div class="kpi" style="border-left-color:var(--amber);padding:.8rem">
          <div class="val" style="font-size:1.4rem">${dirSpan(t.direction)}</div>
          <div class="lbl">Trend Direction</div>
          <div style="font-size:.72rem;color:var(--muted);margin-top:.2rem">slope ${t.slope_kwh_per_month>0?'+':''}${t.slope_kwh_per_month} kWh/mo</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;font-size:.82rem;margin-bottom:1rem">
        <div style="background:var(--surf2);border-radius:8px;padding:.9rem">
          <div style="color:var(--muted);margin-bottom:.5rem;font-size:.72rem;text-transform:uppercase">Historical Summary</div>
          <div>Avg: <strong>${hs.avg_kwh} kWh</strong></div>
          <div>Min: ${hs.min_kwh} kWh &nbsp;|&nbsp; Max: ${hs.max_kwh} kWh</div>
          <div>Std Dev: ${hs.std_kwh} kWh</div>
          <div>Most Common Tier: ${tierChip(hs.most_common_tier)}</div>
        </div>
        <div style="background:var(--surf2);border-radius:8px;padding:.9rem">
          <div style="color:var(--muted);margin-bottom:.5rem;font-size:.72rem;text-transform:uppercase">Trend Model Stats</div>
          <div>R²: <strong>${t.r_squared}</strong></div>
          <div>p-value: ${t.p_value}</div>
          <div>Slope: ${t.slope_kwh_per_month > 0?'+':''}${t.slope_kwh_per_month} kWh/month</div>
          <div>Direction: ${dirSpan(t.direction)}</div>
        </div>
      </div>
      <div style="background:rgba(99,102,241,.07);border:1px solid rgba(99,102,241,.2);
          border-radius:8px;padding:.9rem;font-size:.83rem;color:#c7d2fe">
        💡 ${p.recommendation}
      </div>
    </div>`;
  });
  document.getElementById('predict-results').innerHTML=html;
}

// ── Logs ───────────────────────────────────────────────────────────────────
async function loadLogs(){
  const {data}=await api('GET','/logs');
  const logs=data.logs||[];
  if(!logs.length){
    document.getElementById('logs-table').innerHTML='<div style="color:var(--muted)">No events yet.</div>';
    return;
  }
  let html='<div style="overflow-x:auto"><table><thead><tr><th>#</th><th>Time</th><th>Event</th><th>Detail</th></tr></thead><tbody>';
  logs.forEach(l=>{
    const ts=l.run_at?l.run_at.substring(0,19).replace('T',' '):'—';
    const color=l.event==='PREDICT'?'var(--indigo)':l.event==='INGEST'?'var(--green)':
                l.event==='SEED'?'var(--cyan)':'var(--muted)';
    html+=`<tr><td style="color:var(--muted);font-size:.75rem">${l.id}</td>
      <td style="font-size:.78rem;color:var(--muted)">${ts}</td>
      <td><span style="color:${color};font-weight:700;font-size:.8rem">${l.event}</span></td>
      <td style="font-size:.82rem">${l.detail||'—'}</td></tr>`;
  });
  html+='</tbody></table></div>';
  document.getElementById('logs-table').innerHTML=html;
}

// ── Boot ───────────────────────────────────────────────────────────────────
refreshOverview();
setInterval(refreshOverview,30000);
</script>
</body>
</html>"""

@app.route("/", methods=["GET"])
def dashboard():
    return render_template_string(DASHBOARD_HTML)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"\n⚡ Intelligent Energy Analytics POC")
    print(f"   Dashboard : http://localhost:{port}")
    print(f"   API docs  : http://localhost:{port}/health")
    print(f"   Records   : {store.count_records()} in database\n")
    app.run(host="0.0.0.0", port=port, debug=False)
