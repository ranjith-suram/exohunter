"""TESS light curves from NASA MAST (SPOC pipeline, 2-minute cadence)."""

from __future__ import annotations

from pathlib import Path

import lightkurve as lk


class NoDataError(RuntimeError):
    """Raised when MAST has no usable light curve for a target."""


def search(tic_id: int, sectors: list[int] | None = None, exptime: int = 120):
    return lk.search_lightcurve(
        f"TIC {tic_id}", mission="TESS", author="SPOC", exptime=exptime, sector=sectors
    )


def download_lightcurve(
    tic_id: int, sectors: list[int] | None = None, cache_dir: Path | None = None
) -> tuple[lk.LightCurve, list[int]]:
    """Download and stitch SPOC PDCSAP light curves.

    With ``sectors=None`` only the most recent sector is used: one sector is
    enough for the MVP and keeps the BLS period grid small.
    """
    results = search(tic_id, sectors)
    if len(results) == 0:
        raise NoDataError(f"No SPOC 2-min light curve for TIC {tic_id} (sectors={sectors})")
    if sectors is None:
        latest = max(int(m) for m in results.table["sequence_number"])
        results = results[results.table["sequence_number"] == latest]

    collection = results.download_all(
        download_dir=str(cache_dir) if cache_dir else None, quality_bitmask="default"
    )
    if collection is None or len(collection) == 0:
        raise NoDataError(f"Download failed for TIC {tic_id}")
    found = sorted({int(lc.meta.get("SECTOR", -1)) for lc in collection})
    return collection.stitch(), found


def targets_in_sector(sector: int, limit: int | None = None) -> list[int]:
    """TIC IDs that have a SPOC 2-min light curve in the given sector."""
    from astroquery.mast import Observations

    obs = Observations.query_criteria(
        obs_collection="TESS",
        dataproduct_type="timeseries",
        provenance_name="SPOC",
        sequence_number=sector,
        t_exptime=[100, 140],
    )
    tics = sorted({int(name) for name in obs["target_name"] if str(name).isdigit()})
    return tics[:limit] if limit else tics
