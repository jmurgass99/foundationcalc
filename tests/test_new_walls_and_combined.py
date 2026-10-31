"""Tests for the 5 new retaining-wall types + combined footing + DXF export."""

from __future__ import annotations

import os

import pytest

from foundationcalc.core.material import Concrete
from foundationcalc.core.soil import SoilLayer, SoilType
from foundationcalc.design.anchored_wall import (
    AnchorLevel, AnchorMode, AnchoredWallDesigner, AnchoredWallGeometry, AnchoredWallLoading,
)
from foundationcalc.design.combined_footing import (
    CombinedFootingInputs, design_combined_footing,
)
from foundationcalc.design.counterfort_wall import (
    CounterfortWallDesigner, CounterfortWallGeometry,
)
from foundationcalc.design.diaphragm_wall import (
    DiaphragmWallDesigner, DiaphragmWallGeometry, DiaphragmWallLoading,
)
from foundationcalc.design.gravity_wall import (
    GravityWallDesigner, GravityWallGeometry, GravityWallLoading,
    GravityWallMaterial,
)
from foundationcalc.design.mse_wall import (
    MSELayer, MSELoading, MSEReinforcementType, MSEWallDesigner, MSEWallGeometry,
)
from foundationcalc.design.retaining_wall import RetainingWallLoading
from foundationcalc.utils.dxf_export import export_footing_dxf


# ----------------------------------------------------------- gravity wall

@pytest.fixture
def soils():
    bf = SoilLayer(name="bf", thickness=10, soil_type=SoilType.COHESIONLESS,
                  friction_angle=32, unit_weight=19)
    fd = SoilLayer(name="fd", thickness=10, soil_type=SoilType.COHESIONLESS,
                  friction_angle=36, unit_weight=20)
    return bf, fd


def test_gravity_wall_runs(soils):
    bf, fd = soils
    geo = GravityWallGeometry(H=4.0, top_width=0.5, bottom_width=2.5)
    load = GravityWallLoading(backfill=bf, foundation_soil=fd, surcharge_q=5)
    res = GravityWallDesigner(
        geo, load, material=GravityWallMaterial.MASS_CONCRETE,
    ).check()
    assert res.W_kN_per_m > 0
    assert res.P_a_total_kN_per_m > 0
    assert res.P_h_kN_per_m > 0
    # The Coulomb resultant has a vertical component that helps stability
    assert res.P_v_kN_per_m > 0


def test_gravity_wall_centroid_matches_manual_formula():
    """For a stem with vertical back, x_c (from its own toe) =
    (s² − (s−a)²/3) / (a+s).  With toe=heel=0 (no footing extension),
    the stem centroid IS the wall centroid."""
    import pytest
    geo = GravityWallGeometry(H=4.0, top_width=0.5, bottom_width=2.2)
    expected = (2.2 ** 2 - 1.7 ** 2 / 3) / 2.7
    assert geo.stem_centroid_x_from_toe_m == pytest.approx(expected, rel=1e-6)
    # NOT B/2
    assert abs(geo.stem_centroid_x_from_toe_m - geo.B / 2) > 0.30


def test_gravity_wall_footing_extension_shifts_centroid():
    """Adding a heel-only footing should shift the combined centroid to
    the right (toward the back)."""
    import pytest
    geo_pure = GravityWallGeometry(H=4, top_width=0.5, stem_bottom=1.5)
    geo_heel = GravityWallGeometry(H=4, top_width=0.5, stem_bottom=1.5,
                                   heel=0.7, base_thickness=0.4)
    bf = SoilLayer(name="bf", thickness=10, soil_type=SoilType.COHESIONLESS,
                  friction_angle=32, unit_weight=18)
    fd = SoilLayer(name="fd", thickness=10, soil_type=SoilType.COHESIONLESS,
                  friction_angle=36, unit_weight=20)
    load = GravityWallLoading(backfill=bf, foundation_soil=fd, surcharge_q=5)
    r_pure = GravityWallDesigner(geo_pure, load,
                                 material=GravityWallMaterial.MASS_CONCRETE).check()
    r_heel = GravityWallDesigner(geo_heel, load,
                                 material=GravityWallMaterial.MASS_CONCRETE).check()
    # The heel adds a slab + soil weight further back → combined centroid
    # moves toward the back (away from the toe).
    assert r_heel.x_W_m > r_pure.x_W_m
    # And the fill on the heel must produce a non-zero contribution.
    assert r_heel.W_backfill_on_heel_kN_per_m > 0


