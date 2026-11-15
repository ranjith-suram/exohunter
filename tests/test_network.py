"""Live test against NASA archives. Skipped in CI: run with `pytest -m network`."""

import pytest

from exohunter.config import get_settings
from exohunter.crossmatch import fetch_toi_table
from exohunter.pipeline import analyze_target

pytestmark = pytest.mark.network


def test_recovers_wasp_126b(tmp_path):
    # WASP-126 b = TOI-114.01, P ~ 3.289 d, sits in TESS's continuous viewing zone.
    settings = get_settings(tmp_path)
    toi = fetch_toi_table(settings.catalog_dir)
    res = analyze_target(25155310, settings, sectors=[1], toi=toi)
    assert res.row["period"] == pytest.approx(3.289, rel=0.01)
    assert res.row["match_label"] == "known_toi"
