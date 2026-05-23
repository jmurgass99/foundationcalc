"""Tests for the EC8 spectrum and the foundation impedance modules."""

from __future__ import annotations

import math

import pytest

from foundationdesignjm.codes.eurocode8 import (
    DesignSpectrum,
    GroundType,
    ImportanceClass,
    SpectrumType,
    build_design_spectrum,
    design_response_spectrum,
    elastic_response_spectrum,
    get_spectrum_parameters,
    importance_factor,
    list_zones,
    lookup_seismic_zone,
)
from foundationdesignjm.dynamics import (
    rectangular_footing_impedance,
    soil_dynamic_modulus,
)


# ---------------------------------------------------------- EC8 -----------

def test_spain_zones_listed():
    zones = list_zones("ES")
    assert "Granada" in zones
    assert "Madrid" in zones


def test_lookup_known_zone():
    z = lookup_seismic_zone("ES", "Granada")
    assert z.a_gR == pytest.approx(0.23, rel=1e-6)
    assert z.spectrum_type == SpectrumType.TYPE_1


def test_lookup_unknown_raises():
    with pytest.raises(KeyError):
        lookup_seismic_zone("ES", "Atlantis")


def test_ground_type_parameters_match_table():
    """EC8 Table 3.2 (Type 1): Ground C → S=1.15, T_B=0.20, T_C=0.60, T_D=2.0."""
    params = get_spectrum_parameters(GroundType.C, SpectrumType.TYPE_1)
    assert params.S == pytest.approx(1.15)
    assert params.T_B == pytest.approx(0.20)
    assert params.T_C == pytest.approx(0.60)
    assert params.T_D == pytest.approx(2.0)


def test_importance_factor_values():
    assert importance_factor(ImportanceClass.I) == 0.8
    assert importance_factor(ImportanceClass.II) == 1.0
    assert importance_factor(ImportanceClass.III) == 1.2
    assert importance_factor(ImportanceClass.IV) == 1.4


def test_elastic_spectrum_at_T0_equals_ag_S():
    """At T = 0, S_e = a_g · S."""
    params = get_spectrum_parameters(GroundType.A, SpectrumType.TYPE_1)
    val = elastic_response_spectrum(0.0, 0.25, params)
    assert val == pytest.approx(0.25 * params.S, rel=1e-9)


def test_elastic_spectrum_plateau():
    """In [T_B, T_C], S_e = a_g · S · η · 2.5 (η=1.0 for ξ=0.05)."""
    params = get_spectrum_parameters(GroundType.B, SpectrumType.TYPE_1)
    expected = 0.20 * params.S * 1.0 * 2.5
    assert elastic_response_spectrum(params.T_B, 0.20, params) == pytest.approx(expected, rel=1e-6)
    assert elastic_response_spectrum(params.T_C, 0.20, params) == pytest.approx(expected, rel=1e-6)


def test_design_spectrum_divided_by_q():
    """S_d on the plateau = (2/3 + ...) ≤ 2.5/q · a_g · S."""
    params = get_spectrum_parameters(GroundType.A, SpectrumType.TYPE_1)
    plateau = design_response_spectrum(params.T_C, 0.30, params, behaviour_factor_q=2.0)
    expected = 0.30 * params.S * 2.5 / 2.0
    assert plateau == pytest.approx(expected, rel=1e-6)


def test_build_design_spectrum_high_level():
    ds = build_design_spectrum("ES", "Granada", GroundType.C,
                              ImportanceClass.III, behaviour_factor_q=3.0)
    # a_g = a_gR · γ_I = 0.23 · 1.2 = 0.276 g
    assert ds.a_g_g == pytest.approx(0.23 * 1.2, rel=1e-6)
    assert ds.S_d(0.4) > 0
    assert ds.S_d(5.0) > 0   # never zero (β·a_g lower bound)


# ------------------------------------------------ Foundation impedance ----

def test_impedance_returns_six_dofs():
    imp = rectangular_footing_impedance(B_m=3.0, L_m=3.0, G_MPa=40.0)
    assert imp.vertical is not None
    assert imp.horizontal_x is not None
    assert imp.horizontal_y is not None
    assert imp.rocking_x is not None
    assert imp.rocking_y is not None
    assert imp.torsion is not None


def test_impedance_static_at_zero_freq():
    """At f=0, k_dyn ≈ 1 and c_dyn ≈ 0."""
    imp = rectangular_footing_impedance(B_m=2.0, L_m=2.0, G_MPa=30.0, frequency_Hz=0.0)
    assert imp.vertical.k_dyn == pytest.approx(1.0, rel=1e-6)
    assert imp.vertical.c_dyn == pytest.approx(0.0, abs=1e-6)


def test_impedance_vertical_kv_scales_with_G():
    imp_low = rectangular_footing_impedance(B_m=3, L_m=3, G_MPa=20)
    imp_hi = rectangular_footing_impedance(B_m=3, L_m=3, G_MPa=80)
    assert imp_hi.vertical.K_static == pytest.approx(4.0 * imp_low.vertical.K_static, rel=1e-6)


def test_impedance_handles_swap_LB():
    """If user passes L < B, the function should swap to keep L ≥ B."""
    a = rectangular_footing_impedance(B_m=4.0, L_m=2.0, G_MPa=30.0)
    b = rectangular_footing_impedance(B_m=2.0, L_m=4.0, G_MPa=30.0)
    assert a.vertical.K_static == pytest.approx(b.vertical.K_static, rel=1e-6)


def test_spring_matrix_is_diagonal():
    K = rectangular_footing_impedance(B_m=2.0, L_m=3.0, G_MPa=30.0).stiffness_matrix()
    assert len(K) == 6 and all(len(row) == 6 for row in K)
    # Off-diagonal must be zero
    for i in range(6):
        for j in range(6):
            if i != j:
                assert K[i][j] == 0.0


def test_soil_dynamic_modulus_gives_positive_values():
    p = soil_dynamic_modulus(E_static_MPa=30.0, nu=0.30, G_over_Gmax=0.4)
    assert p["G_max_MPa"] > p["G_static_MPa"]
    assert p["V_s_m_s"] > 0


def test_impedance_dynamic_factor_reduces_with_frequency():
    """k_dyn decreases as a_0 grows (above zero)."""
    low = rectangular_footing_impedance(B_m=3, L_m=3, G_MPa=30, frequency_Hz=2.0)
    high = rectangular_footing_impedance(B_m=3, L_m=3, G_MPa=30, frequency_Hz=10.0)
    assert high.vertical.k_dyn < low.vertical.k_dyn
