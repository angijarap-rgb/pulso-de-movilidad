import mlflow
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.base import BaseEstimator, RegressorMixin


class SeasonalRegressor(RegressorMixin, BaseEstimator):
    def fit(self, features, target=None):
        self.feature_names_in_ = features.columns.to_numpy()
        return self

    def predict(self, features):
        return features["seasonal"].to_numpy()


def registry_uri(root):
    return "sqlite:///" + (root / "mlflow.db").resolve().as_posix()


def set_champion(root, registry, active):
    client = MlflowClient(registry_uri=registry_uri(root))
    client.set_registered_model_alias(registry["model_name"], "champion", registry["versions"][active])


def register(root, report, model, example, report_path):
    uri = registry_uri(root)
    mlflow.set_tracking_uri(uri)
    mlflow.set_registry_uri(uri)
    name = "pulso-" + report["kind"]
    mlflow.set_experiment(name)
    with mlflow.start_run(run_name=report["run_id"]) as run:
        mlflow.log_params({
            "source": report["kind"],
            "active": report["decision"]["active"],
            "start": report["start"],
            "dataset_sha256": report["dataset_sha256"],
        })
        for split, candidates in report["metrics"].items():
            for candidate, values in candidates.items():
                mlflow.log_metric(f"{split}_{candidate}_mae", values["mae"])
                if values["wape"] is not None:
                    mlflow.log_metric(f"{split}_{candidate}_wape", values["wape"])
        mlflow.log_artifact(str(report_path))
        client = MlflowClient()
        versions = {}
        for candidate, estimator in (("baseline", SeasonalRegressor().fit(example)), ("challenger", model)):
            artifact = mlflow.sklearn.log_model(
                estimator,
                name=candidate,
                signature=infer_signature(example, estimator.predict(example)),
                registered_model_name=name,
                serialization_format="cloudpickle",
                code_paths=["pulso"] if candidate == "baseline" else None,
            )
            version = artifact.registered_model_version
            client.set_model_version_tag(name, version, "candidate", candidate)
            versions[candidate] = version
        client.set_registered_model_alias(name, "challenger", versions["challenger"])
        registry = {"experiment_run": run.info.run_id, "model_name": name, "versions": versions}
        set_champion(root, registry, report["decision"]["active"])
        return registry
