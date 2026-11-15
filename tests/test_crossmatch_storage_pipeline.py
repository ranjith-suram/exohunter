import numpy as np
import pandas as pd

from exohunter.config import get_settings
from exohunter.crossmatch import crossmatch, period_harmonic
from exohunter.detrend import bin_timeseries, clip_upper_outliers
from exohunter.pipeline import analyze_arrays
from exohunter.storage import Store

TOI = pd.DataFrame(
    {
        "toi": [101.01, 202.01],
        "tid": [111, 222],
        "tfopwg_disp": ["KP", "PC"],
        "pl_orbper": [3.2, 10.0],
        "pl_trandurh": [2.0, 3.0],
        "pl_trandep": [1000.0, 500.0],
    }
)


def test_period_harmonics():
    assert period_harmonic(3.2, 3.2) == 1.0
    assert period_harmonic(6.4, 3.2) == 2.0
    assert period_harmonic(1.6, 3.2) == 0.5
    assert period_harmonic(4.0, 3.2) is None


def test_crossmatch_labels():
    assert crossmatch(111, 3.21, TOI).label == "known_toi"
    assert crossmatch(111, 3.21, TOI).disposition == "KP"
    assert crossmatch(222, 4.4, TOI).label == "new_signal_on_toi_star"
    assert crossmatch(999, 1.0, TOI).label == "no_known_match"
    assert crossmatch(999, 1.0, None).label == "not_checked"


def test_binning_and_clipping():
    t = np.arange(0, 1, 1 / 1440)  # 1-min cadence for a day
    f = np.ones_like(t)
    f[10] = 2.0
    clipped = clip_upper_outliers(f + np.random.default_rng(0).normal(0, 1e-4, t.size))
    assert np.isnan(clipped[10])
    tb, (fb,), eb = bin_timeseries(t, f, bin_days=10 / 1440)
    assert tb.size == 144 and fb.size == 144 and np.all(eb >= 0)


def test_pipeline_end_to_end_offline(lightcurve, tmp_path):
    t, f, _ = lightcurve(period=3.2, depth=1e-3, cadence_min=2.0)
    res = analyze_arrays(111, t, f, f, [1], toi=TOI)
    assert res.row["status"] == "candidate"
    assert res.row["match_label"] == "known_toi"

    store = Store(get_settings(tmp_path))
    store.save_result(res.row)
    store.save_result(res.row)  # upsert, no duplicate
    store.save_series(111, "lc", res.lightcurve)
    out = store.results(status=["candidate"])
    assert len(out) == 1 and out.tic_id[0] == 111
    assert store.load_series(111, "lc") is not None
