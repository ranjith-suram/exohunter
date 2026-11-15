"""Compare detections with known TESS Objects of Interest (TOIs)."""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

TAP_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
TOI_QUERY = "select toi, tid, tfopwg_disp, pl_orbper, pl_trandurh, pl_trandep from toi"
HARMONICS = (1.0, 2.0, 0.5, 3.0, 1 / 3)


@dataclass
class Match:
    label: str  # known_toi | new_signal_on_toi_star | no_known_match | not_checked
    toi: str | None = None
    disposition: str | None = None
    known_period: float | None = None
    harmonic: float | None = None


def fetch_toi_table(cache_dir: Path, max_age_days: float = 7, force: bool = False) -> pd.DataFrame:
    """Download the NASA Exoplanet Archive TOI table, cached as Parquet."""
    path = cache_dir / "toi.parquet"
    if path.exists() and not force and (time.time() - path.stat().st_mtime) < max_age_days * 86400:
        return pd.read_parquet(path)
    resp = requests.get(TAP_URL, params={"query": TOI_QUERY, "format": "csv"}, timeout=120)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.to_parquet(path, index=False)
    return df


def period_harmonic(period: float, known: float, tol: float = 0.01) -> float | None:
    """Return h if period ~= known * h for a small-integer harmonic, else None."""
    for h in HARMONICS:
        if abs(period - known * h) / (known * h) < tol:
            return h
    return None


def crossmatch(tic_id: int, period: float, toi: pd.DataFrame | None) -> Match:
    if toi is None:
        return Match("not_checked")
    rows = toi[toi["tid"] == tic_id]
    if rows.empty:
        return Match("no_known_match")
    for row in rows.itertuples():
        if pd.notna(row.pl_orbper) and (h := period_harmonic(period, row.pl_orbper)) is not None:
            return Match(
                "known_toi",
                toi=str(row.toi),
                disposition=None if pd.isna(row.tfopwg_disp) else str(row.tfopwg_disp),
                known_period=float(row.pl_orbper),
                harmonic=h,
            )
    return Match("new_signal_on_toi_star", toi=", ".join(str(t) for t in rows["toi"]))
