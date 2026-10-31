"""Tests for seismic analysis (Mononobe-Okabe + liquefaction)."""

import math
import pytest

from foundationcalc.analysis.seismic import (
    cyclic_stress_ratio,
    liquefaction_screening,
    mononobe_okabe_K,
    normalised_SPT,
    rigid_wall_dynamic_increment,
    seismic_thrust,
)


def test_normalised_SPT_clamped():
    """N_1(60) clamped between 0.5·N and 2·N."""
    assert normalised_SPT(20, 100.0) == pytest.approx(20.0)
    # At σ' = 25 kPa → (100/25)^0.5 = 2 (clamped)
    assert normalised_SPT(10, 25.0) == pytest.approx(20.0)
    # At σ' = 400 kPa → (100/400)^0.5 = 0.5 (clamped)
    assert normalised_SPT(20, 400.0) == pytest.approx(10.0)


def test_cyclic_stress_ratio_below_20m():
    """τ_e = 0.65·α·S·σ_v0."""
    assert cyclic_stress_ratio(0.20, 100.0, depth_m=10.0) == pytest.approx(13.0)


def test_cyclic_stress_ratio_above_20m_returns_None():
    assert cyclic_stress_ratio(0.20, 100.0, depth_m=21.0) is None


def test_liquefaction_screening_deep_layer_skipped():
    res = liquefaction_screening(depth_m=20.0, alpha_S=0.20)
    assert res.required is False
    assert "15 m" in res.reason


def test_liquefaction_screening_clay():
    res = liquefaction_screening(
        depth_m=5.0, alpha_S=0.10, clay_fraction=30, plasticity_index=15
    )
    assert res.required is False


def test_liquefaction_screening_clean_sand_high_N():
    res = liquefaction_screening(depth_m=5.0, alpha_S=0.10, N_1_60=35.0)
    assert res.required is False


def test_liquefaction_screening_loose_sand():
    res = liquefaction_screening(depth_m=5.0, alpha_S=0.30, N_1_60=10.0)
    assert res.required is True


def test_mononobe_okabe_vertical_wall_no_seismic_equals_coulomb():
    """When k_h = k_v = 0, M-O collapses to Coulomb K_a.

    For vertical wall ψ=90, δ=0, β=0, the result is the Rankine K_a.
    """
    K, theta = mononobe_okabe_K(
        phi_deg=30.0, delta_deg=0.0, psi_deg=90.0, beta_deg=0.0, kh=0.0, kv=0.0,
    )
    expected = math.tan(math.radians(30.0)) ** 0  # placeholder
    # Compare against Rankine
    Ka_rankine = math.tan(math.radians(45.0 - 15.0)) ** 2
    assert K == pytest.approx(Ka_rankine, rel=0.05)
    assert theta == pytest.approx(0.0, abs=1e-6)


def test_mononobe_okabe_increases_with_seismic():
    """K should grow with k_h."""
    K0, _ = mononobe_okabe_K(35.0, 0.0, 90.0, 0.0, 0.0, 0.0)
    K1, _ = mononobe_okabe_K(35.0, 0.0, 90.0, 0.0, 0.15, 0.0)
    K2, _ = mononobe_okabe_K(35.0, 0.0, 90.0, 0.0, 0.30, 0.0)
    assert K1 > K0
    assert K2 > K1


def test_seismic_thrust_components():
    K, _ = mononobe_okabe_K(35.0, 0.0, 90.0, 0.0, 0.0, 0.0)
    res = seismic_thrust(H=4.0, gamma_star=18.0, K_mo=K)
    static = 0.5 * 18.0 * K * 4.0 ** 2
    assert res.seismic_thrust == pytest.approx(static, rel=1e-6)


def test_rigid_wall_dynamic_increment():
    """ΔP_d = α · S · γ · H²."""
    delta_p = rigid_wall_dynamic_increment(H=3.0, gamma=18.0, alpha_S=0.20)
    assert delta_p == pytest.approx(0.20 * 18.0 * 9.0)
