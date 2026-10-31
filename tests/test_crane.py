"""Tests for the tower-crane foundation module."""

import math

import pytest

from foundationcalc.analysis.crane import (
    CraneLoadCase,
    CraneLoadState,
    crane_foundation_check,
    design_envelope,
)
from foundationcalc.codes.eurocode7 import DesignApproach
from foundationcalc.core.geometry import Column, RectangularFoundation
from foundationcalc.core.material import Concrete
from foundationcalc.core.soil import SoilLayer, SoilType


SAND = SoilLayer(
    name="sand", thickness=10.0, soil_type=SoilType.COHESIONLESS,
    friction_angle=36.0, cohesion=0.0, unit_weight=19.0,
)
C30 = Concrete(name="C30/37", fck=30.0)


def _service_case() -> CraneLoadCase:
    return CraneLoadCase(
        state=CraneLoadState.SERVICE, name="Service",
        N_kN=700.0, M_x_kNm=2400.0, M_y_kNm=0.0,
        V_x_kN=0.0, V_y_kN=60.0,
        is_wind_dominant=False, dynamic_factor=1.10,
    )


def _oos_case() -> CraneLoadCase:
    return CraneLoadCase(
        state=CraneLoadState.OUT_OF_SERVICE, name="OOS",
        N_kN=500.0, M_x_kNm=3200.0, M_y_kNm=0.0,
        V_x_kN=0.0, V_y_kN=130.0,
        is_wind_dominant=True, dynamic_factor=1.0,
    )


def test_load_case_resultants():
    s = _service_case()
    assert s.M_resultant == pytest.approx(2400.0)
    assert s.V_resultant == pytest.approx(60.0)


def test_service_case_passes_redesigned_pad():
    """6.5x6.5x1.6 m pad with 1.5 m overburden — service case should pass all DAs."""
    pad = RectangularFoundation(length=6500, width=6500, thickness=1600, embedment_depth=1500)
    mast = Column(length=2000, width=2000, pos_x=3250, pos_y=3250)
    for da in [DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2]:
        res = crane_foundation_check(
            foundation=pad, column=mast, load_case=_service_case(),
            soil=SAND, concrete=C30,
            design_approach=da, drained=True,
            soil_overburden_depth_mm=1500.0,
            soil_unit_weight_overburden=SAND.unit_weight,
        )
        assert res.all_ok, f"DA={da.value} should pass but utilizations = " \
            f"bearing={res.bearing_utilization:.2f} toppling={res.overturning_utilization:.2f}"


def test_undersized_pad_fails_storm():
    """4.5x4.5x1.4 m is too small for OOS storm — must catch the failure."""
    pad = RectangularFoundation(length=4500, width=4500, thickness=1400, embedment_depth=1500)
    mast = Column(length=2000, width=2000, pos_x=2250, pos_y=2250)
    res = crane_foundation_check(
        foundation=pad, column=mast, load_case=_oos_case(),
        soil=SAND, concrete=C30,
        design_approach=DesignApproach.DA1_C1, drained=True,
        soil_overburden_depth_mm=1500.0,
        soil_unit_weight_overburden=SAND.unit_weight,
    )
    assert not res.all_ok
    assert res.bearing_utilization > 1.0 or res.overturning_utilization > 1.0


def test_overturned_regime_for_extreme_eccentricity():
    """Manufacturer storm M on an even smaller pad → resultant exits the footing entirely."""
    pad = RectangularFoundation(length=3000, width=3000, thickness=1000, embedment_depth=1000)
    mast = Column(length=1500, width=1500, pos_x=1500, pos_y=1500)
    res = crane_foundation_check(
        foundation=pad, column=mast, load_case=_oos_case(),
        soil=SAND, concrete=C30,
        design_approach=DesignApproach.DA1_C1, drained=True,
        soil_overburden_depth_mm=0.0,
    )
    assert res.regime == "overturned"
    assert math.isinf(res.q_max)


def test_design_envelope_runs_all_combinations():
    pad = RectangularFoundation(length=6500, width=6500, thickness=1600, embedment_depth=1500)
    mast = Column(length=2000, width=2000, pos_x=3250, pos_y=3250)
    results = design_envelope(
        foundation=pad, column=mast,
        load_cases=[_service_case(), _oos_case()],
        soil=SAND, concrete=C30,
        drained=True,
        soil_overburden_depth_mm=1500.0,
        soil_unit_weight_overburden=SAND.unit_weight,
    )
    # 2 load cases × 4 DAs = 8 results
    assert len(results) == 8
    assert all(r.all_ok for r in results)


def test_partial_uplift_regime_under_service():
    """Service case on the initial pad: e > L/6 so should be `outside_core` (uplift)."""
    pad = RectangularFoundation(length=4500, width=4500, thickness=1400, embedment_depth=1500)
    mast = Column(length=2000, width=2000, pos_x=2250, pos_y=2250)
    res = crane_foundation_check(
        foundation=pad, column=mast, load_case=_service_case(),
        soil=SAND, concrete=C30,
        design_approach=DesignApproach.DA1_C1, drained=True,
        soil_overburden_depth_mm=1500.0,
        soil_unit_weight_overburden=SAND.unit_weight,
    )
    assert res.regime == "outside_core"
    assert res.uplift
