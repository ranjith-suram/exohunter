"""Periodic transit search with Box Least Squares (BLS)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
from astropy.timeseries import BoxLeastSquares

DEFAULT_DURATIONS_DAYS = (0.04, 0.06, 0.08, 0.12, 0.16, 0.25)


@dataclass
class BLSResult:
    period: float
    t0: float
    duration: float
    depth: float
    depth_err: float
    depth_snr: float
    sde: float
    n_transits: int
    depth_odd: float
    depth_odd_err: float
    depth_even: float
    depth_even_err: float
    periods: np.ndarray = field(repr=False)
    power: np.ndarray = field(repr=False)

    def summary(self) -> dict:
        d = asdict(self)
        d.pop("periods")
        d.pop("power")
        return d


def robust_std(x: np.ndarray) -> float:
    return float(1.4826 * np.nanmedian(np.abs(x - np.nanmedian(x))))


def phase_fold(time: np.ndarray, period: float, t0: float) -> np.ndarray:
    """Time from nearest transit centre, in days, in [-P/2, P/2)."""
    return (time - t0 + 0.5 * period) % period - 0.5 * period


def bls_search(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray | None = None,
    min_period: float = 0.5,
    max_period: float | None = None,
    durations: tuple[float, ...] = DEFAULT_DURATIONS_DAYS,
    max_grid: int = 200_000,
) -> BLSResult:
    """Find the strongest box-shaped periodic dip.

    ``max_period`` defaults to half the baseline so at least two transits fit.
    The period grid is thinned if it would exceed ``max_grid`` points.
    """
    time = np.asarray(time, float)
    flux = np.asarray(flux, float)
    good = np.isfinite(time) & np.isfinite(flux)
    if flux_err is not None:
        flux_err = np.asarray(flux_err, float)
        good &= np.isfinite(flux_err) & (flux_err > 0)
    t, y = time[good], flux[good]
    if t.size < 100:
        raise ValueError(f"Too few points for a transit search ({t.size})")
    dy = flux_err[good] if flux_err is not None else np.full_like(y, robust_std(y))

    baseline = t.max() - t.min()
    max_period = max_period or baseline / 2
    if max_period <= min_period:
        raise ValueError(f"Baseline {baseline:.1f} d too short for min_period {min_period}")
    durs = [d for d in durations if d < min_period]

    bls = BoxLeastSquares(t, y, dy)
    periods = bls.autoperiod(durs, minimum_period=min_period, maximum_period=max_period)
    if periods.size > max_grid:
        factor = periods.size / max_grid
        periods = bls.autoperiod(
            durs, minimum_period=min_period, maximum_period=max_period, frequency_factor=factor
        )

    pg = bls.power(periods, durs, objective="likelihood")
    power = np.asarray(pg.power, float)
    i = int(np.nanargmax(power))
    sde = float((power[i] - np.nanmean(power)) / np.nanstd(power))
    period, t0, dur = float(pg.period[i]), float(pg.transit_time[i]), float(pg.duration[i])

    stats = bls.compute_stats(period, dur, t0)
    depth, depth_err = (float(v) for v in stats["depth"])
    odd, odd_err = (float(v) for v in stats["depth_odd"])
    even, even_err = (float(v) for v in stats["depth_even"])
    n_transits = int(np.sum(np.asarray(stats["per_transit_count"]) > 0))

    return BLSResult(
        period=period,
        t0=t0,
        duration=dur,
        depth=depth,
        depth_err=depth_err,
        depth_snr=depth / depth_err if depth_err > 0 else 0.0,
        sde=sde,
        n_transits=n_transits,
        depth_odd=odd,
        depth_odd_err=odd_err,
        depth_even=even,
        depth_even_err=even_err,
        periods=np.asarray(periods, float),
        power=power,
    )
