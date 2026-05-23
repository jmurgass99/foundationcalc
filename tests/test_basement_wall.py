"""Tests for the basement-wall designer."""

from __future__ import annotations

import math

import pytest

from foundationdesignjm.design.basement_wall import (
    BasementWallDesigner,
    BasementWallGeometry,
    BasementWallLoading,
    PressureDiagram,
    SupportConfig,
)


def _make(**load_kwargs):
    geo = BasementWallGeometry(
        height=3.5, thickness=0.30,
        eccentricity_top=0.0, eccentricity_base=0.0,
    )
    defaults = dict(
        phi_deg=30, gamma_soil=19, surcharge_q=0,
        N_min_kN_per_m=0, N_max_kN_per_m=0,
    )
    defaults.update(load_kwargs)
    load = BasementWallLoading(**defaults)
    return geo, load


def test_K0_jaky_no_OCR():
    """K_0 = 1 − sin φ (non-overconsolidated)."""
    _, load = _make()
    assert load.K0 == pytest.approx(1.0 - math.sin(math.radians(30)), rel=1e-6)


def test_K0_with_OCR_higher_than_normal():
    """Mayne-Kulhawy: K_0 = (1 − sin φ) · OCR^sin φ ; OCR > 1 → larger K_0."""
    _, load_no = _make()
    _, load_oc = _make()
    load_oc.OCR = 3.0
    assert load_oc.K0 > load_no.K0


def test_cantilever_base_moment_matches_closed_form():
    """For a cantilever with triangular load q_base = K0·γ·H, M_base = −q·H²/6."""
    geo, load = _make()
    res = BasementWallDesigner(
        geo, load,
        support=SupportConfig.CANTILEVER,
        pressure=PressureDiagram.TRIANGULAR,
    ).solve()
    K0 = load.K0
    q_base = K0 * load.gamma_soil * geo.height
    expected_M_base = -q_base * geo.height ** 2 / 6.0
    assert res.M_outer_max_kNm == pytest.approx(expected_M_base, rel=1e-2)


def test_propped_cantilever_top_reaction_matches_closed_form():
    """Propped cantilever with pure triangular load: T_top = q·H/10."""
    geo, load = _make()
    res = BasementWallDesigner(
        geo, load,
        support=SupportConfig.PROPPED_CANTILEVER,
        pressure=PressureDiagram.TRIANGULAR,
    ).solve()
    K0 = load.K0
    q_base = K0 * load.gamma_soil * geo.height
    expected_T_top = q_base * geo.height / 10.0
    assert res.R_top_kN_per_m == pytest.approx(expected_T_top, rel=1e-2)


def test_propped_cantilever_base_moment_matches_closed_form():
    """Propped cantilever with pure triangular load: M_base = −q·H²/15."""
    geo, load = _make()
    res = BasementWallDesigner(
        geo, load,
        support=SupportConfig.PROPPED_CANTILEVER,
        pressure=PressureDiagram.TRIANGULAR,
    ).solve()
    K0 = load.K0
    q_base = K0 * load.gamma_soil * geo.height
    expected_M_base = -q_base * geo.height ** 2 / 15.0
    assert res.M_outer_max_kNm == pytest.approx(expected_M_base, rel=1e-2)


def test_pinned_pinned_max_span_moment_matches_closed_form():
    """Pinned-pinned beam with pure triangular load: M_max ≈ q·H²·√5/75 at z = H/√5."""
    geo, load = _make()
    res = BasementWallDesigner(
        geo, load,
        support=SupportConfig.PINNED_PINNED,
        pressure=PressureDiagram.TRIANGULAR,
    ).solve()
    K0 = load.K0
    q_base = K0 * load.gamma_soil * geo.height
    expected_M_span = q_base * geo.height ** 2 * math.sqrt(3) / 27.0
    assert res.M_inner_max_kNm == pytest.approx(expected_M_span, rel=2e-2)


def test_water_increases_pressure():
    """A water table elevates the base pressure."""
    _, dry = _make()
    _, wet = _make()
    wet.water_height = 2.5
    geo, _ = _make()
    res_dry = BasementWallDesigner(geo, dry, support=SupportConfig.PROPPED_CANTILEVER).solve()
    res_wet = BasementWallDesigner(geo, wet, support=SupportConfig.PROPPED_CANTILEVER).solve()
    assert res_wet.q_base_kPa > res_dry.q_base_kPa
    assert abs(res_wet.M_outer_max_kNm) > abs(res_dry.M_outer_max_kNm)


def test_surcharge_adds_uniform_pressure_top():
    """Surcharge q adds K_0·q at the top of the diagram."""
    geo, load = _make(surcharge_q=20)
    res = BasementWallDesigner(geo, load, support=SupportConfig.PROPPED_CANTILEVER).solve()
    assert res.q_top_kPa == pytest.approx(load.K0 * 20.0, rel=1e-3)


def test_rectangular_pressure_is_smaller_at_base_than_triangular_peak():
    """The 0.67·K_0·(γH + q) approximation gives a smaller base value than K_0·γH."""
    geo, load = _make()
    tri = BasementWallDesigner(geo, load, pressure=PressureDiagram.TRIANGULAR).solve()
    rect = BasementWallDesigner(geo, load, pressure=PressureDiagram.RECTANGULAR).solve()
    assert rect.q_base_kPa < tri.q_base_kPa


def test_axial_eccentricity_adds_second_order_moment():
    """e_2 > 0 produces a hogging moment at the base of M = −e_2 · N_max."""
    geo = BasementWallGeometry(
        height=3.5, thickness=0.30,
        eccentricity_top=0.0, eccentricity_base=0.08,
    )
    load = BasementWallLoading(
        phi_deg=30, gamma_soil=19, surcharge_q=0,
        N_min_kN_per_m=0, N_max_kN_per_m=300,
    )
    res = BasementWallDesigner(geo, load, support=SupportConfig.PROPPED_CANTILEVER).solve()
    # M_outer_max must include the −e_2·N contribution
    assert res.second_order_M_base_kNm == pytest.approx(-0.08 * 300.0)
    # The outer moment must be more negative than the pressure-only case
    load_no_ax = load.model_copy(update={"N_max_kN_per_m": 0})
    res_no_ax = BasementWallDesigner(geo, load_no_ax,
                                     support=SupportConfig.PROPPED_CANTILEVER).solve()
    assert res.M_outer_max_kNm < res_no_ax.M_outer_max_kNm


def test_no_soil_combination_uses_only_axial():
    """When N_max and an eccentricity are present, even without pressure the
    bending exists due to combination 3 (no soil)."""
    geo = BasementWallGeometry(
        height=3.5, thickness=0.30,
        eccentricity_top=0.0, eccentricity_base=0.10,
    )
    # Build with zero soil weight (almost): low phi and small gamma -> small pressure
    load = BasementWallLoading(
        phi_deg=15, gamma_soil=10.001, surcharge_q=0,
        N_min_kN_per_m=0, N_max_kN_per_m=400,
    )
    res = BasementWallDesigner(geo, load, support=SupportConfig.PROPPED_CANTILEVER).solve()
    # Outer max must reach at least the axial-only contribution (-40 kNm/m)
    assert res.M_outer_max_kNm <= -0.10 * 400.0 + 1.0
