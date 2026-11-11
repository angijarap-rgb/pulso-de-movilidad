import hashlib
from pathlib import Path

import pandas as pd

SOURCE = "https://www.gob.pe/institucion/mtc/informes-publicaciones/345063-estadistica-servicios-de-transporte-terrestre-por-ferrovia-servicio-de-pasajeros"
DATASET = Path(__file__).resolve().parent.parent / "datasets" / "metro-lima.csv"


def load_data(path=DATASET):
    path = Path(path)
    raw = pd.read_csv(path, dtype={"mes": "string", "estacion": "string", "pasajeros": "Int64"})
    if raw.empty or raw.isna().any().any():
        raise ValueError("El CSV está vacío o contiene valores faltantes")
    raw["estacion"] = raw["estacion"].str.strip()
    if (raw["estacion"] == "").any() or (raw["pasajeros"] < 0).any():
        raise ValueError("Hay estaciones vacías o conteos negativos")
    if not raw["mes"].str.fullmatch(r"\d{4}-(0[1-9]|1[0-2])").all():
        raise ValueError("Los meses deben tener formato AAAA-MM")
    if raw.duplicated(["mes", "estacion"]).any():
        raise ValueError("Hay estaciones repetidas en un mismo mes")
    station_ids = {station: index for index, station in enumerate(sorted(raw["estacion"].unique()), 1)}
    raw["day"] = pd.to_datetime(raw["mes"], format="%Y-%m")
    raw["zone"] = raw["estacion"].map(station_ids).astype(int)
    months = pd.date_range(raw["day"].min(), raw["day"].max(), freq="MS")
    if len(raw) != len(months) * len(station_ids):
        raise ValueError("Faltan meses o estaciones en el CSV")
    history = raw.rename(columns={"pasajeros": "trips"})[["day", "zone", "trips"]]
    zones = {value: key for key, value in station_ids.items()}
    manifest = [{"url": SOURCE, "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": len(raw)}]
    return history, manifest, zones
