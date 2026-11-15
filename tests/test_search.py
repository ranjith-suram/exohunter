import numpy as np
import pytest

from exohunter.search import bls_search, phase_fold


def test_recovers_injected_planet(lightcurve):
    t, f, e = lightcurve(period=3.2, depth=1e-3)
    r = bls_search(t, f, e)
    assert r.period == pytest.approx(3.2, rel=0.005)
    assert r.depth == pytest.approx(1e-3, rel=0.2)
    assert r.sde > 7
    assert r.depth_snr > 7
    assert r.n_transits >= 7


def test_pure_noise_is_not_significant(lightcurve):
    t, f, e = lightcurve(depth=0.0)
    r = bls_search(t, f, e)
    assert r.depth_snr < 7


def test_rejects_tiny_input():
    with pytest.raises(ValueError):
        bls_search(np.arange(10.0), np.ones(10))


def test_phase_fold_centres_transits():
    t = np.array([1.0, 4.0, 7.0, 2.5])
    assert np.allclose(phase_fold(t, 3.0, 1.0), [0, 0, 0, 1.5 - 3.0])
