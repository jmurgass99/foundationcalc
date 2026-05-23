"""Validation against the worked example "pad footing on dry sand" from
docs/theory/04_eurocode7_examples.md (EN 1997-1 example).

Footing 2.5 × 1.5 m, depth 0.5 m, V_Gk = 800 kN, V_Qk = 450 kN, central.
Sand: φ_k = 35°, c'_k = 0, γ_k = 18 kN/m³.

Expected DA1-C1 numbers (from the PDF):
  N_q = 33.3, N_c = 46.1, N_γ = 45.2
  s_q = 1.34, s_c = 1.35, s_γ = 0.82
  q_ult_q = 402.8 kPa, q_ult_γ = 500.7 kPa
  Σ q_ult = 903.5 kPa  → utilization 54 %
DA1-C2:
  φ_d = 29.3°, N_q = 16.9, N_c = 28.4, N_γ = 17.8
  q_ult ≈ 394.4 kPa  → utilization 97 %
DA-2 (EU recommended):  q_Rd ≈ 645.3 kPa → utilization 75 %.
"""

import math
import pytest

from foundationdesignjm.analysis.bearing_capacity import (
    BearingCapacityFormula,
    bearing_capacity_factors,
    drained_bearing_capacity,
    shape_factors,
    undrained_bearing_capacity,
)
from foundationdesignjm.codes.eurocode7 import (
    DesignApproach,
    LimitState,
    get_partial_factors,
)
from foundationdesignjm.core.geometry import RectangularFoundation
from foundationdesignjm.core.soil import SoilLayer, SoilType


PAD_FOOTING = RectangularFoundation(
    length=2500.0, width=1500.0, thickness=500.0, embedment_depth=500.0,
)
SAND = SoilLayer(
    name="sand",
    thickness=10.0,
    soil_type=SoilType.COHESIONLESS,
    friction_angle=35.0,
    cohesion=0.0,
    unit_weight=18.0,
)

V_Gk = 800.0  # kN
V_Qk = 450.0  # kN
W_Gk = PAD_FOOTING.area * PAD_FOOTING.thickness_m * 25.0  # ≈ 46.9 kN


def test_bearing_factors_phi_35():
    """Reference values for φ' = 35°."""
    Nq, Nc, Ng = bearing_capacity_factors(35.0, BearingCapacityFormula.CHEN_EC7)
    assert Nq == pytest.approx(33.3, abs=0.2)
    assert Nc == pytest.approx(46.1, abs=0.2)
    assert Ng == pytest.approx(45.2, abs=0.2)


def test_bearing_factors_phi_29_3():
    """φ' = 29.3° (DA1-C2 reduced)."""
    Nq, Nc, Ng = bearing_capacity_factors(29.3, BearingCapacityFormula.CHEN_EC7)
    assert Nq == pytest.approx(16.9, abs=0.3)
    assert Nc == pytest.approx(28.4, abs=0.3)
    assert Ng == pytest.approx(17.8, abs=0.3)


def test_shape_factors_15_25_phi35():
    """Footing B' = 1.5, L' = 2.5, φ = 35°.

    Reference from the PDF:
      s_q = 1.34, s_c = 1.35, s_γ = 0.82
    """
    Nq, Nc, _ = bearing_capacity_factors(35.0)
    sq, sc, sg = shape_factors(B_eff=1.5, L_eff=2.5, phi_deg=35.0, Nq=Nq, Nc=Nc)
    assert sq == pytest.approx(1.34, abs=0.01)
    assert sc == pytest.approx(1.35, abs=0.02)
    assert sg == pytest.approx(0.82, abs=0.01)


def test_DA1_C1_q_ult_900_kPa():
    """DA1-C1 q_ult ≈ 903.5 kPa."""
    pf = get_partial_factors(DesignApproach.DA1_C1, LimitState.GEO)
    res = drained_bearing_capacity(
        foundation=PAD_FOOTING,
        soil=SAND,
        gamma_Rv=pf.resistance.gamma_Rv,
        gamma_phi=pf.soil.gamma_phi,
        gamma_c=pf.soil.gamma_c,
        gamma_gamma=pf.soil.gamma_gamma,
    )
    assert res.q_ult == pytest.approx(903.5, abs=10.0)


def test_DA1_C2_q_ult_390_kPa():
    """DA1-C2 q_ult ≈ 394.4 kPa with φ_d = 29.3°."""
    pf = get_partial_factors(DesignApproach.DA1_C2, LimitState.GEO)
    res = drained_bearing_capacity(
        foundation=PAD_FOOTING,
        soil=SAND,
        gamma_Rv=pf.resistance.gamma_Rv,
        gamma_phi=pf.soil.gamma_phi,
        gamma_c=pf.soil.gamma_c,
        gamma_gamma=pf.soil.gamma_gamma,
    )
    assert res.q_ult == pytest.approx(394.4, abs=10.0)


def test_DA2_qRd_645_kPa():
    """DA-2: γ_R,v = 1.4 → q_Rd ≈ 645.3 kPa."""
    pf = get_partial_factors(DesignApproach.DA2, LimitState.GEO)
    res = drained_bearing_capacity(
        foundation=PAD_FOOTING,
        soil=SAND,
        gamma_Rv=pf.resistance.gamma_Rv,
        gamma_phi=pf.soil.gamma_phi,
        gamma_c=pf.soil.gamma_c,
        gamma_gamma=pf.soil.gamma_gamma,
    )
    assert res.q_ult / res.gamma_Rv == pytest.approx(645.3, abs=10.0)


def test_undrained_clay_simple():
    """Undrained clay: q_ult ≈ (π+2)·c_u·s_c + γ·D for strip → ~245 kPa for cu=45."""
    foundation = RectangularFoundation(length=10000.0, width=2700.0, thickness=500.0, embedment_depth=500.0)
    clay = SoilLayer(
        name="clay",
        thickness=10.0,
        soil_type=SoilType.COHESIVE,
        undrained_shear_strength=45.0,
        unit_weight=22.0,
    )
    res = undrained_bearing_capacity(foundation=foundation, soil=clay)
    expected = (math.pi + 2) * 45.0 * (1 + 0.2 * (2.7 / 10.0)) + 11.0  # σ_vk,b = 22·0.5 = 11
    assert res.q_ult == pytest.approx(expected, rel=0.05)
