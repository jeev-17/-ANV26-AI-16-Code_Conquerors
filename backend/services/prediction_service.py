"""Loads saved artifacts once; converts model output into the documented 0-100 risk score."""
import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class ModelNotReady(RuntimeError):
    pass


def risk_level(score: float) -> str:
    s = round(float(score), 1)
    return "Low" if s <= 25 else "Moderate" if s <= 50 else "High" if s <= 75 else "Critical"


class RiskModel:
    def __init__(self):
        mp = ROOT / "artifacts" / "model"
        pp = ROOT / "artifacts" / "preprocessor" / "preprocessor.joblib"
        if not (mp / "xgb_model.joblib").exists() or not pp.exists():
            raise ModelNotReady("Model artifacts not found. Run `python -m models.risk_model` first.")
        self.model = joblib.load(mp / "xgb_model.joblib")
        self.pre = joblib.load(pp)
        self.meta = json.loads((mp / "meta.json").read_text())
        self.classes = self.meta["classes"]
        self.features = self.meta["features"]
        self.weights = (np.array(self.classes, dtype=float) - 1.0) / 3.0 * 100.0

    def complete(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for c in self.features:
            if c not in df:
                df[c] = self.meta["defaults"][c]
        return df[self.features]

    def transform(self, df):
        return self.pre.transform(self.complete(df))

    def predict(self, df: pd.DataFrame):
        proba = self.model.predict_proba(self.transform(df))
        score = np.clip(proba @ self.weights, 0, 100)
        return proba, score


@lru_cache(maxsize=1)
def get_model() -> RiskModel:
    return RiskModel()
