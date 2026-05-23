"""Tests for the sliding and overturning checks."""

import math
import pytest

from foundationdesignjm.analysis.stability import (
    overturning_check,
    sliding_resistance_drained,
    sliding_resistance_undrained,
)
from foundationdesignjm.core.soil import SoilLayer, SoilType


SAND = SoilLayer(
    name="sand", thickness=5.0, soil_type=SoilType.COHESIONLESS,
    friction_angle=36.0, cohesion=0.0, unit_weight=18.0,
)
CLAY = SoilLayer(
    name="clay", thickness=5.0, soil_type=SoilType.COHESIVE,
    undrained_shear_strength=45.0, unit_weight=22.0,
)


def test_drained_sliding_basic():
    """N=300 kN, H=50 kN, φ=36°, no cohesion → H_Rd ≈ 300·tan36° = 218 kN."""
    res = sliding_resistance_drained(
        N_Ed=300.0, soil=SAND, A_eff=2.0, H_Ed=50.0,
        delta_factor=1.0,
    )
    assert res.H_Rd == pytest.approx(300.0 * math.tan(math.radians(36.0)), abs=0.5)
    assert res.utilization < 1.0
    assert res.is_ok


def test_drained_sliding_precast_delta_factor():
    """k = 2/3 — δ = arctan(2/3 · tanφ)."""
    res = sliding_resistance_drained(
        N_Ed=300.0, soil=SAND, A_eff=2.0, H_Ed=50.0,
        delta_factor=2.0 / 3.0,
    )
    expected_delta = math.degrees(math.atan(2.0 / 3.0 * math.tan(math.radians(36.0))))
    assert res.delta_d_deg == pytest.approx(expected_delta, abs=1e-3)


def test_undrained_sliding():
    """H_Rd = c_u · A_eff."""
    res = sliding_resistance_undrained(
        N_Ed=300.0, soil=CLAY, A_eff=2.5, H_Ed=50.0,
    )
    assert res.H_Rd == pytest.approx(45.0 * 2.5)


def test_overturning_eccentricity():
    """e_B = B/2 − (M_stb − M_dst)/V.

    Cantilever wall example (DA1-C1 per docs/theory/04):
      M_Ed,stb = γ_G · M_Ek,stb + γ_Q · Q_Qk · (B+x)/2 = 368.1 kN·m/m
      M_Ed,dst = 68.9, V_d = 239 → e_B ≈ 0.10 m (in middle-third).
    """
    res = overturning_check(M_dst_d=68.9, M_stb_d=368.1, V_d=239.0, B=2.7)
    expected_eB = 2.7 / 2 - (368.1 - 68.9) / 239.0
    assert res.e_B == pytest.approx(expected_eB, abs=0.01)
    assert abs(res.e_B) <= 2.7 / 6.0  # middle-third
    assert res.middle_third
