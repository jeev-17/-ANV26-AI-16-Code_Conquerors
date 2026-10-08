"""Dataset loading, schema inspection and San Diego extraction (runs ONCE, at training time)."""
import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger("saferoute.dataset")
DATASET_ID = "yuvidhepe/us-accidents-updated"
ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REQUIRED = ["Severity", "Start_Time", "Start_Lat", "Start_Lng"]
# San Diego County bounding box (sanity filter on top of County/State match)
BBOX = dict(lat_min=32.53, lat_max=33.51, lng_min=-117.60, lng_max=-116.08)
KEEP = [
    "Severity", "Start_Time", "Start_Lat", "Start_Lng", "Street", "City", "County", "State",
    "Temperature(F)", "Wind_Chill(F)", "Humidity(%)", "Pressure(in)", "Visibility(mi)",
    "Wind_Speed(mph)", "Precipitation(in)", "Weather_Condition", "Sunrise_Sunset",
    "Amenity", "Bump", "Crossing", "Give_Way", "Junction", "No_Exit", "Railway",
    "Roundabout", "Station", "Stop", "Traffic_Calming", "Traffic_Signal",
]


def load_raw_dataset():
    from datasets import load_dataset
    return load_dataset(DATASET_ID)


def inspect_schema(ds) -> dict:
    schema = {s: {"num_rows": d.num_rows, "columns": {k: str(v) for k, v in d.features.items()}}
              for s, d in ds.items()}
    for s, info in schema.items():
        log.info("Split %s: %d rows, %d columns", s, info["num_rows"], len(info["columns"]))
    return schema


def extract_san_diego(ds, chunk=250_000) -> pd.DataFrame:
    parts = []
    for split, d in ds.items():
        cols = list(d.features.keys())
        missing = [c for c in REQUIRED if c not in cols]
        if missing:
            raise RuntimeError(f"Dataset split '{split}' lacks required columns {missing}. Actual: {cols}")
        keep = [c for c in KEEP if c in cols]
        pd_view = d.select_columns(keep).with_format("pandas")
        for i in range(0, d.num_rows, chunk):
            df = pd_view[i:i + chunk]
            m = df["Start_Lat"].between(BBOX["lat_min"], BBOX["lat_max"]) & \
                df["Start_Lng"].between(BBOX["lng_min"], BBOX["lng_max"])
            if "County" in df and "State" in df:
                m &= (df["County"].astype(str).str.lower() == "san diego") & (df["State"] == "CA")
            if m.any():
                parts.append(df[m])
        log.info("Scanned split %s", split)
    if not parts:
        raise RuntimeError("No San Diego records found; inspect County/State/lat/lng columns.")
    out = pd.concat(parts, ignore_index=True)
    log.info("San Diego records: %d", len(out))
    return out


def data_report(sd: pd.DataFrame, schema: dict) -> dict:
    rep = {
        "dataset": DATASET_ID,
        "schema": schema,
        "san_diego_rows": int(len(sd)),
        "severity_distribution": {str(k): int(v) for k, v in sd["Severity"].value_counts().sort_index().items()},
        "missing_values": {c: int(v) for c, v in sd.isna().sum().items() if v > 0},
    }
    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "data_report.json").write_text(json.dumps(rep, indent=2))
    return rep
