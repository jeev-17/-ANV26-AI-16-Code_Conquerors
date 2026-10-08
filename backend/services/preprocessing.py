"""Feature engineering + sklearn preprocessor. Excludes ID, Description, End_Time, Distance(mi)
(Distance is measured after the accident = target-adjacent leakage) and Source."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

RAW_NUM = {"Temperature(F)": "temp", "Wind_Chill(F)": "wind_chill", "Humidity(%)": "humidity",
           "Pressure(in)": "pressure", "Visibility(mi)": "visibility", "Wind_Speed(mph)": "wind_speed",
           "Precipitation(in)": "precip", "Start_Lat": "lat", "Start_Lng": "lng"}
RAW_BOOL = {"Amenity": "amenity", "Bump": "bump", "Crossing": "crossing", "Give_Way": "give_way",
            "Junction": "junction", "No_Exit": "no_exit", "Railway": "railway", "Roundabout": "roundabout",
            "Station": "station", "Stop": "stop", "Traffic_Calming": "traffic_calming",
            "Traffic_Signal": "traffic_signal"}
TIME_NUM = ["hour", "day_of_week", "month", "weekend"]
NUMERIC = list(RAW_NUM.values()) + TIME_NUM
BOOL = list(RAW_BOOL.values())
CAT = ["weather", "time_of_day", "daylight"]
FEATURES = NUMERIC + BOOL + CAT

LABELS = {
    "temp": "Temperature", "wind_chill": "Wind Chill", "humidity": "Humidity", "pressure": "Pressure",
    "visibility": "Visibility", "wind_speed": "Wind Speed", "precip": "Precipitation", "lat": "Latitude",
    "lng": "Longitude", "hour": "Hour of Day", "day_of_week": "Day of Week", "month": "Month",
    "weekend": "Weekend", "amenity": "Amenity", "bump": "Speed Bump", "crossing": "Crossing",
    "give_way": "Give Way", "junction": "Junction", "no_exit": "No Exit", "railway": "Railway",
    "roundabout": "Roundabout", "station": "Station", "stop": "Stop Sign",
    "traffic_calming": "Traffic Calming", "traffic_signal": "Traffic Signal",
    "weather": "Weather Condition", "time_of_day": "Time of Day", "daylight": "Day/Night",
}


def bucket_weather(s: pd.Series) -> pd.Series:
    t = s.fillna("Unknown").astype(str).str.lower()
    out = pd.Series("Other", index=s.index)
    out[t.str.contains("clear|fair")] = "Clear"
    out[t.str.contains("cloud|overcast")] = "Cloudy"
    out[t.str.contains("rain|drizzle|shower|storm|thunder")] = "Rain"
    out[t.str.contains("fog|mist|haze|smoke")] = "Low Visibility"
    out[t == "unknown"] = "Unknown"
    return out


def time_of_day_from_hour(hour):
    """Night 21-5, Morning 6-11, Afternoon 12-16, Evening 17-20."""
    h = pd.Series(hour).astype(float)
    out = pd.Series("Night", index=h.index)
    out[(h >= 6) & (h <= 11)] = "Morning"
    out[(h >= 12) & (h <= 16)] = "Afternoon"
    out[(h >= 17) & (h <= 20)] = "Evening"
    return out


def daylight_from_hour(hour):
    """Deterministic approximation used for route segments (no live sun data): night = 19:00-05:59."""
    h = pd.Series(hour).astype(float)
    return pd.Series(np.where((h >= 19) | (h < 6), "Night", "Day"), index=h.index)


def engineer_features(raw: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=raw.index)
    for src, dst in RAW_NUM.items():
        f[dst] = pd.to_numeric(raw[src], errors="coerce") if src in raw else np.nan
    for src, dst in RAW_BOOL.items():
        f[dst] = raw[src].astype(str).str.lower().isin(["true", "1", "1.0"]).astype(int) if src in raw else 0
    t = pd.to_datetime(raw["Start_Time"], errors="coerce", format="mixed")
    f["hour"] = t.dt.hour
    f["day_of_week"] = t.dt.dayofweek
    f["month"] = t.dt.month
    f["weekend"] = (t.dt.dayofweek >= 5).astype(float).where(t.notna())
    f["weather"] = bucket_weather(raw["Weather_Condition"]) if "Weather_Condition" in raw else "Unknown"
    f["time_of_day"] = time_of_day_from_hour(f["hour"].fillna(12)).where(f["hour"].notna(), "Unknown")
    f["daylight"] = raw["Sunrise_Sunset"].fillna("Unknown").astype(str) if "Sunrise_Sunset" in raw else "Unknown"
    return f[FEATURES]


def build_preprocessor(num, boo, cat) -> ColumnTransformer:
    ct = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), num),
        ("bool", "passthrough", boo),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="constant", fill_value="Unknown")),
                          ("enc", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))]), cat),
    ], verbose_feature_names_out=False)
    ct.set_output(transform="pandas")
    return ct
