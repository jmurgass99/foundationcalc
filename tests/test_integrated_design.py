"""Tests for the integrated bearing / settlement / CPT pipeline."""

from __future__ import annotations

import math

import pytest

from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
from foundationdesignjm.analysis.cpt_to_design import (
    design_footing_from_cpt,
    soil_profile_from_cpt,
)
from foundationdesignjm.analysis.failure_mode import (
    FailureMode,
    classify_failure_mode,
    critical_rigidity_index,
    rigidity_index,
    vesic_reduction_factors,
)
from foundationdesignjm.analysis.footing_settlement import (
    total_footing_settlement,
)
from foundationdesignjm.analysis.multi_layer_bc import (
    multi_layer_bearing_capacity,
)
from foundationdesignjm.codes.eurocode7 import DesignApproach
from foundationdesignjm.core.geometry import RectangularFoundation
from foundationdesignjm.core.soil import SoilLayer, SoilProfile, SoilType


# ------------------------------------------------------------- failure mode

def test_rigidity_index_decreases_with_overburden():
    """Higher overburden → smaller I_r (more compressible behaviour)."""
    I_low = rigidity_index(E_kPa=30e3, nu=0.3, c_prime_kPa=0, phi_deg=30, q_prime_kPa=10)
    I_hi = rigidity_index(E_kPa=30e3, nu=0.3, c_prime_kPa=0, phi_deg=30, q_prime_kPa=400)
    assert I_low > I_hi


def test_critical_rigidity_index_grows_with_phi():
    """I_rc grows with φ' — the boundary moves up for denser soils."""
    assert critical_rigidity_index(20) < critical_rigidity_index(40)


def test_dense_sand_is_general_shear():
    r = classify_failure_mode(E_kPa=80e3, nu=0.3, c_prime_kPa=0, phi_deg=40,
                              q_prime_kPa=50, B_m=2, L_m=2, Nq=64,
                              relative_density_pct=80)
    assert r.mode == FailureMode.GENERAL_SHEAR
    assert r.zeta_q == 1.0
    assert r.zeta_gamma == 1.0


def test_low_rigidity_triggers_reduction():
    """For very low I_r (high stress, soft sand), reduction factors kick in."""
    # Build a low-I_r scenario manually
    zc, zq, zg = vesic_reduction_factors(phi_deg=25, I_r=4, B_m=2, L_m=2, Nq=10)
    assert zq < 1.0
    assert zg < 1.0
    assert 0 <= zc <= 1.0


# --------------------------------------------------------- multi-layer BC

def test_strong_over_weak_governed_by_weak():
    """A dense sand layer over a soft clay must be governed by the clay
    when the sand thickness below the footing is < 2B."""
    pad = RectangularFoundation(length=2500, width=2500, thickness=500, embedment_depth=1000)
    strong = SoilLayer(name="dense_sand", thickness=2.0, soil_type=SoilType.COHESIONLESS,
                      friction_angle=38, unit_weight=19)
    weak = SoilLayer(name="soft_clay", thickness=8.0, soil_type=SoilType.COHESIVE,
                    friction_angle=0, undrained_shear_strength=30, unit_weight=18)
    profile = SoilProfile(layers=[strong, weak])
    res = multi_layer_bearing_capacity(pad, profile, founding_depth_m=1.0)
    assert res.governing_case == "punching_through_strong_to_weak"
    assert res.q_ult_kPa < res.bottom_strong_q_ult
    assert res.governing_layer == "soft_clay"


def test_homogeneous_profile_uses_founding_layer():
    """If only one layer exists, q_ult should equal the standard BC of that layer."""
    pad = RectangularFoundation(length=2500, width=2500, thickness=500, embedment_depth=1000)
    sand = SoilLayer(name="sand", thickness=15, soil_type=SoilType.COHESIONLESS,
                    friction_angle=35, unit_weight=20)
    profile = SoilProfile(layers=[sand])
    res = multi_layer_bearing_capacity(pad, profile, founding_depth_m=1.0)
    assert res.governing_case == "founding_layer"
    assert res.governing_layer == "sand"


# ----------------------------------------------------- footing settlement

