import json
import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from threadpoolctl import threadpool_limits

from pulso.features import FEATURES, HORIZON, make_features


def create_app(root=None, kind=None):
    root = Path(root or os.getenv("PULSO_RUNS", "runs"))
    kind = kind or os.getenv("PULSO_SOURCE", "metro-lima")

    @asynccontextmanager
    async def lifespan(app):
        pointer = root / f"active-{kind}.json"
        app.state.bundle = None
        if pointer.is_file():
            run_id = json.loads(pointer.read_text(encoding="utf-8"))["run_id"]
            folder = root / "versions" / run_id
            report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
            history = pd.read_csv(folder / "history.csv", parse_dates=["day"])
            features = make_features(history, future_months=1).set_index(["day", "zone"], drop=False)
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

    @app.get("/v1/stations")
    def stations(request: Request):
        if request.app.state.bundle is None:
            raise HTTPException(503, "Ejecuta el pipeline antes de consultar estaciones")
        report, _, _ = request.app.state.bundle
        return report["zones"]

    @app.get("/v1/forecast")
    def forecast(month: date, station: int, request: Request):
        if request.app.state.bundle is None:
            raise HTTPException(503, "Ejecuta el pipeline antes de servir predicciones")
        report, features, model = request.app.state.bundle
        if str(station) not in report["zones"]:
            raise HTTPException(404, "Estación fuera del alcance")
        earliest = date.fromisoformat(report["windows"]["test"][0])
        latest = features.index.get_level_values("day").max().date()
        if month.day != 1 or not earliest <= month <= latest:
            raise HTTPException(422, f"Usa el primer día de un mes entre {earliest} a {latest}")
        values = features.loc[[(pd.Timestamp(month), station)], FEATURES]
        if model is None:
            count = values["lag_12"].iloc[0]
        else:
            with threadpool_limits(limits=2):
                count = model.predict(values)[0]
        return {
            "month": month.strftime("%Y-%m"),
            "forecast_origin": (pd.Timestamp(month) - pd.DateOffset(months=HORIZON)).strftime("%Y-%m"),
            "station": report["zones"][str(station)],
            "predicted_passengers": round(float(count), 2),
            "active_model": report["decision"]["active"],
            "run_id": report["run_id"],
            "source": report["kind"],
        }

    return app


app = create_app()
