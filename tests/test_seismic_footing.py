"""Tests for the seismic spread-footing check."""

from __future__ import annotations

import pytest

from foundationdesignjm.analysis.seismic_footing import (
    SeismicAction,
    seismic_footing_check,
)
from foundationdesignjm.codes.eurocode7 import DesignApproach
from foundationdesignjm.core.geometry import Column, RectangularFoundation
from foundationdesignjm.core.material import Concrete
from foundationdesignjm.core.soil import SoilLayer, SoilType


@pytest.fixture
def pad():
    return RectangularFoundation(
        length=3000, width=3000, thickness=700, embedment_depth=1200,
    )


@pytest.fixture
def col():
    return Column(length=400, width=400, pos_x=1500, pos_y=1500)


@pytest.fixture
def soil():
    return SoilLayer(
        name="dense_sand", thickness=10, soil_type=SoilType.COHESIONLESS,
        friction_angle=36, cohesion=0, unit_weight=20,
    )


@pytest.fixture
def concrete():
    return Concrete(name="C30", fck=30)


@pytest.fixture
def seism():
    return SeismicAction(
        a_g=0.20, S=1.15, importance_factor_gamma_I=1.0, r_factor=2.0,
    )


def test_kh_computation(seism):
    """k_h = a_g · γ_I · S / r."""
    expected = 0.20 * 1.0 * 1.15 / 2.0
    assert seism.k_h == pytest.approx(expected)


def test_static_case_passes(pad, col, soil, concrete, seism):
    """No earthquake → load is just G+ψQ; foundation must pass."""
    res = seismic_footing_check(
        pad, col, N_kN=1200, H_kN=0, M_kNm=0,
        soil=soil, concrete=concrete, seismic=seism,
        design_approach=DesignApproach.DA3,
        soil_overburden_depth_mm=500,
    )
    assert res.all_ok
    assert res.middle_third


def test_seismic_increases_utilization(pad, col, soil, concrete, seism):
    """Adding seismic shear must increase sliding and overturning utilization."""
    light = seismic_footing_check(
        pad, col, N_kN=1200, H_kN=0, M_kNm=0,
        soil=soil, concrete=concrete, seismic=seism,
        design_approach=DesignApproach.DA3,
        soil_overburden_depth_mm=500,
    )
    heavy = seismic_footing_check(
        pad, col, N_kN=1200, H_kN=180, M_kNm=420,
        soil=soil, concrete=concrete, seismic=seism,
        design_approach=DesignApproach.DA3,
        soil_overburden_depth_mm=500,
    )
    assert heavy.sliding_utilization > light.sliding_utilization
    assert heavy.overturning_utilization > light.overturning_utilization


def test_undersized_pad_fails(col, soil, concrete, seism):
    """A 1.2 m square pad must fail in the strong shaking case."""
    small_pad = RectangularFoundation(
        length=1200, width=1200, thickness=400, embedment_depth=800,
    )
    small_col = Column(length=400, width=400, pos_x=600, pos_y=600)
    res = seismic_footing_check(
        small_pad, small_col, N_kN=1200, H_kN=200, M_kNm=400,
        soil=soil, concrete=concrete, seismic=seism,
        design_approach=DesignApproach.DA3,
    )
    assert not res.all_ok


def test_seismic_inclination_factor_reduces_bearing(pad, col, soil, concrete):
    """A stronger k_h must reduce q_Rd through the seismic inclination factor."""
    light = seismic_footing_check(
        pad, col, N_kN=1200, H_kN=100, M_kNm=200,
        soil=soil, concrete=concrete,
        seismic=SeismicAction(a_g=0.05, S=1.0, r_factor=2.0),
        design_approach=DesignApproach.DA3,
        soil_overburden_depth_mm=500,
    )
    strong = seismic_footing_check(
        pad, col, N_kN=1200, H_kN=100, M_kNm=200,
        soil=soil, concrete=concrete,
        seismic=SeismicAction(a_g=0.30, S=1.15, r_factor=1.0),
        design_approach=DesignApproach.DA3,
        soil_overburden_depth_mm=500,
    )
    assert strong.bearing_q_Rd < light.bearing_q_Rd


def test_vertical_upward_seismic_reduces_N(pad, col, soil, concrete):
    """Upward k_v must reduce the total vertical action."""
    no_kv = seismic_footing_check(
        pad, col, N_kN=1200, H_kN=0, M_kNm=0,
        soil=soil, concrete=concrete,
        seismic=SeismicAction(a_g=0.0001, S=1.0, r_factor=2.0),
        design_approach=DesignApproach.DA3,
        soil_overburden_depth_mm=500,
    )
    big_kv = seismic_footing_check(
        pad, col, N_kN=1200, H_kN=0, M_kNm=0,
        soil=soil, concrete=concrete,
        seismic=SeismicAction(a_g=0.30, S=1.15, r_factor=1.0),
        design_approach=DesignApproach.DA3,
        soil_overburden_depth_mm=500,
    )
    assert big_kv.N_d < no_kv.N_d
