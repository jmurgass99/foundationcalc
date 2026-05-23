"""Tests for the cantilever retaining-wall designer."""

from __future__ import annotations

import pytest

from foundationdesignjm.codes.eurocode7 import DesignApproach
from foundationdesignjm.core.material import Concrete
from foundationdesignjm.core.soil import SoilLayer, SoilType
from foundationdesignjm.design.retaining_wall import (
    CantileverWallDesigner,
    CantileverWallGeometry,
    RetainingWallLoading,
)


def _baseline_wall(**overrides) -> CantileverWallDesigner:
    geo = CantileverWallGeometry(
        H=5.0, stem_top=0.30, stem_bottom=0.45,
        toe=1.0, heel=2.5, base_thickness=0.55,
        embedment_front=0.8,
    )
    backfill = SoilLayer(name="fill", thickness=10, soil_type=SoilType.COHESIONLESS,
                        friction_angle=33, cohesion=0, unit_weight=19)
    foundation = SoilLayer(name="gravel", thickness=10, soil_type=SoilType.COHESIONLESS,
                          friction_angle=36, cohesion=0, unit_weight=20)
    load = RetainingWallLoading(
        backfill=backfill, foundation_soil=foundation,
        surcharge_q=10.0, water_height=0.0,
        use_coulomb=True, delta_over_phi=2.0 / 3.0,
    )
    for k, v in overrides.items():
        if hasattr(load, k):
            setattr(load, k, v)
    concrete = Concrete(name="C30", fck=30)
    return CantileverWallDesigner(geo, load, concrete, design_approach=DesignApproach.DA2)


def test_geometry_total_width():
    geo = CantileverWallGeometry(
        H=4.0, stem_top=0.25, stem_bottom=0.40,
        toe=0.8, heel=1.6, base_thickness=0.45,
    )
    assert geo.B == pytest.approx(0.8 + 0.40 + 1.6)


def test_geometry_rejects_widening_stem():
    with pytest.raises(ValueError):
        CantileverWallGeometry(
            H=4.0, stem_top=0.50, stem_bottom=0.30,
            toe=0.8, heel=1.6, base_thickness=0.40,
        )


def test_baseline_wall_all_ok():
    """A well-proportioned 5 m wall must pass all checks under DA-2."""
    res = _baseline_wall().check()
    assert res.all_ok
    assert res.bearing_utilization < 1.0
    assert res.sliding_utilization < 1.0
    assert res.overturning_utilization < 1.0
    assert res.middle_third


def test_overturning_FoS_above_15():
    """Working safety factor against overturning should be > 1.5 for the baseline."""
    res = _baseline_wall().check()
    assert res.actions.overturning_FoS > 1.5


def test_surcharge_increases_demand():
    """Adding a heavier surcharge must increase horizontal demand."""
    light = _baseline_wall()
    H_light = light.check().actions.H_d
    heavy = _baseline_wall()
    heavy.load.surcharge_q = 30.0
    H_heavy = heavy.check().actions.H_d
    assert H_heavy > H_light


def test_water_increases_horizontal_thrust():
    """Hydrostatic pressure must increase the horizontal action."""
    dry = _baseline_wall()
    H_dry = dry.check().actions.H_d
    wet = _baseline_wall()
    wet.load.water_height = 3.0
    H_wet = wet.check().actions.H_d
    assert H_wet > H_dry


def test_narrower_base_fails_sliding_or_bearing():
    """A clearly too-narrow base must fail at least one stability check."""
    geo = CantileverWallGeometry(
        H=5.0, stem_top=0.30, stem_bottom=0.45,
        toe=0.3, heel=0.7, base_thickness=0.40,   # B = 1.45 m, far too narrow
        embedment_front=0.5,
    )
    backfill = SoilLayer(name="fill", thickness=10, soil_type=SoilType.COHESIONLESS,
                        friction_angle=30, cohesion=0, unit_weight=19)
    foundation = SoilLayer(name="med-sand", thickness=10, soil_type=SoilType.COHESIONLESS,
                          friction_angle=32, cohesion=0, unit_weight=19)
    load = RetainingWallLoading(
        backfill=backfill, foundation_soil=foundation,
        surcharge_q=15.0, use_coulomb=False,
    )
    des = CantileverWallDesigner(geo, load, Concrete(fck=30), design_approach=DesignApproach.DA2)
    res = des.check()
    assert not res.all_ok


def test_structural_forces_positive():
    """Stem, heel and toe moments must be positive and non-trivial."""
    res = _baseline_wall().check()
    assert res.M_stem_base > 0
    assert res.V_stem_base > 0
    # Heel and toe moments scale with foundation pressure differential
    assert res.M_toe > 0  # toe lifts under high front pressure
    # Order-of-magnitude sanity: stem moment should be the largest of the three
    assert res.M_stem_base >= res.M_toe


def test_active_pressure_with_coulomb_lower_than_at_rest():
    """K_a (Coulomb) < K_0 for a vertical wall with no batter — the wall yields."""
    import math
    from foundationdesignjm.analysis.earth_pressure import K0, Ka_coulomb
    phi = 33
    K_a = Ka_coulomb(phi, delta_deg=phi * 2.0 / 3.0)
    K_0 = K0(phi)
    assert K_a < K_0


def test_da3_more_conservative_than_da2():
    """DA-3 applies factors on both actions and material — usually more conservative."""
    da2 = _baseline_wall()
    da3 = CantileverWallDesigner(
        da2.geo, da2.load, da2.concrete, design_approach=DesignApproach.DA3,
    )
    res2 = da2.check()
    res3 = da3.check()
    assert res3.bearing_utilization > res2.bearing_utilization