def test_gravity_wall_material_changes_sliding(soils):
    """Crib has higher base friction (δ_b/φ = 0.85) than mass-concrete
    (2/3) → for the same wall, sliding utilization should be smaller
    for crib than for mass concrete."""
    import pytest
    bf, fd = soils
    geo = GravityWallGeometry(H=4.0, top_width=0.5, bottom_width=2.2)
    load = GravityWallLoading(backfill=bf, foundation_soil=fd, surcharge_q=5)
    r_crib = GravityWallDesigner(geo, load,
                                 material=GravityWallMaterial.CRIB).check()
    r_conc = GravityWallDesigner(geo, load,
                                 material=GravityWallMaterial.MASS_CONCRETE).check()
    assert r_crib.sliding_utilization < r_conc.sliding_utilization


def test_gravity_wall_heavier_with_concrete_than_gabion(soils):
    bf, fd = soils
    geo = GravityWallGeometry(H=3.5, top_width=0.5, bottom_width=2.0)
    load = GravityWallLoading(backfill=bf, foundation_soil=fd)
    r_concrete = GravityWallDesigner(
        geo, load, material=GravityWallMaterial.MASS_CONCRETE,
    ).check()
    r_gabion = GravityWallDesigner(
        geo, load, material=GravityWallMaterial.GABION,
    ).check()
    assert r_concrete.W_kN_per_m > r_gabion.W_kN_per_m


# ------------------------------------------------------ counterfort wall

def test_counterfort_runs(soils):
    bf, fd = soils
    geo = CounterfortWallGeometry(
        H=8.0, stem_thickness=0.35, toe=1.5, heel=3.0, base_thickness=0.8,
        counterfort_spacing_m=3.0, counterfort_thickness_m=0.40,
    )
    load = RetainingWallLoading(backfill=bf, foundation_soil=fd, surcharge_q=10)
    res = CounterfortWallDesigner(geo, load, Concrete(fck=30)).check()
    assert res.stem_M_midspan_kNm_per_m > 0
    assert res.stem_M_support_kNm_per_m > res.stem_M_midspan_kNm_per_m
    assert res.counterfort_M_base_kNm > 0


def test_counterfort_wider_spacing_increases_stem_moment(soils):
    bf, fd = soils
    geo_close = CounterfortWallGeometry(
        H=8, stem_thickness=0.35, toe=1.5, heel=3, base_thickness=0.8,
        counterfort_spacing_m=2.5, counterfort_thickness_m=0.40,
    )
    geo_far = CounterfortWallGeometry(
        H=8, stem_thickness=0.35, toe=1.5, heel=3, base_thickness=0.8,
        counterfort_spacing_m=5.0, counterfort_thickness_m=0.40,
    )
    load = RetainingWallLoading(backfill=bf, foundation_soil=fd, surcharge_q=10)
    r_close = CounterfortWallDesigner(geo_close, load, Concrete(fck=30)).check()
    r_far = CounterfortWallDesigner(geo_far, load, Concrete(fck=30)).check()
    assert r_far.stem_M_midspan_kNm_per_m > r_close.stem_M_midspan_kNm_per_m


# --------------------------------------------------------------- MSE wall

def test_mse_runs():
    layers = [
        MSELayer(z_below_top_m=0.5 + i, length_m=5.0,
                reinforcement_type=MSEReinforcementType.GEOGRID_PET,
                spacing_vertical_m=1.0)
        for i in range(5)
    ]
    geo = MSEWallGeometry(H=5.0, B_reinforced=5.0, layers=layers)
    load = MSELoading(phi_fill_deg=36, gamma_fill_kN_m3=20, surcharge_q=10,
                     phi_foundation_deg=32, gamma_foundation_kN_m3=19)
    res = MSEWallDesigner(geo, load).check()
    assert len(res.internal) == 5
    # Tension at lower layers > tension at upper layers
    assert res.internal[-1].T_max_kN_per_m > res.internal[0].T_max_kN_per_m


