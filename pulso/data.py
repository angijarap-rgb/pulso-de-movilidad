import hashlib
import os
from pathlib import Path
from urllib.request import urlopen

import duckdb
import numpy as np
import pandas as pd

ZONES = {
    48: "Clinton East",
    79: "East Village",
    132: "JFK Airport",
    138: "LaGuardia Airport",
    161: "Midtown Center",
    236: "Upper East Side North",
}
SOURCE = "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page"
BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(month, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{month}.parquet"
    url = f"{BASE_URL}/yellow_tripdata_{month}.parquet"
    if not path.exists():
        partial = path.with_suffix(".part")
        try:
            with urlopen(url, timeout=90) as response, partial.open("wb") as stream:
                while chunk := response.read(1024 * 1024):
                    stream.write(chunk)
            os.replace(partial, path)
        finally:
            partial.unlink(missing_ok=True)
    return path, url


def read_month(connection, path, month):
    start = month.start_time.date()
    stop = (month + 1).start_time.date()
    total, inside = connection.execute(
        """
        SELECT count(*), count(*) FILTER (
            WHERE tpep_pickup_datetime >= ? AND tpep_pickup_datetime < ?
        )
        FROM read_parquet(?)
        """,
        [start, stop, str(path)],
    ).fetchone()
    if not total or inside / total < 0.99:
        raise ValueError(f"{month}: más de 1 % de fechas fuera del mes o nulas")

    rows = connection.execute(
        """
        SELECT CAST(tpep_pickup_datetime AS DATE) AS day,
               CAST(PULocationID AS INTEGER) AS zone, count(*) AS trips
        FROM read_parquet(?)
        WHERE tpep_pickup_datetime >= ? AND tpep_pickup_datetime < ?
          AND PULocationID IN (SELECT unnest(?))
        GROUP BY 1, 2
        """,
        [str(path), start, stop, list(ZONES)],
    ).df()
    expected_days = pd.date_range(start, stop, inclusive="left")
    expected = pd.MultiIndex.from_product([expected_days, ZONES], names=["day", "zone"])
    indexed = rows.set_index(["day", "zone"]).reindex(expected)
    if indexed["trips"].isna().any():
        raise ValueError(f"{month}: faltan observaciones para una zona y día")
    return indexed.reset_index(), {"raw_rows": total, "excluded_dates": total - inside}


def load_data(start, directory, synthetic=False):
    months = pd.period_range(start=start, periods=16, freq="M")
    if synthetic:
        days = pd.date_range(months[0].start_time, (months[-1] + 1).start_time, inclusive="left")
        rng = np.random.default_rng(21)
        records = []
        for offset, day in enumerate(days):
            for index, zone in enumerate(ZONES):
                level = 160 + index * 65 + (32 if day.weekday() < 5 else -28)
                change = 105 if index == 0 and offset > 425 else 0
                trips = int(rng.poisson(level + change + 15 * np.sin(offset / 21)))
                records.append((day, zone, trips))
        return pd.DataFrame(records, columns=["day", "zone", "trips"]), []
    batches, manifest = [], []
    with duckdb.connect() as connection:
        connection.execute("SET threads=2")
        for month in months:
            path, url = download(month, Path(directory))
            rows, quality = read_month(connection, path, month)
            batches.append(rows)
            manifest.append({"month": str(month), "url": url, "sha256": file_hash(path), **quality})
    return pd.concat(batches, ignore_index=True), manifest
