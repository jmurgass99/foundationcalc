"""Tests for CPT, SPT, stress and consolidation modules."""

from __future__ import annotations

import math

import pytest

from foundationcalc.analysis.consolidation import (
    ClayLayer,
    Tv_from_U,
    U_from_Tv,
    consolidation_curve,
    elastic_settlement_rectangle,
    settlement_consolidation,
    time_to_consolidation,
)
from foundationcalc.analysis.cpt import (
    CPTProfile,
    CPTReading,
    SBTZone,
    cu_from_qt,
    i_c_robertson_2009,
    i_sbt_robertson_2010,
    phi_from_qt_kulhawy_mayne,
    relative_density_kulhawy_mayne,
    sbt_zone_from_i_c,
)
from foundationcalc.analysis.spt import (
    SoilTypeSPT,
    SPTReading,
    cu_stroud,
    derive_parameters,
    energy_correction,
    normalised_SPT,
    overburden_correction_C_N,
    phi_hatanaka_uchida,
    phi_peck_hanson_thornburn,
    relative_density_skempton,
)
from foundationcalc.analysis.stress import (
    boussinesq_circular_load_centre,
    boussinesq_point_load_dsigma_z,
    boussinesq_rect_centre,
    boussinesq_rect_corner,
    boussinesq_strip_load_dsigma_z,
    newmark_influence_factor,
)


# ---------------------------------------------------------------- CPT ------

def test_cpt_robertson_sbt_classification():
    """Clean sand: I_c < 2.05 → zone SAND."""
    # q_t = 10 MPa, R_f = 0.5 % (typical clean sand)
    assert i_sbt_robertson_2010(10.0, 0.5) < 2.05
    # Soft clay: q_t = 0.5 MPa, R_f = 5 %
    assert i_sbt_robertson_2010(0.5, 5.0) > 2.95


def test_phi_kulhawy_sand_range():
    """Sand q_c = 10 MPa under low overburden → 38° – 42°."""
    phi = phi_from_qt_kulhawy_mayne(q_t_MPa=10, sigma_v0_eff_MPa=0.05)
    assert 35 <= phi <= 45


def test_cu_from_qt_matches_handbook():
    """c_u = (q_t − σ_v0) / 14 for N_kt = 14."""
    assert cu_from_qt(q_t_kPa=1000, sigma_v0_kPa=100, N_kt=14) == pytest.approx(64.286, rel=1e-3)


def test_relative_density_clamped_to_100():
    """Very high q_c must not produce D_R > 100 %."""
    Dr = relative_density_kulhawy_mayne(q_t_MPa=50, sigma_v0_eff_MPa=0.05)
    assert 0 <= Dr <= 100


def test_cpt_profile_stratification():
    readings = []
    for d in [0.5, 1, 2, 3, 4]:
        readings.append(CPTReading(depth=d, q_c_MPa=8.0, f_s_kPa=50.0))
    for d in [5, 6, 7, 8, 9, 10]:
        readings.append(CPTReading(depth=d, q_c_MPa=0.8, f_s_kPa=40.0, u_2_kPa=80))
    profile = CPTProfile(readings=readings, water_table_depth_m=2.0)
    layers = profile.stratify(n_layers=4)
    assert len(layers) == 4
    # First layer should be sand-like
    assert layers[0].sbt_zone in (SBTZone.SAND, SBTZone.DENSE_SAND_GRAVEL, SBTZone.SAND_MIX)
    # Last layer should be clay
    assert layers[-1].sbt_zone in (SBTZone.CLAY, SBTZone.SILT_MIX_CLAY)


# ---------------------------------------------------------------- SPT ------

def test_spt_overburden_correction_clamped():
    """C_N is clamped between 0.5 and 2.0."""
    assert overburden_correction_C_N(1.0) == 2.0    # very shallow
    assert overburden_correction_C_N(1000.0) == 0.5  # very deep


def test_spt_energy_correction_60():
    """N_60 = N · (ER / 60); ER=60 → N_60 = N."""
    assert energy_correction(N_raw=20, energy_ratio_ER=60) == 20


def test_phi_hatanaka_below_45_deg():
    """For N_1(60) = 25, φ ≈ √(500) + 20 ≈ 42.4°."""
    phi = phi_hatanaka_uchida(25)
    assert phi == pytest.approx(math.sqrt(500) + 20, rel=1e-6)


def test_phi_peck_chart_range():
    """N_60 = 20 → φ ≈ 32–34 ° from PHT chart."""
    phi = phi_peck_hanson_thornburn(20)
    assert 30 < phi < 36


def test_cu_stroud_high_pi():
    """High plasticity → f_1 ≈ 4.5 → c_u = 4.5 · N_60."""
    assert cu_stroud(20, plasticity_index=40) == pytest.approx(90.0)


def test_skempton_relative_density():
    """N_1(60) = 60 → D_R = 100 %."""
    assert relative_density_skempton(60) == pytest.approx(100.0, abs=1e-6)


