import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from pulso.activate import activate
from pulso.api import create_app
from pulso.data import DATASET, load_data
from pulso.evaluation import promotion
from pulso.features import FEATURES, make_features
from pulso.pipeline import run, time_split


def test_mtc_coverage():
    history, _, stations = load_data()
    assert len(stations) == 26
    assert len(history) == 1248
    assert history.groupby("day")["trips"].sum().loc["2025-12-01"] == 18457806


@pytest.mark.parametrize("corruption", ["duplicate", "missing"])
def test_invalid_monthly_coverage(tmp_path, corruption):
    frame = pd.read_csv(DATASET)
    frame = pd.concat([frame, frame.head(1)]) if corruption == "duplicate" else frame.iloc[1:]
    path = tmp_path / "bad.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="repetidas|Faltan"):
        load_data(path)


def test_features_respect_reporting_gap():
    history, _, _ = load_data()
    month = pd.Timestamp("2025-01-01")
    available = history[history.day <= "2024-11-01"]
    complete = make_features(history).query("day == @month")[FEATURES].reset_index(drop=True)
    restricted = make_features(available, future_months=2).query("day == @month")[FEATURES].reset_index(drop=True)
    pd.testing.assert_frame_equal(complete, restricted)


def test_validation_and_test_are_separate():
    history, _, _ = load_data()
    train, validation, test = time_split(make_features(history))
    assert train.day.max() == pd.Timestamp("2023-11-01")
    assert validation.day.min() == pd.Timestamp("2024-01-01")
    assert validation.day.max() == pd.Timestamp("2024-11-01")
    assert test.day.min() == pd.Timestamp("2025-01-01")
    assert test.day.max() == pd.Timestamp("2025-12-01")


def test_promotion_checks_station_regression():
    baseline = {"mae": 100, "zones": {"1": 100, "2": 100}}
    assert promotion(baseline, {"mae": 96, "zones": {"1": 86, "2": 106}})["active"] == "challenger"
    assert promotion(baseline, {"mae": 94, "zones": {"1": 70, "2": 118}})["active"] == "baseline"


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    root = tmp_path_factory.mktemp("runs")
    return root, run(root=root)


def test_forecast_matches_report(trained):
    root, report = trained
    month, station, _, baseline, challenger = report["predictions"][0]
    with TestClient(create_app(root)) as client:
        assert client.get("/health").json()["run_id"] == report["run_id"]
        assert len(client.get("/v1/stations").json()) == 26
        response = client.get("/v1/forecast", params={"month": f"{month}-01", "station": station})
        assert response.status_code == 200
        expected = challenger if report["decision"]["active"] == "challenger" else baseline
        assert response.json()["predicted_passengers"] == expected
        assert client.get("/v1/forecast", params={"month": "2025-01-01", "station": -1}).status_code == 404
        assert client.get("/v1/forecast", params={"month": "2025-01-02", "station": station}).status_code == 422
        assert client.get("/v1/forecast", params={"month": "2026-01-01", "station": station}).status_code == 200


def test_registry_and_reactivation(trained):
    from mlflow import MlflowClient

    from pulso.registry import registry_uri

    root, report = trained
    activate(root, report["run_id"])
    assert json.loads((root / "active-metro-lima.json").read_text())["run_id"] == report["run_id"]
    registry = report["registry"]
    client = MlflowClient(registry_uri=registry_uri(root))
    champion = client.get_model_version_by_alias(registry["model_name"], "champion")
    assert champion.version == registry["versions"][report["decision"]["active"]]


def test_api_before_training(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/health").status_code == 503
