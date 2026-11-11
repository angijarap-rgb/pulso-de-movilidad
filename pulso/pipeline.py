import argparse
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

from pulso.data import DATASET, SOURCE, load_data
from pulso.evaluation import monitor, promotion, scores
from pulso.features import FEATURES, make_features

LOGGER = logging.getLogger("pulso")


def write_json(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(contents, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def time_split(frame):
    last = frame["day"].max().to_period("M")
    test_start = (last - 11).start_time
    validation_start = (last - 23).start_time
    train = frame[frame["day"] < validation_start - pd.DateOffset(months=1)].copy()
    validation = frame[frame["day"].between(
        validation_start, test_start - pd.DateOffset(months=1), inclusive="left",
    )].copy()
    test = frame[frame["day"] >= test_start].copy()
    if any(group.empty or group["trips"].isna().any() for group in (train, validation, test)):
        raise ValueError("El historial no cubre entrenamiento, validación y prueba")
    return train, validation, test


def run(data=DATASET, root="runs", tracking=True, publish=None):
    root = Path(root)
    kind = "metro-lima"
    history, manifest, zones = load_data(data)
    start = history["day"].min().strftime("%Y-%m")
    history = history.sort_values(["day", "zone"]).reset_index(drop=True)
    dataset_hash = hashlib.sha256(history.to_csv(index=False).encode()).hexdigest()
    LOGGER.info("source=%s rows=%d sha256=%s", kind, len(history), dataset_hash)
    train, validation, test = time_split(make_features(history))
    model = HistGradientBoostingRegressor(
        loss="poisson", max_iter=120, max_leaf_nodes=15, min_samples_leaf=12, random_state=21,
    )
    with threadpool_limits(limits=2):
        model.fit(train[FEATURES], train["trips"])
        for frame in (validation, test):
            frame["baseline"] = frame["seasonal"]
            frame["challenger"] = model.predict(frame[FEATURES])
    metrics = {
        split: {candidate: scores(frame, frame[candidate].to_numpy()) for candidate in ("baseline", "challenger")}
        for split, frame in (("validation", validation), ("test", test))
    }
    decision = promotion(**metrics["validation"])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output = root / "versions" / run_id
    output.mkdir(parents=True)
    report = {
        "run_id": run_id,
        "kind": kind,
        "start": start,
        "source": SOURCE,
        "dataset_sha256": dataset_hash,
        "sources": manifest,
        "zones": zones,
        "windows": {
            name: [group["day"].min().date().isoformat(), group["day"].max().date().isoformat()]
            for name, group in (("train", train), ("validation", validation), ("test", test))
        },
        "metrics": metrics,
        "decision": decision,
        "monitoring": monitor(validation, test, decision["active"]),
        "predictions": [
            [row.day.strftime("%Y-%m"), int(row.zone), int(row.trips), round(row.baseline, 2), round(row.challenger, 2)]
            for row in test.itertuples(index=False)
        ],
    }
    joblib.dump(model, output / "challenger.joblib")
    history.to_csv(output / "history.csv", index=False)
    write_json(output / "report.json", report)
    if tracking:
        from pulso.registry import register

        report["registry"] = register(root, report, model, train[FEATURES].head(5), output / "report.json")
        write_json(output / "report.json", report)
    if publish:
        write_json(Path(publish), report)
    write_json(root / f"active-{kind}.json", {"run_id": run_id})
    LOGGER.info("run=%s active=%s test_mae=%.2f", run_id, decision["active"], metrics["test"][decision["active"]]["mae"])
    return report


def main():
    parser = argparse.ArgumentParser(description="Entrena y evalúa el pronóstico mensual")
    parser.add_argument("--data", type=Path, default=DATASET)
    parser.add_argument("--root", default="runs")
    parser.add_argument("--no-tracking", action="store_true")
    parser.add_argument("--publish", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(args.data, args.root, not args.no_tracking, args.publish)


if __name__ == "__main__":
    main()
