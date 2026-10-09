"""Congestion data disabled: the model trains on accident data only."""

FEATURE_COLS = []


def available():
    return False


def features_for(lat, lng, hour):
    # Never called while available() is False
    return {}
