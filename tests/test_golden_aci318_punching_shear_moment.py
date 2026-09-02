"""Golden test para punzonamiento con momento no balanceado según ACI 318-19.

Fuente Normativa:
  ACI 318-19: Building Code Requirements for Structural Concrete.
  - §8.4.4.2: Transfer of moment to column by shear (γ_v = 1 - γ_f, γ_f = 1 / (1 + (2/3)·sqrt(b1/b2)))
  - §22.6.4.1: Critical section at d/2 from column faces
  - §R22.6.4.2: Maximum shear stress v_ug = Vu / Ac + γ_vx · Mux · cy / Jcx + γ_vy · Muy · cx / Jcy
  - §22.6.5.2: Two-way shear concrete strength v_c = min(vc1, vc2, vc3) with size effect factor λ_s (§22.5.5.1.3)
  - Tabla 21.2.1: Strength reduction factor φ = 0.75 for shear

Derivación analítica a mano — Caso 1 (Columna Interior):
-------------------------------------------------------
Datos:
  c1 = 400 mm, c2 = 400 mm, d = 300 mm
  Vu = 450 kN = 450,000 N, Mux = 60 kNm = 60,000,000 N·mm, Muy = 0
  f'c = 28.0 MPa, normal-weight (λ = 1.0), φ = 0.75

1. Perímetro crítico b0 y área Ac:
  bx = 400 + 300 = 700 mm
  by = 400 + 300 = 700 mm
  b0 = 2·(700 + 700) = 2800 mm
  Ac = 2800 · 300 = 840,000 mm²

2. Fracción de momento transferida por cortante:
  b1 = by = 700 mm, b2 = bx = 700 mm
  γ_fx = 1 / (1 + (2/3)·sqrt(700/700)) = 1 / (1 + 2/3) = 0.60
  γ_vx = 1.0 - 0.60 = 0.40

3. Centroide y propiedad polar Jcx:
  cy = 700 / 2 = 350 mm
  Jcx = (300 · 700³) / 6 + (700 · 300³) / 6 + (300 · 700 · 700²) / 2
      = 17,150,000,000 + 3,150,000,000 + 51,450,000,000 = 71,750,000,000 mm⁴

4. Tensiones actuantes:
  v_dir = 450,000 / 840,000 = 0.535714286 MPa
  v_mom = (0.40 · 60,000,000 · 350) / 71,750,000,000 = 0.117073171 MPa
  v_ug_max = 0.535714286 + 0.117073171 = 0.652787456 MPa
  v_ug_min = 0.535714286 - 0.117073171 = 0.418641115 MPa

5. Resistencia nominal y de diseño (ACI 318-19 §22.6.5.2):
  λ_s = sqrt(2 / (1 + 0.004 · 300)) = sqrt(2 / 2.2) = 0.953462589 <= 1.0
  vc1 = 0.33 · 0.953462589 · 1.0 · sqrt(28) = 1.664917631 MPa
  vc2 = 0.17 · (1 + 2/1) · 0.953462589 · sqrt(28) = 2.572145430 MPa
  vc3 = 0.083 · (2 + 40·300/2800) · 0.953462589 · sqrt(28) = 2.632145448 MPa
  vc = 1.664917631 MPa
  φ·vc = 0.75 · 1.664917631 = 1.248688223 MPa

6. Ratio de utilización (DCR):
  DCR = 0.652787456 / 1.248688223 = 0.522778580
"""
from __future__ import annotations

import math
import pytest

from foundationdesignjm.design.punching_shear import (
    AciPunchingShearResult,
    punching_shear_aci318_check,
)