def test_mse_short_geogrid_fails_pullout():
    """A shallow layer with a geogrid that ends inside the active wedge
    has no anchor length → pullout fails."""
    # At z = 0.5 m in a 5 m wall, the active wedge boundary is at
    # (5 - 0.5)/tan(45 + 18) ≈ 2.29 m. A 2 m geogrid ends INSIDE the
    # wedge → no anchor length.
    layers = [MSELayer(z_below_top_m=0.5, length_m=2.0,
                      reinforcement_type=MSEReinforcementType.GEOGRID_PET,
                      spacing_vertical_m=1.0)]
    geo = MSEWallGeometry(H=5.0, B_reinforced=5.0, layers=layers)
    load = MSELoading(phi_fill_deg=36, gamma_fill_kN_m3=20,
                     phi_foundation_deg=32, gamma_foundation_kN_m3=19)
    res = MSEWallDesigner(geo, load).check()
    assert not res.internal[0].ok


# ------------------------------------------------------- anchored wall

def test_anchored_runs():
    geo = AnchoredWallGeometry(
        H_excavation=10.0, embedment_m=3.0,
        anchor_levels=[
            AnchorLevel(z_below_top_m=2, horizontal_spacing_m=2.5,
                       bond_zone_soil="medium_sand"),
            AnchorLevel(z_below_top_m=5, horizontal_spacing_m=2.5,
                       bond_zone_soil="medium_sand"),
            AnchorLevel(z_below_top_m=8, horizontal_spacing_m=2.5,
                       bond_zone_soil="medium_sand"),
        ],
    )
    load = AnchoredWallLoading(phi_deg=32, gamma_kN_m3=20, surcharge_q=15)
    res = AnchoredWallDesigner(geo, load).check()
    assert len(res.anchors) == 3
    for a in res.anchors:
        assert a.free_length_m >= 4.5
        assert a.bond_length_m > 0


def test_anchored_no_levels_raises():
    geo = AnchoredWallGeometry(
        H_excavation=10, embedment_m=3, anchor_levels=[],
    )
    load = AnchoredWallLoading(phi_deg=32, gamma_kN_m3=20)
    with pytest.raises(ValueError):
        AnchoredWallDesigner(geo, load).check()


def test_anchor_active_has_lockoff_passive_does_not():
    """Active anchors get a non-zero lock-off; passive anchors do not."""
    geo = AnchoredWallGeometry(
        H_excavation=10.0, embedment_m=3.0,
        anchor_levels=[
            AnchorLevel(z_below_top_m=2, horizontal_spacing_m=2.5,
                        bond_zone_soil="medium_sand", mode=AnchorMode.ACTIVE),
            AnchorLevel(z_below_top_m=5, horizontal_spacing_m=2.5,
                        bond_zone_soil="medium_sand", mode=AnchorMode.PASSIVE),
        ],
    )
    load = AnchoredWallLoading(phi_deg=32, gamma_kN_m3=20)
    res = AnchoredWallDesigner(geo, load).check()
    active, passive = res.anchors
    assert active.mode == AnchorMode.ACTIVE
    assert active.lock_off_load_kN > 0
    assert active.requires_wall_movement is False
    assert passive.mode == AnchorMode.PASSIVE
    assert passive.lock_off_load_kN == 0.0
    assert passive.requires_wall_movement is True


