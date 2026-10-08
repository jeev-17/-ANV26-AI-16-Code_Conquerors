"""Route -> segments -> historical accident matching (GeoPandas/Shapely/PyProj) -> model risk."""
import math
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import substring

from services.prediction_service import get_model, risk_level
from services.preprocessing import BOOL, daylight_from_hour, time_of_day_from_hour

ROOT = Path(__file__).resolve().parents[1]
UTM = "EPSG:32611"  # San Diego
_to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True)
_to_ll = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True)
RADII = (100, 300, 600)  # metres; expands until historical accidents are found


@lru_cache(maxsize=1)
def accident_index():
    p = ROOT / "data" / "processed" / "sd_accidents.csv"
    if not p.exists():
        raise FileNotFoundError("Processed accident CSV missing. Run `python -m models.risk_model` first.")
    df = pd.read_csv(p)
    xs, ys = _to_utm.transform(df["lng"].values, df["lat"].values)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(xs, ys), crs=UTM)
    gdf.sindex  # build spatial index once
    return gdf


def now_context():
    n = datetime.now(ZoneInfo("America/Los_Angeles"))
    return {"hour": n.hour, "day_of_week": n.weekday(), "month": n.month}


def split_segments(steps, max_len=400, min_len=1.0):
    segs = []
    for st in steps:
        coords = st["geometry"]["coordinates"]
        if len(coords) < 2:
            continue
        xs, ys = _to_utm.transform([c[0] for c in coords], [c[1] for c in coords])
        line = LineString(list(zip(xs, ys)))
        L = line.length
        if L < min_len:
            continue
        n = max(1, math.ceil(L / max_len))
        edges = np.linspace(0, L, n + 1)
        for a, b in zip(edges[:-1], edges[1:]):
            piece = substring(line, a, b)
            if piece.length >= min_len and piece.geom_type == "LineString":
                segs.append({"road_name": st["name"] or "Unnamed road", "line": piece, "length_m": float(b - a)})
    return segs


def analyze_route(route: dict, ctx: dict, route_key: str):
    """Returns (summary dict, segments list, feature DataFrame aligned with segments)."""
    rm = get_model()
    gdf = accident_index()
    d = rm.meta["defaults"]
    segs = split_segments(route["steps"])
    if not segs:
        raise ValueError("Route contains no usable segments.")
    rows, cum = [], 0.0
    for i, s in enumerate(segs):
        line = s["line"]
        idx, radius = np.array([], dtype=int), None
        for r in RADII:
            idx = gdf.sindex.query(line.buffer(r), predicate="intersects")
            if len(idx):
                radius = r
                break
        near = gdf.iloc[idx] if len(idx) else None
        mid = line.interpolate(0.5, normalized=True)
        lng, lat = _to_ll.transform(mid.x, mid.y)
        row = {c: d[c] for c in rm.features}              # weather = typical historical San Diego values
        row.update({"lat": lat, "lng": lng, "hour": ctx["hour"], "day_of_week": ctx["day_of_week"],
                    "month": ctx["month"], "weekend": float(ctx["day_of_week"] >= 5)})
        for c in BOOL:
            if c in rm.features:
                row[c] = float(near[c].mean()) if near is not None else 0.0
        if "time_of_day" in rm.features:
            row["time_of_day"] = time_of_day_from_hour([ctx["hour"]]).iloc[0]
        if "daylight" in rm.features:
            row["daylight"] = daylight_from_hour([ctx["hour"]]).iloc[0]
        rows.append(row)
        ll = [[y, x] for x, y in zip(*_to_ll.transform(*zip(*line.coords)))]
        s.update({"id": f"{route_key}-S{i + 1}", "index": i + 1, "from_mi": cum / 1609.344,
                  "to_mi": (cum + s["length_m"]) / 1609.344, "coords": ll,
                  "location": {"lat": lat, "lng": lng}, "match_radius_m": radius,
                  "has_history": near is not None,
                  "accidents_nearby": int(len(idx)),
                  "mean_historical_severity": float(near["Severity"].mean()) if near is not None else None})
        cum += s["length_m"]
        s.pop("line")
    X = pd.DataFrame(rows)
    proba, score = rm.predict(X)
    for s, p, sc in zip(segs, proba, score):
        s["risk_score"] = round(float(sc), 1)
        s["risk_level"] = risk_level(sc)
        s["from_to"] = f"{s['from_mi']:.2f} mi → {s['to_mi']:.2f} mi"
        s["class_probabilities"] = {f"Severity {c}": round(float(v), 4) for c, v in zip(rm.classes, p)}
        s["predicted_severity"] = int(rm.classes[int(np.argmax(p))])
        s["length_m"] = round(s["length_m"], 1)
        s["from_mi"], s["to_mi"] = round(s["from_mi"], 3), round(s["to_mi"], 3)
    L = np.array([s["length_m"] for s in segs])
    sc = np.array([s["risk_score"] for s in segs])
    route_score = float((sc * L).sum() / L.sum())  # length-weighted mean of segment scores
    top = max(segs, key=lambda s: s["risk_score"])
    summary = {
        "distance_km": round(route["distance_m"] / 1000, 2), "distance_mi": round(route["distance_m"] / 1609.344, 2),
        "estimated_time_min": round(route["duration_s"] / 60, 1),
        "risk_score": round(route_score, 1), "risk_level": risk_level(route_score),
        "n_segments": len(segs),
        "high_risk_segments": int(sum(s["risk_level"] == "High" for s in segs)),
        "critical_risk_segments": int(sum(s["risk_level"] == "Critical" for s in segs)),
        "average_segment_risk": round(float(sc.mean()), 1),
        "highest_risk_segment": {"id": top["id"], "road_name": top["road_name"], "risk_score": top["risk_score"]},
        "segments_with_history": int(sum(s["has_history"] for s in segs)),
        "historical_accidents_matched": int(sum(s["accidents_nearby"] for s in segs)),
    }
    return summary, segs, X, L