def test_golden_aci318_interior_column_moment_transfer_exact():
    """GOLDEN. Verificación analítica cerrada de punzonamiento interior con momento ACI 318-19."""
    res = punching_shear_aci318_check(
        c1_mm=400.0,
        c2_mm=400.0,
        d_eff_mm=300.0,
        Vu_kN=450.0,
        fc_MPa=28.0,
        Mux_kNm=60.0,
        Muy_kNm=0.0,
        column_type="interior",
        phi=0.75,
    )

    # 1. Geometría y propiedades del perímetro crítico
    assert res.b0_mm == pytest.approx(2800.0, rel=1e-9)
    assert res.Ac_mm2 == pytest.approx(840000.0, rel=1e-9)
    assert res.Jcx_mm4 == pytest.approx(71750000000.0, rel=1e-9)

    # 2. Factores de transferencia de momento (§8.4.4.2)
    assert res.gamma_vx == pytest.approx(0.40, rel=1e-9)

    # 3. Tensiones actuantes directas y excéntricas
    assert res.v_dir_MPa == pytest.approx(0.535714286, rel=1e-8)
    assert res.v_mom_x_MPa == pytest.approx(0.117073171, rel=1e-8)
    assert res.v_ug_max_MPa == pytest.approx(0.652787456, rel=1e-8)
    assert res.v_ug_min_MPa == pytest.approx(0.418641115, rel=1e-8)

    # 4. Factor de tamaño y resistencias ACI 318-19 §22.6.5.2
    assert res.lambda_s == pytest.approx(math.sqrt(2.0 / 2.2), rel=1e-12)
    assert res.vc_MPa == pytest.approx(0.33 * math.sqrt(2.0 / 2.2) * math.sqrt(28.0), rel=1e-12)
    assert res.phi_vc_MPa == pytest.approx(0.75 * 0.33 * math.sqrt(2.0 / 2.2) * math.sqrt(28.0), rel=1e-12)

    # 5. DCR
    expected_dcr = (0.5357142857142857 + 0.11707317073170732) / (0.75 * 0.33 * math.sqrt(2.0 / 2.2) * math.sqrt(28.0))
    assert res.utilization == pytest.approx(expected_dcr, rel=1e-12)
    assert res.is_ok is True


def test_golden_aci318_zero_moment_boundary_collapses_to_pure_shear():
    """GOLDEN. Caso frontera M = 0 colapsa exactamente al cortante puro v_ug = Vu / Ac."""
    res_zero = punching_shear_aci318_check(
        c1_mm=400.0,
        c2_mm=400.0,
        d_eff_mm=300.0,
        Vu_kN=450.0,
        fc_MPa=28.0,
        Mux_kNm=0.0,
        Muy_kNm=0.0,
        column_type="interior",
    )

    assert res_zero.v_mom_x_MPa == 0.0
    assert res_zero.v_mom_y_MPa == 0.0
    assert res_zero.v_ug_max_MPa == res_zero.v_dir_MPa
    assert res_zero.v_ug_max_MPa == pytest.approx(450000.0 / 840000.0, rel=1e-12)
    # DCR sin momento
    assert res_zero.utilization == pytest.approx((450000.0 / 840000.0) / (0.75 * 0.33 * math.sqrt(2.0 / 2.2) * math.sqrt(28.0)), rel=1e-12)


def test_golden_aci318_edge_column_biaxial_moment():
    """GOLDEN. Columna de borde (3 lados) con momentos biaxiales."""
    # c1 = 400, c2 = 400, d = 300, Vu = 250 kN, Mux = 25 kNm, Muy = 40 kNm
    res_edge = punching_shear_aci318_check(
        c1_mm=400.0,
        c2_mm=400.0,
        d_eff_mm=300.0,
        Vu_kN=250.0,
        fc_MPa=28.0,
        Mux_kNm=25.0,
        Muy_kNm=40.0,
        column_type="edge",
    )

    assert res_edge.b0_mm == pytest.approx(1800.0, rel=1e-12)
    assert res_edge.Ac_mm2 == pytest.approx(540000.0, rel=1e-12)
    gamma_vy_expected = 1.0 - 1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(550.0 / 700.0))
    gamma_vx_expected = 1.0 - 1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(700.0 / 550.0))
    assert res_edge.gamma_vy == pytest.approx(gamma_vy_expected, rel=1e-12)
    assert res_edge.gamma_vx == pytest.approx(gamma_vx_expected, rel=1e-12)
    assert res_edge.v_dir_MPa == pytest.approx(250000.0 / 540000.0, rel=1e-12)
    assert res_edge.v_ug_max_MPa == pytest.approx(res_edge.v_dir_MPa + res_edge.v_mom_x_MPa + res_edge.v_mom_y_MPa, rel=1e-12)
    assert res_edge.utilization == pytest.approx(res_edge.v_ug_max_MPa / res_edge.phi_vc_MPa, rel=1e-12)
    assert res_edge.is_ok is True