def test_anchor_active_demand_exceeds_passive_demand():
    """At-rest / apparent pressure (active mode) must be larger than the
    classical K_a triangular pressure (passive mode) for the same wall."""
    common = dict(z_below_top_m=4, horizontal_spacing_m=2.5,
                  bond_zone_soil="medium_sand")
    geo_active = AnchoredWallGeometry(
        H_excavation=10.0, embedment_m=3.0,
        anchor_levels=[AnchorLevel(**common, mode=AnchorMode.ACTIVE)],
    )
    geo_passive = AnchoredWallGeometry(
        H_excavation=10.0, embedment_m=3.0,
        anchor_levels=[AnchorLevel(**common, mode=AnchorMode.PASSIVE)],
    )
    load = AnchoredWallLoading(phi_deg=32, gamma_kN_m3=20,
                               use_apparent_pressure=True)
    res_a = AnchoredWallDesigner(geo_active, load).check()
    res_p = AnchoredWallDesigner(geo_passive, load).check()
    assert (res_a.anchors[0].T_design_kN_per_anchor
            > res_p.anchors[0].T_design_kN_per_anchor)


# ------------------------------------------------------ diaphragm wall

def test_diaphragm_runs():
    geo = DiaphragmWallGeometry(
        H_excavation=10.0, embedment_m=5.0,
        thickness_m=0.80, prop_levels_m=[1.0],
    )
    load = DiaphragmWallLoading(phi_deg=32, gamma_kN_m3=20, surcharge_q=15)
    res = DiaphragmWallDesigner(geo, load).check()
    assert res.P_active_kN_per_m > 0
    assert res.P_passive_kN_per_m > 0
    assert res.embedment_required_m > 0


def test_diaphragm_deeper_embedment_increases_passive():
    geo_shallow = DiaphragmWallGeometry(
        H_excavation=10, embedment_m=2, thickness_m=0.8, prop_levels_m=[1.0],
    )
    geo_deep = DiaphragmWallGeometry(
        H_excavation=10, embedment_m=8, thickness_m=0.8, prop_levels_m=[1.0],
    )
    load = DiaphragmWallLoading(phi_deg=32, gamma_kN_m3=20)
    r_s = DiaphragmWallDesigner(geo_shallow, load).check()
    r_d = DiaphragmWallDesigner(geo_deep, load).check()
    assert r_d.P_passive_kN_per_m > r_s.P_passive_kN_per_m
    assert r_d.overturning_safety_factor > r_s.overturning_safety_factor


# --------------------------------------------------- combined footing

def test_combined_footing_rectangular():
    """Column at the middle of the property → rectangular."""
    res = design_combined_footing(CombinedFootingInputs(
        P1_kN=800, P2_kN=1200, col_spacing_m=4.5,
        column_1_to_property_line_m=2.0,    # not at property line
        q_allow_kPa=180,
    ))
    assert res.shape == "rectangular"
    assert res.L_m > 0
    assert res.A_provided_m2 >= res.A_required_m2 * 0.95


def test_combined_footing_trapezoidal_at_property_line():
    """Column 1 right at the property line → trapezoidal."""
    res = design_combined_footing(CombinedFootingInputs(
        P1_kN=800, P2_kN=1200, col_spacing_m=4.5,
        column_1_to_property_line_m=0.0,
        q_allow_kPa=180,
    ))
    assert res.shape == "trapezoidal"
    assert res.B2_m >= res.B1_m


def test_combined_footing_reinforcement_positive():
    res = design_combined_footing(CombinedFootingInputs(
        P1_kN=900, P2_kN=900, col_spacing_m=4.0,
        column_1_to_property_line_m=1.5, q_allow_kPa=200,
    ))
    assert res.As_top_mm2 > 0
    assert res.As_bot_mm2 > 0


# --------------------------------------------------------- DXF export

def test_dxf_export_writes_file(tmp_path):
    path = export_footing_dxf(
        str(tmp_path / "footing.dxf"),
        B_mm=2500, L_mm=2500, column_a_mm=400,
        rebar_long_count=12, rebar_long_dia_mm=16,
        rebar_trans_count=12, rebar_trans_dia_mm=16,
        cover_mm=70, title="Test",
    )
    assert os.path.isfile(path)
    text = open(path, encoding="ascii").read()
    # Basic DXF sanity: starts with header, contains LINE entities, ends with EOF.
    assert "SECTION" in text
    assert "LINE" in text
    assert text.strip().endswith("EOF")
    # Must reference the layers we declared.
    assert "FOOTING" in text and "COLUMN" in text and "REBAR_X" in text
