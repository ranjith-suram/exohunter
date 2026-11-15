"""End-to-end analysis of one star: fetch -> detrend -> search -> vet -> cross-match."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from .config import Settings
from .crossmatch import crossmatch
from .detrend import bin_timeseries, clip_upper_outliers, flatten_lightcurve
from .search import bls_search
from .sources import tess
from .vet import Thresholds, vet


@dataclass
class TargetResult:
    row: dict
    lightcurve: pd.DataFrame
    periodogram: pd.DataFrame


def analyze_arrays(
    tic_id: int,
    time: np.ndarray,
    raw: np.ndarray,
    flat: np.ndarray,
    sectors: list[int],
    toi: pd.DataFrame | None = None,
    bin_minutes: float = 10.0,
    thresholds: Thresholds | None = None,
) -> TargetResult:
    """Everything after download. Pure function of arrays, so it is unit-testable."""
    flat = clip_upper_outliers(flat)
    tb, (fb, rb), eb = bin_timeseries(time, flat, raw, bin_days=bin_minutes / 1440)

    res = bls_search(tb, fb, eb)
    report = vet(res, tb, fb, thresholds)
    match = crossmatch(tic_id, res.period, toi)

    row = {
        "tic_id": tic_id,
        "sectors": ",".join(map(str, sectors)),
        "analyzed_at": datetime.now(UTC).replace(tzinfo=None),
        "n_points": int(tb.size),
        **{k: res.summary()[k] for k in ("period", "t0", "duration", "depth", "depth_snr", "sde")},
        "n_transits": res.n_transits,
        "odd_even_sigma": report.odd_even_sigma,
        "secondary_sigma": report.secondary_sigma,
        "status": report.status,
        "flags": ",".join(report.flags),
        "match_label": match.label,
        "toi": match.toi,
        "toi_disposition": match.disposition,
        "known_period": match.known_period,
    }
    lc = pd.DataFrame({"time": tb, "flux": fb, "flux_err": eb, "flux_raw": rb})
    # Keep periodogram files small: every point is not needed to draw it.
    step = max(1, res.periods.size // 20_000)
    pg = pd.DataFrame({"period": res.periods[::step], "power": res.power[::step]})
    return TargetResult(row, lc, pg)


def analyze_target(
    tic_id: int,
    settings: Settings,
    sectors: list[int] | None = None,
    toi: pd.DataFrame | None = None,
) -> TargetResult:
    lc, found = tess.download_lightcurve(tic_id, sectors, cache_dir=settings.cache_dir)
    time, raw, flat, _ = flatten_lightcurve(lc)
    return analyze_arrays(tic_id, time, raw, flat, found, toi)
