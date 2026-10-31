"""Tests for earth-pressure coefficients and thrusts."""

import math
import pytest

from foundationcalc.analysis.earth_pressure import (
    K0,
    Ka_coulomb,
    Ka_rankine,
    Kp_rankine,
    active_thrust,
    at_rest_thrust,
    heel_min_width_for_rankine,
    tension_crack_depth,
)


def test_K0_NC_phi_30():
    """K_0 for normally consolidated sand φ=30°: 1 − sin 30° = 0.5."""
    assert K0(30.0) == pytest.approx(0.5)


def test_Ka_Kp_complementary():
    """K_a · K_p = 1 in Rankine when φ' is the same."""
    for phi in [20, 25, 30, 35, 40]:
        assert Ka_rankine(phi) * Kp_rankine(phi) == pytest.approx(1.0, rel=1e-9)


def test_Ka_rankine_phi36():
    """K_a Rankine for φ=36° (cantilever wall example) ≈ 0.260."""
    assert Ka_rankine(36.0) == pytest.approx(0.260, abs=0.005)


def test_Ka_rankine_phi30_2():
    """K_a for φ=30.2° (DA1-C2 reduced) ≈ 0.331."""
    assert Ka_rankine(30.2) == pytest.approx(0.331, abs=0.005)


def test_Coulomb_reduces_to_Rankine_when_delta_alpha_zero():
    """If δ=α=0 and β=90°, Coulomb = Rankine."""
    for phi in [25, 30, 35, 40]:
        Ka_c = Ka_coulomb(phi, delta_deg=0.0, beta_deg=90.0, alpha_deg=0.0)
        Ka_r = Ka_rankine(phi)
        assert Ka_c == pytest.approx(Ka_r, rel=1e-6)


def test_tension_crack_depth():
    """z_c = 2 c' / (γ √K_a) — for φ=30°, c'=10 kPa, γ=18: z_c = 1.92 m."""
    Ka = Ka_rankine(30.0)
    zc = tension_crack_depth(c_prime=10.0, gamma=18.0, K_a=Ka)
    assert zc == pytest.approx(2 * 10.0 / (18.0 * math.sqrt(Ka)), rel=1e-9)


def test_active_thrust_phi36_H3():
    """Cantilever wall H=3.3 m, γ=18, φ=36° (DA1-C1):

    P_a ≈ ½ K_a γ H² = 0.5 · 0.260 · 18 · 3.3² ≈ 25.5 kN/m (without surcharge).
    """
    res = active_thrust(H=3.3, gamma=18.0, phi_deg=36.0, c_prime=0.0)
    assert res.thrust_P == pytest.approx(25.5, abs=1.0)
    assert res.point_of_application_z == pytest.approx(3.3 / 3.0, abs=0.05)


def test_at_rest_thrust():
    """At-rest thrust on a basement wall."""
    res = at_rest_thrust(H=3.0, gamma=18.0, phi_deg=30.0)
    expected = 0.5 * 0.5 * 18.0 * 3.0 ** 2
    assert res.thrust_P == pytest.approx(expected, rel=1e-6)


def test_heel_min_width_rankine():
    """b_min = h · tan(45 − φ/2)."""
    assert heel_min_width_for_rankine(h=3.3, phi_deg=36.0) == pytest.approx(
        3.3 * math.tan(math.radians(45.0 - 18.0)), rel=1e-9
    )
