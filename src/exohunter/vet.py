"""Automated vetting: cheap tests that reject common false positives."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .search import BLSResult, phase_fold, robust_std

TESS_ORBIT_DAYS = 13.7  # spacecraft orbit; momentum dumps and scattered light repeat on it


@dataclass(frozen=True)
class Thresholds:
    min_sde: float = 7.0
    min_snr: float = 7.0
    min_transits: int = 2
    max_odd_even_sigma: float = 3.0
    # Formal BLS errors ignore red noise, so on bright stars a few-% difference can look
    # "significant". Real binaries folded at half their period differ far more.
    max_odd_even_frac: float = 0.15
    max_secondary_sigma: float = 3.0
    deep_transit: float = 0.03  # > 3% depth is often a binary star (or a giant around an M dwarf)


@dataclass
class VetReport:
    status: str  # candidate | weak | likely_eb | suspect_systematic
    flags: list[str] = field(default_factory=list)
    odd_even_sigma: float = 0.0
    secondary_depth: float = 0.0
    secondary_sigma: float = 0.0


def odd_even_sigma(r: BLSResult) -> float:
    """Eclipsing binaries at 2x the true period show alternating depths."""
    err = np.hypot(r.depth_odd_err, r.depth_even_err)
    return float(abs(r.depth_odd - r.depth_even) / err) if err > 0 else 0.0


def secondary_eclipse(
    time: np.ndarray, flux: np.ndarray, period: float, t0: float, duration: float
) -> tuple[float, float]:
    """Depth and significance of a dip at phase 0.5 (planets rarely show one in TESS)."""
    good = np.isfinite(time) & np.isfinite(flux)
    time, flux = time[good], flux[good]
    sec = np.abs(phase_fold(time, period, t0 + period / 2)) < duration / 2
    out = (np.abs(phase_fold(time, period, t0)) > duration) & (
        np.abs(phase_fold(time, period, t0 + period / 2)) > duration
    )
    if sec.sum() < 3 or out.sum() < 10:
        return 0.0, 0.0
    depth = float(np.median(flux[out]) - np.mean(flux[sec]))
    err = robust_std(flux[out]) / np.sqrt(sec.sum())
    return depth, (depth / err if err > 0 else 0.0)


def near_tess_orbit(period: float, tol: float = 0.02) -> bool:
    return any(abs(period - TESS_ORBIT_DAYS * m) / (TESS_ORBIT_DAYS * m) < tol for m in (0.5, 1))


def vet(
    r: BLSResult, time: np.ndarray, flux: np.ndarray, th: Thresholds | None = None
) -> VetReport:
    th = th or Thresholds()
    flags: list[str] = []
    if r.sde < th.min_sde:
        flags.append("low_sde")
    if r.depth_snr < th.min_snr:
        flags.append("low_snr")
    if r.n_transits < th.min_transits:
        flags.append("too_few_transits")

    oe = odd_even_sigma(r)
    oe_frac = abs(r.depth_odd - r.depth_even) / max(r.depth, 1e-12)
    if oe > th.max_odd_even_sigma and oe_frac > th.max_odd_even_frac:
        flags.append("odd_even_mismatch")
    sec_depth, sec_sigma = secondary_eclipse(time, flux, r.period, r.t0, r.duration)
    if sec_sigma > th.max_secondary_sigma:
        flags.append("secondary_eclipse")
    if r.depth > th.deep_transit:
        flags.append("deep_transit")
    if near_tess_orbit(r.period):
        flags.append("near_tess_orbit")

    if {"low_sde", "low_snr", "too_few_transits"} & set(flags):
        status = "weak"
    elif {"odd_even_mismatch", "secondary_eclipse"} & set(flags):
        status = "likely_eb"
    elif "near_tess_orbit" in flags:
        status = "suspect_systematic"
    else:
        status = "candidate"
    return VetReport(status, flags, oe, sec_depth, sec_sigma)
