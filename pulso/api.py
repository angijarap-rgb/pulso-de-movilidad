import json
import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from threadpoolctl import threadpool_limits

from pulso.features import FEATURES, HORIZON, make_features


def create_app(root=None, kind=None):
    root = Path(root or os.getenv("PULSO_RUNS", "runs"))
    kind = kind or os.getenv("PULSO_SOURCE", "tlc")

    @asynccontextmanager
    async def lifespan(app):
        pointer = root / f"active-{kind}.json"
        app.state.bundle = None
        if pointer.is_file():
            run_id = json.loads(pointer.read_text(encoding="utf-8"))["run_id"]
            folder = root / "versions" / run_id
            report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
            history = pd.read_csv(folder / "history.csv", parse_dates=["day"])
            features = make_features(history, future_days=98).set_index(["day", "zone"], drop=False)
            model = joblib.load(folder / "challenger.joblib") if report["decision"]["active"] == "challenger" else None
            app.state.bundle = report, features, model
        yield

    app = FastAPI(title="Pulso de Movilidad", version="1.0.0", lifespan=lifespan)

    @app.get("/health")
    def health(request: Request):
        if request.app.state.bundle is None:
            raise HTTPException(503, "Ejecuta el pipeline antes de servir predicciones")
        report, _, _ = request.app.state.bundle
        return {"status": "ready", "run_id": report["run_id"], "source": report["kind"]}

    @app.get("/v1/forecast")
    def forecast(day: date, zone: int, request: Request):
        if request.app.state.bundle is None:
            raise HTTPException(503, "Ejecuta el pipeline antes de servir predicciones")
        report, features, model = request.app.state.bundle
        if str(zone) not in report["zones"]:
            raise HTTPException(404, "Zona fuera del alcance")
        earliest = date.fromisoformat(report["windows"]["test"][0])
        latest = features.index.get_level_values("day").max().date()
        if not earliest <= day <= latest:
            raise HTTPException(422, f"Fecha fuera de la ventana disponible: {earliest} a {latest}")
        values = features.loc[[(pd.Timestamp(day), zone)], FEATURES]
        if model is None:
            count = values["seasonal"].iloc[0]
        else:
            with threadpool_limits(limits=2):
                count = model.predict(values)[0]
        return {
            "date": day,
            "forecast_origin": day - timedelta(days=HORIZON),
            "zone": zone,
            "predicted_trips": round(float(count), 2),
            "active_model": report["decision"]["active"],
            "run_id": report["run_id"],
            "source": report["kind"],
        }

    return app


app = create_app()
