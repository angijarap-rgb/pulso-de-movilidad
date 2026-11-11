import numpy as np
from sklearn.metrics import mean_absolute_error


def scores(frame, prediction):
    actual = frame["trips"].to_numpy()
    errors = np.abs(actual - prediction)
    return {
        "mae": float(mean_absolute_error(actual, prediction)),
        "wape": float(errors.sum() / actual.sum()) if actual.sum() else None,
        "rows": len(frame),
        "zones": {
            str(zone): float(errors[frame["zone"].to_numpy() == zone].mean())
            for zone in sorted(frame["zone"].unique())
        },
    }


def promotion(baseline, challenger):
    improvement = (baseline["mae"] - challenger["mae"]) / max(baseline["mae"], 1)
    regressions = [
        zone for zone, error in baseline["zones"].items()
        if challenger["zones"][zone] > error + max(error * 0.10, 5)
    ]
    return {
        "active": "challenger" if improvement >= 0.03 and not regressions else "baseline",
        "validation_improvement": float(improvement),
        "minimum_improvement": 0.03,
        "regressed_zones": regressions,
    }


def monitor(reference, evaluation, active_column):
    results = []
    for (month, zone), window in evaluation.groupby([evaluation["day"].dt.to_period("Q"), "zone"]):
        baseline = reference[reference["zone"] == zone]
        scale = max(float(baseline["seasonal"].quantile(.75) - baseline["seasonal"].quantile(.25)), 1)
        drift = abs(float(window["seasonal"].mean() - baseline["seasonal"].mean())) / scale
        ref_mae = float((baseline["trips"] - baseline[active_column]).abs().mean())
        mae = float((window["trips"] - window[active_column]).abs().mean())
        results.append({
            "period": str(month), "zone": int(zone), "drift_score": round(drift, 3),
            "drift_alert": drift >= 1, "reference_mae": round(ref_mae, 2), "mae": round(mae, 2),
            "performance_alert": mae > ref_mae + max(0.25 * ref_mae, 5),
            "observations": len(window),
        })
    return results
