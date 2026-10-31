"""Golden test para empuje de tierras de Rankine / Coulomb y estabilidad de muro.

Fuente:
Das, B. M., "Principles of Foundation Engineering", 8th Ed., Chapter 13 (Retaining Walls).
Bowles, J. E., "Foundation Analysis and Design", 5th Ed., Chapter 11.

Caso de referencia publicado y derivación analítica cerrada:
------------------------------------------------------------
Muro de altura H = 4.00 m, espesor t = 0.40 m.
Relleno granular homogéneo:
    γ = 18.0 kN/m³
    φ' = 30.0°
    Sobrecarga uniforme en superficie: q = 10.0 kPa

1. Coeficiente activo de Rankine:
    Ka = tan²(45° - 30°/2) = tan²(30°) = (1/√3)² = 1/3 = 0.333333...

2. Empujes laterales:
    Empuje de suelo:
        P_soil = 0.5 · Ka · γ · H² = 0.5 · (1/3) · 18.0 · 4.00² = 48.0 kN/m
        Punto de aplicación sobre la base: z_soil = H/3 = 4.00/3 = 1.3333 m
    Empuje de sobrecarga:
        P_sur = Ka · q · H = (1/3) · 10.0 · 4.00 = 40.0/3 = 13.333333 kN/m
        Punto de aplicación: z_sur = H/2 = 2.00 m
    Empuje horizontal total:
        P_total = 48.0 + 13.333333 = 61.333333 kN/m.

3. Momento volcador respecto a la base:
    M_ov = P_soil · (H/3) + P_sur · (H/2)
         = 48.0 · (4/3) + (40/3) · 2.00 = 64.0 + 26.666667 = 90.666667 kNm/m.

4. Cargas estabilizadoras y deslizamiento:
    Peso propio muro (γ_c = 25.0 kN/m³): W_wall = 25.0 · 0.40 · 4.00 = 40.0 kN/m.
    Carga axial en coronación: N = 200.0 kN/m.
    Carga vertical total: V_total = 40.0 + 200.0 = 240.0 kN/m.
    Rozamiento en base (tan δ = 0.50): R_f = 240.0 · 0.50 = 120.0 kN/m.
    Factor de seguridad al deslizamiento:
        FS_sl = 120.0 / 61.333333 = 1.95652...
"""
from __future__ import annotations

import math
import pytest
from foundationcalc.design.basement_wall import (
    evaluate_wall_stability_coulomb_rankine,
)


def test_golden_basement_wall_rankine_thrust_and_safety_factors():
    """GOLDEN. Validación analítica cerrada contra ejemplo de literatura técnica (Das/Bowles)."""
    H = 4.0
    t = 0.40
    gamma_s = 18.0
    phi = 30.0
    q = 10.0
    N = 200.0

    res = evaluate_wall_stability_coulomb_rankine(
        height_m=H,
        thickness_m=t,
        gamma_soil_kN_m3=gamma_s,
        phi_deg=phi,
        surcharge_q_kPa=q,
        N_axial_kN_per_m=N,
        base_width_m=t,
        method="rankine",
        gamma_concrete_kN_m3=25.0,
        tan_delta_base=0.50,
    )

    # 1. Coeficiente Ka exacto = 1/3
    assert res.Ka == pytest.approx(1.0 / 3.0, rel=1e-6)

    # 2. Empujes exactos
    assert res.thrust_soil_kN_per_m == pytest.approx(48.0, rel=1e-6)
    assert res.thrust_surcharge_kN_per_m == pytest.approx(40.0 / 3.0, rel=1e-6)
    assert res.total_active_thrust_kN_per_m == pytest.approx(61.333333, rel=1e-5)

    # 3. Momentos
    assert res.overturning_moment_kNm_per_m == pytest.approx(90.666667, rel=1e-5)

    # 4. Factores de seguridad
    # R_friction = (40 + 200) * 0.5 = 120 kN/m
    assert res.resisting_friction_kN_per_m == pytest.approx(120.0, rel=1e-6)
    assert res.FS_sliding == pytest.approx(120.0 / (184.0 / 3.0), rel=1e-5)
    assert res.is_safe_sliding is True
