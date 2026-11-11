import numpy as np
import pandas as pd

LAGS = (98, 105, 112, 119)
LAG_COLUMNS = [f"lag_{lag}" for lag in LAGS]
FEATURES = ["zone", "weekday", "month_sin", "month_cos", *LAG_COLUMNS, "seasonal"]
HORIZON = 1


def make_features(history, future_days=0):
    start = history["day"].min()
    stop = history["day"].max() + pd.Timedelta(days=future_days)
    days = pd.date_range(start, stop)
    zones = sorted(history["zone"].unique())
    grid = pd.MultiIndex.from_product([zones, days], names=["zone", "day"])
    frame = history.set_index(["zone", "day"]).reindex(grid).reset_index()
    groups = frame.groupby("zone", sort=False)["trips"]
    for lag, column in zip(LAGS, LAG_COLUMNS, strict=True):
        frame[column] = groups.shift(lag)
    frame["weekday"] = frame["day"].dt.weekday
    phase = 2 * np.pi * (frame["day"].dt.month - 1) / 12
    frame["month_sin"] = np.sin(phase)
    frame["month_cos"] = np.cos(phase)
    frame["seasonal"] = frame[LAG_COLUMNS].median(axis=1, skipna=False)
    return frame.dropna(subset=LAG_COLUMNS).sort_values(["day", "zone"]).reset_index(drop=True)
