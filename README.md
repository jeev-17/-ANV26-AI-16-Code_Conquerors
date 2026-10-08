# SafeRouteAI

AI-powered route risk analysis for San Diego, CA, based on historical US-Accidents data.
Research/demo only — see disclaimer below.

## Run

```bash
# 1. Backend (Python 3.10+)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Train ONCE (downloads yuvidhepe/us-accidents-updated, filters San Diego, trains XGBoost,
#    saves artifacts/ + data/processed/). Prints schema, class distribution, missing values, metrics.
python -m models.risk_model

# 3. Serve
uvicorn main:app --reload --port 8000

# 4. Frontend (new terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173
```

Check `backend/data/processed/data_report.json` (schema, San Diego row count, Severity distribution,
missing values) and `backend/artifacts/model/meta.json` (accuracy, precision, recall, F1, confusion matrix).

## How the numbers are produced (no hard-coded values)
- **Target**: `Severity` (1-4), multi-class XGBoost. Features: weather, road flags (junction, crossing, signal…),
  time features (hour, weekday, month, weekend, time-of-day), lat/lng. Excluded: ID, Description, End_Time,
  Distance(mi) (post-accident), Source. Split: 80/20 stratified, `random_state=42`; classes with <20 rows dropped.
- **Risk score (0-100)** = `100 * Σ_k P(severity=k) * (k-1)/3`. Levels: 0-25 Low, 26-50 Moderate, 51-75 High, 76-100 Critical.
- **Routing**: OSRM returns geometry + estimated time only. Routes are cut into ≤400 m segments (by OSRM step/road name).
- **Segment features**: road-feature shares come from historical accidents within 100 m (expanding to 300/600 m)
  of the segment (GeoPandas spatial index, UTM 11N). Segments with no match are flagged `has_history=false`.
  Weather uses typical (median/mode) San Diego historical values — **no live weather**. Time = current Pacific
  time unless `hour/day_of_week/month` are sent to `/api/route-risk`.
- **Route score** = length-weighted mean of segment scores.
- **Comparison**: safest = lowest risk, fastest = lowest time, balanced = best normalised risk+time among the rest.
  If OSRM returns fewer alternatives, the missing roles show "Not available" (nothing is fabricated).
- **SHAP**: `shap.TreeExplainer` on the trained model; per-class values combined with the score's class weights
  (severity-weighted log-odds; sign shows direction).

## Endpoints
`GET /api/health` · `GET /api/model-info` · `POST /api/route` · `POST /api/predict` ·
`POST /api/route-risk` · `GET /api/segment/{id}` · `POST /api/explain`

## Limitations
The model learns from *recorded accidents only* (no exposure/traffic-volume data), so scores reflect where and
under what conditions recorded accidents were severe — not the probability of having an accident.
Nominatim/OSRM public demo servers are rate-limited; self-host for heavy use.

> Risk predictions are generated from historical accident data and are intended for research and demonstration
> purposes. Predictions indicate estimated historical accident risk and should not be interpreted as guaranteed
> accident probability or a substitute for safe driving. Routing times are estimates and are not based on live traffic.
