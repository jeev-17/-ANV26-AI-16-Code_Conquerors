"""SafeRouteAI FastAPI backend. Run from backend/:  uvicorn main:app --reload --port 8000"""
import logging
import uuid
from collections import OrderedDict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services import geospatial_service as geo
from services import routing_service as routing
from services.prediction_service import ModelNotReady, get_model, risk_level
from services import shap_service

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="SafeRouteAI API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["https://saferouteai-predict.netlify.app", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])

DISCLAIMER = ("Risk predictions are generated from historical accident data and are intended for research and "
              "demonstration purposes. Predictions indicate estimated historical accident risk and should not be "
              "interpreted as guaranteed accident probability or a substitute for safe driving. "
              "Routing times are estimates and are not based on live traffic.")
CACHE: "OrderedDict[str, dict]" = OrderedDict()   # analysis_id -> routes (in-memory, last 20)


class RouteRequest(BaseModel):
    start: str = Field(..., min_length=2, max_length=200)
    end: str = Field(..., min_length=2, max_length=200)
    hour: Optional[int] = Field(None, ge=0, le=23)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    month: Optional[int] = Field(None, ge=1, le=12)


class PredictRequest(BaseModel):
    features: Dict[str, Any] = Field(default_factory=dict, description="Subset of model features; others use defaults")


class ExplainRequest(BaseModel):
    analysis_id: str
    route_index: int = 0
    segment_id: Optional[str] = None


def _model():
    try:
        return get_model()
    except ModelNotReady as e:
        raise HTTPException(503, str(e))


def _geocode_pair(req: RouteRequest):
    try:
        return routing.geocode(req.start), routing.geocode(req.end)
    except routing.RoutingError as e:
        raise HTTPException(e.status, str(e))


@app.get("/api/health")
def health():
    ready = True
    try:
        get_model()
    except ModelNotReady:
        ready = False
    return {"status": "ok", "model_loaded": ready}


@app.get("/api/model-info")
def model_info():
    m = _model()
    meta = m.meta
    return {"algorithm": meta["algorithm"], "classes": meta["classes"], "features": meta["features"],
            "risk_score_formula": meta["risk_score_formula"], "metrics": meta["metrics"],
            "data_report": meta["data_report"], "disclaimer": DISCLAIMER}


@app.post("/api/route")
def route(req: RouteRequest):
    s, e = _geocode_pair(req)
    try:
        routes = routing.get_routes(s, e)
    except routing.RoutingError as ex:
        raise HTTPException(ex.status, str(ex))
    return {"start": s, "end": e, "routes": [{"distance_m": r["distance_m"], "duration_s": r["duration_s"],
                                              "path": r["path"]} for r in routes]}


@app.post("/api/predict")
def predict(req: PredictRequest):
    m = _model()
    unknown = [k for k in req.features if k not in m.features]
    if unknown:
        raise HTTPException(422, f"Unknown features {unknown}. Valid: {m.features}")
    proba, score = m.predict(pd.DataFrame([req.features]))
    return {"risk_score": round(float(score[0]), 1), "risk_level": risk_level(score[0]),
            "class_probabilities": {f"Severity {c}": round(float(p), 4) for c, p in zip(m.classes, proba[0])},
            "note": "Estimated historical accident risk, not a guarantee."}


@app.post("/api/route-risk")
def route_risk(req: RouteRequest):
    _model()
    s, e = _geocode_pair(req)
    try:
        raw_routes = routing.get_routes(s, e)
    except routing.RoutingError as ex:
        raise HTTPException(ex.status, str(ex))
    ctx = geo.now_context()
    ctx.update({k: v for k, v in (("hour", req.hour), ("day_of_week", req.day_of_week), ("month", req.month)) if v is not None})
    aid = uuid.uuid4().hex[:10]
    routes, store = [], []
    try:
        for i, r in enumerate(raw_routes):
            summary, segs, X, L = geo.analyze_route(r, ctx, f"{aid}-R{i}")
            routes.append({"index": i, "summary": summary, "segments": segs, "path": r["path"]})
            store.append({"segments": {sg["id"]: j for j, sg in enumerate(segs)}, "X": X, "L": L, "seg_list": segs})
    except FileNotFoundError as ex:
        raise HTTPException(503, str(ex))
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    scores = np.array([r["summary"]["risk_score"] for r in routes])
    times = np.array([r["summary"]["estimated_time_min"] for r in routes])
    safest, fastest = int(np.argmin(scores)), int(np.argmin(times))
    balanced = None
    rest = [i for i in range(len(routes)) if i not in (safest, fastest)]
    if rest:
        def norm(a): return (a - a.min()) / (a.max() - a.min()) if a.max() > a.min() else np.zeros_like(a)
        comb = norm(scores) + norm(times)
        balanced = int(min(rest, key=lambda i: comb[i]))
    CACHE[aid] = {"routes": store}
    while len(CACHE) > 20:
        CACHE.popitem(last=False)
    return {"analysis_id": aid, "start": s, "end": e, "context": ctx, "routes": routes,
            "comparison": {"safest": safest, "balanced": balanced, "fastest": fastest},
            "notes": ["Estimated Time comes from OSRM routing, not live traffic.",
                      "Weather inputs use typical historical San Diego values (no live weather).",
                      "Segment features come from historical accidents within 100-600 m; segments with none are flagged."],
            "disclaimer": DISCLAIMER}


def _entry(aid, ri):
    if aid not in CACHE or ri >= len(CACHE[aid]["routes"]):
        raise HTTPException(404, "Analysis not found or expired. Generate routes again.")
    return CACHE[aid]["routes"][ri]


@app.get("/api/segment/{segment_id}")
def segment(segment_id: str):
    try:
        aid, rk, _ = segment_id.split("-")
        ri = int(rk[1:])
    except ValueError:
        raise HTTPException(400, "Malformed segment id.")
    ent = _entry(aid, ri)
    j = ent["segments"].get(segment_id)
    if j is None:
        raise HTTPException(404, "Segment not found.")
    return ent["seg_list"][j]


@app.post("/api/explain")
def explain(req: ExplainRequest):
    _model()
    ent = _entry(req.analysis_id, req.route_index)
    if req.segment_id:
        j = ent["segments"].get(req.segment_id)
        if j is None:
            raise HTTPException(404, "Segment not found.")
        factors = shap_service.top_factors(ent["X"].iloc[[j]])
        scope = "segment"
    else:
        factors = shap_service.top_factors(ent["X"], weights=ent["L"])
        scope = "route (length-weighted mean of segment SHAP values)"
    return {"scope": scope, "factors": factors,
            "units": "SHAP values in severity-weighted log-odds space; positive = increases predicted risk"}
