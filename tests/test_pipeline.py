"""
tests/test_pipeline.py — Full pipeline integration tests
"""
import sys, os, pytest, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ingest import validate_and_clean
import src.store as store_mod

# ── helpers pulled from predict since they're module-level functions ──────────
def linregress(xs, ys):
    n = len(xs)
    xm = sum(xs)/n; ym = sum(ys)/n
    ssxy = sum((xs[i]-xm)*(ys[i]-ym) for i in range(n))
    ssxx = sum((v-xm)**2 for v in xs) or 1
    ssyy = sum((v-ym)**2 for v in ys) or 1
    slope = ssxy/ssxx
    intercept = ym - slope*xm
    r2 = (ssxy**2)/(ssxx*ssyy)
    pred = slope*n + intercept
    avg = ym; thr = avg*0.02
    direction = "INCREASING" if slope>thr else ("DECREASING" if slope<-thr else "STABLE")
    return {"slope":round(slope,3),"r2":round(r2,4),"pred":round(max(pred,0),2),"dir":direction}

def kwhToTier(kwh):
    if kwh < 400: return "LOW"
    if kwh < 600: return "MEDIUM"
    if kwh < 900: return "HIGH"
    return "CRITICAL"

@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(store_mod, 'DB_PATH', tmp_path / 'test.db')
    store_mod.initialise()
    yield

class TestIngest:
    def test_valid_payload(self):
        r = validate_and_clean({'customer_id':'CUST-001','energy_kwh':450.5,
                                'period_month':'2024-07','energy_tier':'medium','region':'North'})
        assert r['customer_id'] == 'CUST-001'
        assert r['energy_kwh'] == 450.5
        assert r['energy_tier'] == 'MEDIUM'
        assert r['region'] == 'NORTH'

    def test_bare_integer_prefixed(self):
        r = validate_and_clean({'customer_id':'42','energy_kwh':300,'period_month':'2024-01'})
        assert r['customer_id'] == 'CUST-42'

    def test_missing_field_raises(self):
        with pytest.raises(ValueError, match='Missing required fields'):
            validate_and_clean({'customer_id':'CUST-001','energy_kwh':300})

    def test_negative_kwh_raises(self):
        with pytest.raises(ValueError):
            validate_and_clean({'customer_id':'X','energy_kwh':-10,'period_month':'2024-01'})

    def test_bad_period_raises(self):
        with pytest.raises(ValueError, match='YYYY-MM'):
            validate_and_clean({'customer_id':'X','energy_kwh':300,'period_month':'07-2024'})

    def test_tier_normalisation(self):
        for raw, exp in [('low','LOW'),('med','MEDIUM'),('hi','HIGH'),('crit','CRITICAL')]:
            r = validate_and_clean({'customer_id':'X','energy_kwh':100,
                                    'period_month':'2024-01','energy_tier':raw})
            assert r['energy_tier'] == exp

class TestPredict:
    def test_kwh_to_tier(self):
        assert kwhToTier(200) == 'LOW'
        assert kwhToTier(450) == 'MEDIUM'
        assert kwhToTier(700) == 'HIGH'
        assert kwhToTier(950) == 'CRITICAL'

    def test_increasing_trend(self):
        kwhs = [300,330,360,390,420,450]
        t = linregress(list(range(len(kwhs))), kwhs)
        assert t['dir'] == 'INCREASING'
        assert t['slope'] > 0
        assert t['r2'] > 0.99

    def test_decreasing_trend(self):
        kwhs = [500,480,460,440,420,400]
        t = linregress(list(range(len(kwhs))), kwhs)
        assert t['dir'] == 'DECREASING'
        assert t['slope'] < 0

    def test_batch_pipeline(self):
        store_mod.seed_sample_data()
        from src.predict import run_batch
        records = store_mod.scan_all()
        report = run_batch(records)
        assert report['report_metadata']['total_customers'] == 3
        assert report['report_metadata']['total_records'] == 18
        custs = {p['customer_id']:p for p in report['customer_predictions']}
        assert custs['CUST-002']['trend_analysis']['direction'] == 'INCREASING'
        assert custs['CUST-003']['trend_analysis']['direction'] == 'DECREASING'
        assert 'CUST-002' in report['fleet_summary']['customers_at_risk']
        assert 'CUST-003' in report['fleet_summary']['customers_declining']

    def test_prediction_keys(self):
        store_mod.seed_sample_data()
        from src.predict import run_batch
        report = run_batch(store_mod.scan_all())
        for p in report['customer_predictions']:
            pred = p['prediction']
            assert 'predicted_kwh' in pred
            assert pred['predicted_tier'] in ('LOW','MEDIUM','HIGH','CRITICAL')
            assert 0.0 <= pred['confidence'] <= 1.0
