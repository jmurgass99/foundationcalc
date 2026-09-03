"""test_consistency_punching_tie_beam.py
========================================
Campaña AG39 - Track 2: Consistencia y articulación de cimentaciones:
  - Punzonamiento biaxial ACI 318-19 §22.6 (punching_shear_aci318_check, #25)
  - Viga de atado sismorresistente NSR-10 A.3.6.4.2 (design_tie_beam_nsr10, #26)
  - Estabilidad de muros de contención (evaluate_wall_stability_coulomb_rankine, #24)
"""
from __future__ import annotations

import math
import pytest

from foundationdesignjm.design.punching_shear import (
    punching_shear_aci318_check,
    AciPunchingShearResult,
)
from foundationdesignjm.design.strap_beam import (
    design_tie_beam_nsr10,
    Nsr10TieBeamResult,
)
from foundationdesignjm.design.basement_wall import (
    evaluate_wall_stability_coulomb_rankine,
    BasementWallStabilityResult,
)


def test_punching_shear_interior_column_eccentric_moment():
    """Golden de punzonamiento ACI 318-19 con momentos biaxiales combinados."""
    # Columna 400x400 mm en losa de d_eff = 250 mm
    c1 = 400.0
    c2 = 400.0
    d = 250.0
    Vu = 450.0  # kN
    fc = 28.0   # MPa
    Mux = 35.0  # kN*m

    res = punching_shear_aci318_check(
        c1_mm=c1,
        c2_mm=c2,
        d_eff_mm=d,
        Vu_kN=Vu,
        fc_MPa=fc,
        Mux_kNm=Mux,
        column_type="interior",
    )

    assert isinstance(res, AciPunchingShearResult)
    # Perímetro crítico b0 = 2*(c1+d) + 2*(c2+d) = 4 * 650 = 2600 mm
    assert res.b0_mm == pytest.approx(2600.0, rel=1e-3)
    # Ac = b0 * d = 2600 * 250 = 650000 mm²
    assert res.Ac_mm2 == pytest.approx(650000.0, rel=1e-3)
    # La tensión v_ug_max debe ser mayor que la cortante directa v_dir por efecto del momento
    assert res.v_ug_max_MPa > res.v_dir_MPa
    assert res.is_ok is True


def test_tie_beam_nsr10_exact_axial_force_and_reinforcement():
    """Golden NSR-10 A.3.6.4.2: Fuerza Tu = 0.25 * Aa * Pu_col."""
    Pu = 1600.0  # kN
    Aa = 0.25    # Zona sísmica intermedia-alta
    L = 5.0      # m

    res = design_tie_beam_nsr10(
        Pu_col_max_kN=Pu,
        Aa=Aa,
        length_m=L,
        seismic_zone="alta",
        fc_MPa=28.0,
        fy_MPa=420.0,
    )

    assert isinstance(res, Nsr10TieBeamResult)
    # Tu = Cu = 0.25 * 0.25 * 1600 = 100.0 kN
    assert res.axial_force_Tu_kN == pytest.approx(100.0, rel=1e-3)
    assert res.axial_force_Cu_kN == pytest.approx(100.0, rel=1e-3)
    # As requerida a tracción: Tu / (phi_t * fy) = 100e3 / (0.90 * 420) = 264.55 mm²
    phi_t = 0.90
    expected_As_tens = (100.0 * 1000.0) / (phi_t * 420.0)
    assert res.As_tension_mm2 == pytest.approx(expected_As_tens, rel=1e-3)
    assert res.width_mm >= 250.0  # Mínimo constructivo sismorresistente


def test_retaining_wall_stability_overturning_and_sliding():
    """Golden estabilidad de muro de sótano/contención por Rankine."""
    res = evaluate_wall_stability_coulomb_rankine(
        height_m=3.50,
        thickness_m=0.30,
        gamma_soil_kN_m3=18.0,
        phi_deg=30.0,
        surcharge_q_kPa=10.0,
        N_axial_kN_per_m=100.0,
        base_width_m=2.40,
    )
    assert isinstance(res, BasementWallStabilityResult)
    # Ka para phi=30° es (1-sin30)/(1+sin30) = 1/3 ≈ 0.3333
    assert res.Ka == pytest.approx(1.0 / 3.0, rel=1e-2)
    # Factores de seguridad deben ser mayores a 1.50 (volcamiento) y 1.10 (deslizamiento)
    assert res.FS_overturning > 1.50
    assert res.FS_sliding > 1.10
