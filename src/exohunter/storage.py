"""Results in DuckDB, light curves and periodograms in Parquet.

Connections are opened per call so the Streamlit app and the CLI can share the
database file without holding a long-lived lock.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import duckdb
import pandas as pd

from .config import Settings

COLUMNS = {
    "tic_id": "BIGINT PRIMARY KEY",
    "sectors": "VARCHAR",
    "analyzed_at": "TIMESTAMP",
    "n_points": "INTEGER",
    "period": "DOUBLE",
    "t0": "DOUBLE",
    "duration": "DOUBLE",
    "depth": "DOUBLE",
    "depth_snr": "DOUBLE",
    "sde": "DOUBLE",
    "n_transits": "INTEGER",
    "odd_even_sigma": "DOUBLE",
    "secondary_sigma": "DOUBLE",
    "status": "VARCHAR",
    "flags": "VARCHAR",
    "match_label": "VARCHAR",
    "toi": "VARCHAR",
    "toi_disposition": "VARCHAR",
    "known_period": "DOUBLE",
}


class Store:
    def __init__(self, settings: Settings):
        self.settings = settings
        with self._conn() as con:
            cols = ", ".join(f"{k} {v}" for k, v in COLUMNS.items())
            con.execute(f"CREATE TABLE IF NOT EXISTS results ({cols})")

    @contextmanager
    def _conn(self, read_only: bool = False):
        con = duckdb.connect(str(self.settings.db_path), read_only=read_only)
        try:
            yield con
        finally:
            con.close()

    def save_result(self, row: dict) -> None:
        names = list(COLUMNS)
        sql = (
            f"INSERT OR REPLACE INTO results ({', '.join(names)}) "
            f"VALUES ({', '.join('?' for _ in names)})"
        )
        with self._conn() as con:
            con.execute(sql, [row.get(n) for n in names])

    def results(
        self,
        status: list[str] | None = None,
        labels: list[str] | None = None,
        min_sde: float | None = None,
    ) -> pd.DataFrame:
        where, params = [], []
        if status:
            where.append(f"status IN ({', '.join('?' for _ in status)})")
            params += status
        if labels:
            where.append(f"match_label IN ({', '.join('?' for _ in labels)})")
            params += labels
        if min_sde is not None:
            where.append("sde >= ?")
            params.append(min_sde)
        sql = "SELECT * FROM results"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY sde DESC"
        with self._conn(read_only=True) as con:
            return con.execute(sql, params).df()

    def _path(self, tic_id: int, kind: str) -> Path:
        return self.settings.lightcurve_dir / f"TIC{tic_id}_{kind}.parquet"

    def save_series(self, tic_id: int, kind: str, df: pd.DataFrame) -> None:
        df.to_parquet(self._path(tic_id, kind), index=False)

    def load_series(self, tic_id: int, kind: str) -> pd.DataFrame | None:
        p = self._path(tic_id, kind)
        return pd.read_parquet(p) if p.exists() else None
