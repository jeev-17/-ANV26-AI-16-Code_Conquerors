"""Training pipeline. Run ONCE from backend/:  python -m models.risk_model"""
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import dataset_service as ds_svc
from services.preprocessing import BOOL, CAT, FEATURES, NUMERIC, build_preprocessor, engineer_features

ROOT = Path(__file__).resolve().parents[1]
ART_MODEL = ROOT / "artifacts" / "model"
ART_PRE = ROOT / "artifacts" / "preprocessor"
SEED = 42
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("saferoute.train")


def main():
    ds = ds_svc.load_raw_dataset()
    schema = ds_svc.inspect_schema(ds)
    raw = ds_svc.extract_san_diego(ds)
    raw["Severity"] = pd.to_numeric(raw["Severity"], errors="coerce")
    raw = raw.dropna(subset=["Severity"]).reset_index(drop=True)
    report = ds_svc.data_report(raw, schema)
    log.info("Severity distribution: %s", report["severity_distribution"])
    log.info("Missing values: %s", report["missing_values"])

    X = engineer_features(raw)
    usable = [c for c in FEATURES if X[c].notna().any()]
    dropped = sorted(set(FEATURES) - set(usable))
    if dropped:
        log.warning("Dropping features absent/empty in dataset: %s", dropped)
    num = [c for c in NUMERIC if c in usable]; boo = [c for c in BOOL if c in usable]; cat = [c for c in CAT if c in usable]

    # classes with too few samples cannot be split/learned reliably
    counts = raw["Severity"].value_counts()
    classes = sorted(int(c) for c, n in counts.items() if n >= 20)
    keep = raw["Severity"].astype(int).isin(classes)
    X, y_sev = X[keep].reset_index(drop=True), raw.loc[keep, "Severity"].astype(int).reset_index(drop=True)
    y = y_sev.map({c: i for i, c in enumerate(classes)}).values
    log.info("Training classes (Severity): %s", classes)

    # persist processed accidents for geospatial matching (CSV)
    out = X[usable].copy(); out["Severity"] = y_sev
    out["Street"] = raw.loc[keep, "Street"].reset_index(drop=True) if "Street" in raw else ""
    out.to_csv(ds_svc.PROCESSED / "sd_accidents.csv", index=False)

    Xtr, Xte, ytr, yte = train_test_split(X[usable], y, test_size=0.2, random_state=SEED, stratify=y)
    Xtr, Xva, ytr, yva = train_test_split(Xtr, ytr, test_size=0.1, random_state=SEED, stratify=ytr)

    pre = build_preprocessor(num, boo, cat).fit(Xtr)
    Ptr, Pva, Pte = pre.transform(Xtr), pre.transform(Xva), pre.transform(Xte)

    cnt = np.bincount(ytr, minlength=len(classes))
    cw = (len(ytr) / (len(classes) * cnt)) ** 0.5     # sqrt-balanced: softens imbalance without wrecking calibration
    model = XGBClassifier(objective="multi:softprob", n_estimators=400, max_depth=6, learning_rate=0.08,
                          subsample=0.9, colsample_bytree=0.9, tree_method="hist", random_state=SEED,
                          early_stopping_rounds=25, eval_metric="mlogloss", n_jobs=-1)
    model.fit(Ptr, ytr, sample_weight=cw[ytr], eval_set=[(Pva, yva)], verbose=False)

    pred = model.predict(Pte)
    p, r, f, _ = precision_recall_fscore_support(yte, pred, average="weighted", zero_division=0)
    pm, rm, fm, _ = precision_recall_fscore_support(yte, pred, average="macro", zero_division=0)
    metrics = {
        "accuracy": float(accuracy_score(yte, pred)),
        "precision_weighted": float(p), "recall_weighted": float(r), "f1_weighted": float(f),
        "precision_macro": float(pm), "recall_macro": float(rm), "f1_macro": float(fm),
        "confusion_matrix": confusion_matrix(yte, pred, labels=range(len(classes))).tolist(),
        "confusion_matrix_labels_severity": classes,
        "per_class": classification_report(yte, pred, target_names=[f"Severity {c}" for c in classes],
                                           output_dict=True, zero_division=0),
        "n_train": int(len(ytr)), "n_test": int(len(yte)), "random_state": SEED,
    }
    log.info("Accuracy %.3f | weighted F1 %.3f | macro F1 %.3f", metrics["accuracy"], metrics["f1_weighted"], metrics["f1_macro"])

    defaults = {c: float(X[c].median()) for c in num}
    defaults.update({c: 0 for c in boo})
    defaults.update({c: str(X[c].mode().iloc[0]) for c in cat})
    meta = {"classes": classes, "numeric": num, "bool": boo, "categorical": cat, "features": usable,
            "defaults": defaults, "metrics": metrics, "data_report": {k: v for k, v in report.items() if k != "schema"},
            "risk_score_formula": "score = 100 * sum_k P(severity=k) * (k-1)/3  (probability-weighted severity, 0-100)",
            "algorithm": "XGBoost multi:softprob"}
    ART_MODEL.mkdir(parents=True, exist_ok=True); ART_PRE.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ART_MODEL / "xgb_model.joblib")
    joblib.dump(pre, ART_PRE / "preprocessor.joblib")
    (ART_MODEL / "meta.json").write_text(json.dumps(meta, indent=2, default=str))
    log.info("Saved artifacts to %s", ROOT / "artifacts")


if __name__ == "__main__":
    main()
