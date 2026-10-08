"""Real SHAP values (TreeExplainer on the trained XGBoost model).
Per-class SHAP (margin/log-odds space) are combined with the same class weights as the risk score:
contribution_f = sum_k w_k * SHAP_k,f.  Positive => pushes the risk score up. Units: weighted log-odds
(reflects direction/ranking of influence, not exact score points)."""
from functools import lru_cache

import numpy as np
import pandas as pd
import shap

from services.preprocessing import LABELS
from services.prediction_service import get_model


@lru_cache(maxsize=1)
def _explainer():
    return shap.TreeExplainer(get_model().model)


def contributions(df: pd.DataFrame) -> np.ndarray:
    rm = get_model()
    X = rm.transform(df)
    sv = _explainer().shap_values(X)
    sv = np.stack(sv, axis=2) if isinstance(sv, list) else np.asarray(sv)
    if sv.ndim == 2:
        sv = sv[:, :, None]
    w = rm.weights if sv.shape[2] == len(rm.weights) else np.ones(sv.shape[2])
    return sv @ w  # (n, features)


def _fmt(v):
    return round(float(v), 3) if isinstance(v, (int, float, np.floating, np.integer)) else str(v)


def top_factors(df: pd.DataFrame, weights=None, top_n=8):
    """df rows = segments (or one row). weights = length weights for route-level aggregation."""
    rm = get_model()
    C = contributions(df)
    w = np.ones(len(df)) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    agg = (C * w[:, None]).sum(0)
    comp = rm.complete(df)
    out = []
    for j in np.argsort(-np.abs(agg))[:top_n]:
        c = rm.features[j]
        val = comp[c].iloc[0] if len(df) == 1 else None
        out.append({"feature": c, "label": LABELS.get(c, c), "shap_value": round(float(agg[j]), 5),
                    "direction": "increases risk" if agg[j] > 0 else "decreases risk",
                    "value": _fmt(val) if val is not None else None})
    return out
