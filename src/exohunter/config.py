"""Paths and settings. Override the data location with the EXOHUNTER_DATA env var."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path

    @property
    def cache_dir(self) -> Path:
        """Raw FITS downloads (lightkurve cache)."""
        return self.data_dir / "cache"

    @property
    def lightcurve_dir(self) -> Path:
        """Processed light curves and periodograms (Parquet)."""
        return self.data_dir / "lightcurves"

    @property
    def catalog_dir(self) -> Path:
        """Cached reference catalogs such as the TOI table."""
        return self.data_dir / "catalogs"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "exohunter.duckdb"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.cache_dir, self.lightcurve_dir, self.catalog_dir):
            d.mkdir(parents=True, exist_ok=True)


def get_settings(data_dir: str | Path | None = None) -> Settings:
    root = Path(data_dir or os.environ.get("EXOHUNTER_DATA") or Path.cwd() / "data")
    settings = Settings(data_dir=root.expanduser().resolve())
    settings.ensure_dirs()
    return settings
