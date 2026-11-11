import json

import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from pulso.activate import activate
from pulso.api import create_app
from pulso.data import ZONES, load_data, read_month
from pulso.evaluation import promotion
from pulso.features import FEATURES, make_features
from pulso.pipeline import run, time_split


def test_future_observations_do_not_change_features():
    history, _ = load_data("2023-07", None, synthetic=True)
    target = pd.Timestamp("2024-09-01")
    available = history[history.day < target - pd.Timedelta(days=90)]
    full = make_features(history).query("day == @target")[FEATURES].reset_index(drop=True)
    restricted = make_features(available, future_days=91).query("day == @target")[FEATURES].reset_index(drop=True)
    pd.testing.assert_frame_equal(full, restricted, check_dtype=False)


def test_label_gaps_account_for_monthly_delay():
    history, _ = load_data("2023-07", None, synthetic=True)
    train, validation, test = time_split(make_features(history), "2023-07")
    for previous, following in ((train, validation), (validation, test)):
        next_month = (previous.day.max().to_period("M") + 1).start_time
        assert next_month + pd.Timedelta(days=60) <= following.day.min() - pd.Timedelta(days=1)


def test_promotion_checks_zone_regression():
    baseline = {"mae": 100, "zones": {"48": 100, "79": 100}}
    assert promotion(baseline, {"mae": 96, "zones": {"48": 86, "79": 106}})["active"] == "challenger"
    assert promotion(baseline, {"mae": 94, "zones": {"48": 70, "79": 118}})["active"] == "baseline"
    assert promotion(baseline, {"mae": 99, "zones": {"48": 99, "79": 99}})["active"] == "baseline"


def test_parquet_ingestion_rejects_missing_coverage(tmp_path):
    dates = pd.date_range("2024-01-01", "2024-01-31")
    trips = pd.MultiIndex.from_product([dates, ZONES], names=["tpep_pickup_datetime", "PULocationID"]).to_frame(index=False)
    path = tmp_path / "sample.parquet"
    with duckdb.connect() as connection:
        connection.from_df(trips).write_parquet(str(path))
        records, quality = read_month(connection, path, pd.Period("2024-01"))
        assert len(records) == quality["raw_rows"] == len(trips)
        path.unlink()
        connection.from_df(trips.iloc[1:]).write_parquet(str(path))
        with pytest.raises(ValueError, match="faltan observaciones"):
            read_month(connection, path, pd.Period("2024-01"))


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    root = tmp_path_factory.mktemp("runs")
    report = run("2023-07", None, root, synthetic=True, tracking=True)
    return root, report


def test_api_matches_report(trained):
    root, report = trained
    day, zone, _, baseline, challenger = report["predictions"][0]
    with TestClient(create_app(root, "synthetic")) as client:
        assert client.get("/health").json()["run_id"] == report["run_id"]
        response = client.get("/v1/forecast", params={"day": day, "zone": zone})
        assert response.status_code == 200
        expected = challenger if report["decision"]["active"] == "challenger" else baseline
        assert response.json()["predicted_trips"] == expected
        assert client.get("/v1/forecast", params={"day": day, "zone": -1}).status_code == 404
        assert client.get("/v1/forecast", params={"day": "2020-01-01", "zone": zone}).status_code == 422


def test_registry_and_rollback(trained):
    from mlflow import MlflowClient

    from pulso.registry import registry_uri

    root, report = trained
    activate(root, report["run_id"])
    assert json.loads((root / "active-synthetic.json").read_text())["run_id"] == report["run_id"]
    registry = report["registry"]
    client = MlflowClient(registry_uri=registry_uri(root))
    champion = client.get_model_version_by_alias(registry["model_name"], "champion")
    assert champion.version == registry["versions"][report["decision"]["active"]]


def test_api_before_training(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/health").status_code == 503
