"""Light-curve cleaning: remove slow stellar/instrumental trends, keep short dips."""

from __future__ import annotations

import numpy as np


def to_array(q) -> np.ndarray:
    """Convert an astropy (Masked)Quantity / Time-like column to a float array, masks -> NaN."""
    mask = getattr(q, "mask", None)
    v = getattr(q, "unmasked", q)
    v = np.asarray(getattr(v, "value", v), dtype=float)
    if mask is not None and np.ndim(mask):
        v = np.where(np.asarray(mask), np.nan, v)
    return v


def flatten_lightcurve(lc, window_days: float = 1.0):
    """Return (time, raw_flux, flat_flux, flux_err) arrays.

    A Savitzky-Golay filter ~1 day wide removes rotation and systematics but
    leaves transits (usually < 6 h) mostly intact.
    """
    lc = lc.remove_nans().normalize()
    time = to_array(lc.time)
    dt = np.nanmedian(np.diff(time))
    window = max(int(round(window_days / dt)) // 2 * 2 + 1, 5)  # odd, in cadences
    flat = lc.flatten(window_length=window, polyorder=2, break_tolerance=10, sigma=3)
    return time, to_array(lc.flux), to_array(flat.flux), to_array(flat.flux_err)


def clip_upper_outliers(flux: np.ndarray, sigma: float = 4.0) -> np.ndarray:
    """Mask (NaN) bright outliers such as flares. Dips are never clipped."""
    med = np.nanmedian(flux)
    mad = 1.4826 * np.nanmedian(np.abs(flux - med))
    out = flux.copy()
    out[flux > med + sigma * mad] = np.nan
    return out


def bin_timeseries(
    time: np.ndarray, *fluxes: np.ndarray, bin_days: float
) -> tuple[np.ndarray, list[np.ndarray], np.ndarray]:
    """Average several flux arrays onto a common time grid.

    Returns (binned_time, [binned_flux, ...], err_of_first_flux).
    """
    good = np.isfinite(time)
    for f in fluxes:
        good &= np.isfinite(f)
    t = time[good]
    idx = np.floor((t - t.min()) / bin_days).astype(np.int64)
    _, inv, counts = np.unique(idx, return_inverse=True, return_counts=True)
    tb = np.bincount(inv, weights=t) / counts
    binned = [np.bincount(inv, weights=f[good]) / counts for f in fluxes]

    f0 = fluxes[0][good]
    var = np.bincount(inv, weights=f0**2) / counts - binned[0] ** 2
    err = np.sqrt(np.clip(var, 0, None) / counts)
    bad = (counts < 2) | (err == 0)
    if np.any(~bad):
        err[bad] = np.median(err[~bad])
    return tb, binned, err
