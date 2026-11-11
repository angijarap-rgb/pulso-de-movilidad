import numpy as np
import pandas as pd

LAGS = (2, 3, 12)
LAG_COLUMNS = [f"lag_{lag}" for lag in LAGS]
FEATURES = ["month_sin", "month_cos", *LAG_COLUMNS]
HORIZON = 1


def make_features(history, future_months=0):
    stop = history["day"].max() + pd.DateOffset(months=future_months)
    months = pd.date_range(history["day"].min(), stop, freq="MS")
    grid = pd.MultiIndex.from_product([sorted(history["zone"].unique()), months], names=["zone", "day"])
    frame = history.set_index(["zone", "day"]).reindex(grid).reset_index()
    groups = frame.groupby("zone", sort=False)["trips"]
    for lag, column in zip(LAGS, LAG_COLUMNS, strict=True):
        frame[column] = groups.shift(lag).astype(float)
    phase = 2 * np.pi * (frame["day"].dt.month - 1) / 12
    frame["month_sin"] = np.sin(phase)
    frame["month_cos"] = np.cos(phase)
    frame["seasonal"] = frame["lag_12"]
    return frame.dropna(subset=LAG_COLUMNS).sort_values(["day", "zone"]).reset_index(drop=True)
