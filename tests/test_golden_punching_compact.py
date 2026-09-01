"""
test_golden_punching_compact.py — Test Golden de punzonamiento en zapatas compactas (EC2 §6.4.4(2)).

VERIFICACIÓN GOLDEN:
====================
Fuente: Eurocódigo 2 EN 1992-1-1 §6.4.4(2) + Derivación analítica en docstring.

Caso de zapata compacta:
- Dimensiones zapata: B = 1.40 m (1400 mm), L = 1.40 m (1400 mm), H = 0.50 m (500 mm) -> A_footing = 1.96 m²
- Soporte: c1 = 400 mm (0.40 m), c2 = 400 mm (0.40 m), pos_x = 700 mm, pos_y = 700 mm (centrado, beta = 1.0)
- Canto útil: d = 0.45 m -> 2d = 0.90 m
- Distancia cara soporte a borde zapata: (1.40 - 0.40)/2 = 0.50 m < 2d (0.90 m)
- Parámetros de materiales: fck = 25.0 MPa, rho_x = rho_y = 0.005, gamma_c = 1.5
- Carga de cálculo: N_sd = 600.0 kN

Derivación analítica del cálculo a mano:
1. xi = min(1 + sqrt(200 / (0.45 * 1000)), 2.0) = 1 + sqrt(200/450) = 1.666667 <= 2.0
2. rho_l = min(sqrt(0.005 * 0.005), 0.02) = 0.005
3. (100 * rho_l * fck)^(1/3) = (100 * 0.005 * 25)^(1/3) = 12.5^(1/3) = 2.320794
4. tau_rd_base = (0.18 / 1.5) * 1.666667 * 2.320794 = 0.464159 MPa = 464.159 kPa
5. A distancia a = 0.20 m:
   u(a) = 2 * (0.40 + 0.40) + 2 * pi * 0.20 = 1.60 + 1.256637 = 2.856637 m
   A_u(a) = 0.40*0.40 + 2*(0.40+0.40)*0.20 + pi*(0.20^2) = 0.16 + 0.32 + 0.125664 = 0.605664 m²
   F_sd = 600 * (1 - 0.605664 / 1.96) = 600 * 0.690988 = 414.593 kN
   tau_sd = 414.593 / (2.856637 * 0.45) = 322.518 kPa
   tau_rd(a) = 464.159 * (2 * 0.45 / 0.20) = 464.159 * 4.5 = 2088.715 kPa
   eta(a = 0.20 m) = 322.518 / 2088.715 = 0.1544
"""
from __future__ import annotations

import math
import pytest

from foundationdesignjm.core.geometry import Column, RectangularFoundation
from foundationdesignjm.design.punching_shear import punching_shear_check


def test_golden_punching_shear_compact_ec2():
    """Golden: Punzonamiento en zapata compacta resuelto por barrido a < 2d según EC2 §6.4.4(2)."""
    foundation = RectangularFoundation(
        length=1400.0,
        width=1400.0,
        thickness=500.0,
    )
    column = Column(
        length=400.0,  # mm
        width=400.0,   # mm
        pos_x=700.0,
        pos_y=700.0,
    )

    d_eff = 0.45  # m
    N_sd = 600.0  # kN
    fck = 25.0    # MPa
    rho = 0.005

    res = punching_shear_check(
        foundation=foundation,
        column=column,
        N_sd_kN=N_sd,
        fck_MPa=fck,
        rho_x=rho,
        rho_y=rho,
        d_eff_m=d_eff,
        gamma_c=1.5,
    )

    # 1. El caso pasa de no aplicable a resuelto y aplicable
    assert res.applicable is True
    assert res.is_compact is True
    assert res.verdict == "PASS"

    # 2. Comprobar que la distancia crítica es menor a 2d (0.90 m)
    assert res.a_crit_m < 2.0 * d_eff

    # 3. Comprobar la resistencia básica base tau_rd_base = 464.16 kPa
    expected_xi = 1.0 + math.sqrt(200.0 / 450.0)
    expected_tau_rd_base_kPa = (0.18 / 1.5) * expected_xi * (100.0 * 0.005 * 25.0)**(1.0/3.0) * 1000.0
    assert res.tau_rd == pytest.approx(expected_tau_rd_base_kPa, rel=1e-3)
    assert res.tau_rd == pytest.approx(464.159, rel=1e-3)

    # 4. Comprobar que la resistencia escalada tau_rd_scaled es mayor que la base gracias a (2d/a)
    assert res.tau_rd_scaled_kPa > res.tau_rd

    # 5. Comprobar ratio de utilización de punzonamiento en el entorno esperado (~0.15 - 0.16)
    assert res.utilization == pytest.approx(0.154, abs=0.03)
    assert res.is_ok is True