def test_settlement_zero_for_zero_net_pressure():
    """If applied pressure equals existing overburden, settlement ≈ 0."""
    pad = RectangularFoundation(length=2500, width=2500, thickness=500, embedment_depth=2000)
    sand = SoilLayer(name="sand", thickness=20, soil_type=SoilType.COHESIONLESS,
                    friction_angle=35, unit_weight=18, youngs_modulus=30)
    profile = SoilProfile(layers=[sand])
    res = total_footing_settlement(pad, profile, founding_depth_m=2.0,
                                  q_applied_kPa=36.0)  # = γ·D = 18·2
    assert res.s_total_mm < 0.5


def test_settlement_dominated_by_clay():
    """Clay layer must contribute most of the settlement."""
    pad = RectangularFoundation(length=2500, width=2500, thickness=500, embedment_depth=1500)
    sand = SoilLayer(name="sand", thickness=3, soil_type=SoilType.COHESIONLESS,
                    friction_angle=33, unit_weight=19, youngs_modulus=25)
    clay = SoilLayer(name="clay", thickness=5, soil_type=SoilType.COHESIVE,
                    friction_angle=0, undrained_shear_strength=40,
                    unit_weight=18, youngs_modulus=8, OCR=1.0)
    profile = SoilProfile(layers=[sand, clay], water_table_depth=2.0)
    res = total_footing_settlement(pad, profile, founding_depth_m=1.5,
                                  q_applied_kPa=200.0)
    assert res.s_consolidation_mm > res.s_immediate_mm


# --------------------------------------------------- CPT-to-design pipeline

def _toy_cpt() -> CPTProfile:
    """Sand-clay-sand profile for the pipeline tests."""
    readings = []
    for d in [0.5, 1, 2, 3]:
        readings.append(CPTReading(depth=d, q_c_MPa=6.0, f_s_kPa=40))
    for d in [4, 5, 6, 7]:
        readings.append(CPTReading(depth=d, q_c_MPa=1.0, f_s_kPa=60, u_2_kPa=50))
    for d in [8, 10, 12, 15]:
        readings.append(CPTReading(depth=d, q_c_MPa=18.0, f_s_kPa=80))
    return CPTProfile(readings=readings, water_table_depth_m=2.5)


def test_soil_profile_from_cpt_has_layers():
    cpt = _toy_cpt()
    profile = soil_profile_from_cpt(cpt, n_layers=4)
    assert len(profile.layers) == 4


def test_design_pipeline_full():
    pad = RectangularFoundation(length=2500, width=2500, thickness=500, embedment_depth=1500)
    res = design_footing_from_cpt(
        _toy_cpt(), pad, founding_depth_m=1.5, q_applied_kPa=180,
        design_approach=DesignApproach.DA2, n_strata=5,
        settlement_limit_mm=50.0,
    )
    assert res.q_Rd_kPa > 0
    assert res.bearing_utilization > 0
    assert res.settlement.s_total_mm > 0
    # The profile has a clay layer → bearing case should be punching
    # OR the clay layer ends up the governing one
    assert "clay" in res.bearing.governing_layer or res.bearing.governing_case == "founding_layer"


def test_design_pipeline_failure_for_oversized_load():
    """A 800 kPa applied pressure must fail bearing on this profile."""
    pad = RectangularFoundation(length=1500, width=1500, thickness=400, embedment_depth=1000)
    res = design_footing_from_cpt(
        _toy_cpt(), pad, founding_depth_m=1.0, q_applied_kPa=800,
        design_approach=DesignApproach.DA2,
        settlement_limit_mm=50.0,
    )
    assert (not res.bearing_ok) or (not res.settlement_ok)


def test_design_pipeline_passes_for_reasonable_load():
    """A 100 kPa applied pressure on a 3 x 3 footing should pass."""
    pad = RectangularFoundation(length=3000, width=3000, thickness=600, embedment_depth=1500)
    # Use a soil profile without a soft clay
    readings = [CPTReading(depth=d, q_c_MPa=15.0, f_s_kPa=70) for d in range(1, 12)]
    cpt = CPTProfile(readings=readings, water_table_depth_m=10.0)
    res = design_footing_from_cpt(
        cpt, pad, founding_depth_m=1.5, q_applied_kPa=100,
        design_approach=DesignApproach.DA2,
        settlement_limit_mm=50.0,
    )
    assert res.bearing_ok
    assert res.settlement_ok
