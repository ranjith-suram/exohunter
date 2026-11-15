import numpy as np
import pytest


def make_lightcurve(
    period=3.2, t0=1.1, duration=0.12, depth=1e-3, noise=3e-4, baseline=27.0,
    cadence_min=10.0, secondary_depth=0.0, alt_depth=None, seed=42,
):
    """Synthetic flat light curve with box transits. ``alt_depth`` makes every other
    transit a different depth (eclipsing-binary signature)."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, baseline, cadence_min / 1440)
    f = 1 + rng.normal(0, noise, t.size)
    phase = (t - t0 + 0.5 * period) % period - 0.5 * period
    epoch = np.round((t - t0) / period).astype(int)
    in_tr = np.abs(phase) < duration / 2
    d = np.where((epoch % 2 == 1) & (alt_depth is not None), alt_depth or 0, depth)
    f[in_tr] -= d[in_tr]
    if secondary_depth:
        ph2 = (t - t0) % period - 0.5 * period
        f[np.abs(ph2) < duration / 2] -= secondary_depth
    return t, f, np.full_like(t, noise)


@pytest.fixture
def lightcurve():
    return make_lightcurve
