from exohunter.search import bls_search
from exohunter.vet import near_tess_orbit, vet


def test_clean_planet_is_candidate(lightcurve):
    t, f, e = lightcurve(period=3.2, depth=1e-3)
    rep = vet(bls_search(t, f, e), t, f)
    assert rep.status == "candidate", rep.flags


def test_secondary_eclipse_flags_binary(lightcurve):
    # A shallow secondary keeps BLS on the true period, so the phase-0.5 test must
    # catch it. (A deep one makes BLS fold at P/2 and odd/even catches it instead.)
    t, f, e = lightcurve(period=3.2, depth=5e-3, secondary_depth=8e-4)
    r = bls_search(t, f, e)
    assert abs(r.period - 3.2) < 0.02
    rep = vet(r, t, f)
    assert "secondary_eclipse" in rep.flags
    assert rep.status == "likely_eb"


def test_alternating_depths_flag_binary(lightcurve):
    # Two unequal eclipses per orbit: BLS locks onto half the true period,
    # so odd and even "transits" have different depths.
    t, f, e = lightcurve(period=2.0, depth=6e-3, alt_depth=3e-3)
    rep = vet(bls_search(t, f, e), t, f)
    assert rep.status == "likely_eb", rep


def test_noise_is_weak(lightcurve):
    t, f, e = lightcurve(depth=0.0)
    assert vet(bls_search(t, f, e), t, f).status == "weak"


def test_near_tess_orbit():
    assert near_tess_orbit(13.7)
    assert near_tess_orbit(6.86)
    assert not near_tess_orbit(3.2)


def test_small_odd_even_difference_on_bright_star_is_not_binary(lightcurve):
    # Very high SNR planet with a 5% odd/even difference (noise, partial coverage):
    # statistically "significant" but physically tiny -> must stay a candidate.
    t, f, e = lightcurve(period=3.2, depth=4e-3, alt_depth=3.8e-3, noise=1e-4)
    rep = vet(bls_search(t, f, e), t, f)
    assert "odd_even_mismatch" not in rep.flags