def test_derive_parameters_sand():
    r = SPTReading(depth_m=5, N_raw=20, sigma_v0_eff_kPa=90,
                   soil_type=SoilTypeSPT.SAND)
    d = derive_parameters(r)
    assert d.phi_deg is not None and d.phi_deg > 30
    assert d.c_u_kPa is None
    assert 0 < d.relative_density_pct <= 100


# --------------------------------------------------------- Stress -----------

def test_boussinesq_point_load_textbook():
    """At z=1 under unit point load: Δσ = 3/(2π) ≈ 0.4775."""
    assert boussinesq_point_load_dsigma_z(1, 0, 0, 1) == pytest.approx(3.0 / (2 * math.pi), rel=1e-6)


def test_circular_load_at_surface_equals_q():
    """Just below the surface, Δσ_z ≈ q under the centre of a circle."""
    assert boussinesq_circular_load_centre(100, 2.0, 0.001) == pytest.approx(100.0, rel=1e-3)


def test_newmark_corner_factor_4_quadrants_centres():
    """4 corners of B/2 × L/2 rectangles equal centre influence of B × L."""
    B, L, z = 4.0, 6.0, 3.0
    centre = boussinesq_rect_centre(100, B, L, z)
    four = 4 * boussinesq_rect_corner(100, B / 2, L / 2, z)
    assert centre == pytest.approx(four, rel=1e-6)


def test_strip_load_centerline_drops_with_depth():
    s_shallow = boussinesq_strip_load_dsigma_z(100, 3, 0, 0.5)
    s_deep = boussinesq_strip_load_dsigma_z(100, 3, 0, 5.0)
    assert s_shallow > s_deep


# ------------------------------------------------------- Consolidation -----

def test_U_50_at_Tv_0p196():
    assert U_from_Tv(0.196) == pytest.approx(0.50, abs=5e-3)


def test_U_90_at_Tv_0p848():
    assert U_from_Tv(0.848) == pytest.approx(0.90, abs=2e-3)


def test_Tv_from_U_inverse_round_trip():
    for U in [0.10, 0.30, 0.50, 0.70, 0.90]:
        Tv = Tv_from_U(U)
        # The inverse approximation has 1-2 % accuracy
        assert U_from_Tv(Tv) == pytest.approx(U, abs=0.02)


def test_consolidation_settlement_NC_clay():
    """NC clay: s = H · C_c / (1+e) · log10((sigma_0 + dsigma)/sigma_0)."""
    layer = ClayLayer(thickness_m=3, e0=1.0, C_c=0.3, C_r=0.05,
                      OCR=1.0, sigma_p_kPa=100, c_v_m2_per_year=2.0)
    s = settlement_consolidation(layer, sigma_0_kPa=100, delta_sigma_kPa=80)
    expected = 3.0 * 0.3 / 2.0 * math.log10(180 / 100)
    assert s == pytest.approx(expected, rel=1e-6)


def test_consolidation_settlement_OC_recompression():
    """Stays in recompression: smaller settlement."""
    layer = ClayLayer(thickness_m=3, e0=1.0, C_c=0.3, C_r=0.05,
                      OCR=3.0, sigma_p_kPa=300, c_v_m2_per_year=2.0)
    s = settlement_consolidation(layer, sigma_0_kPa=100, delta_sigma_kPa=80)
    expected = 3.0 * 0.05 / 2.0 * math.log10(180 / 100)
    assert s == pytest.approx(expected, rel=1e-6)


def test_consolidation_settlement_crosses_preconsolidation():
    layer = ClayLayer(thickness_m=3, e0=1.0, C_c=0.3, C_r=0.05,
                      OCR=1.5, sigma_p_kPa=150, c_v_m2_per_year=2.0)
    s = settlement_consolidation(layer, sigma_0_kPa=100, delta_sigma_kPa=100)
    s_oc = 3.0 * 0.05 / 2.0 * math.log10(150 / 100)
    s_nc = 3.0 * 0.3 / 2.0 * math.log10(200 / 150)
    assert s == pytest.approx(s_oc + s_nc, rel=1e-6)


def test_consolidation_time_curve_monotonic():
    layer = ClayLayer(thickness_m=4, e0=0.9, C_c=0.25, C_r=0.04,
                      OCR=1.0, sigma_p_kPa=120, c_v_m2_per_year=3.0)
    curve = consolidation_curve(layer, s_final_m=0.05, t_max_years=10, n_points=20)
    assert all(curve.U[i + 1] >= curve.U[i] for i in range(len(curve.U) - 1))
    assert curve.U[-1] >= curve.U[0]


def test_elastic_settlement_rectangle_positive():
    s = elastic_settlement_rectangle(q_kPa=150, B_m=2.5, L_m=2.5,
                                     E_kPa=30e3, nu=0.30)
    assert 5e-3 < s < 30e-3
