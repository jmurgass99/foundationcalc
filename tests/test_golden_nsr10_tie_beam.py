"""Golden test para dimensionado de vigas de amarre según NSR-10 Artículo A.3.6.4.2.

Fuente Normativa:
NSR-10 (Reglamento Colombiano de Construcción Sismo Resistente),
Título A (Requisitos Generales de Diseño Sismo Resistente),
Artículo A.3.6.4.2 — Fuerzas de diseño para vigas de amarre.

Derivación analítica a mano:
----------------------------
Columna de mayor carga axial mayorada conectada: Pu = 2400.0 kN.
Coeficiente de aceleración horizontal pico efectiva: Aa = 0.35 (Amenaza sísmica alta).
Longitud de la viga de amarre: L = 5.00 m.
Materiales: f'c = 21.0 MPa, fy = 420.0 MPa.

1. Fuerza axial normativa exacta (NSR-10 A.3.6.4.2):
    En zona de amenaza sísmica alta:
        Tu = Cu = 0.25 · Aa · Pu
           = 0.25 · 0.35 · 2400.0 = 210.00 kN EXACTAMENTE.

2. En zona de amenaza sísmica intermedia:
        Tu_inter = 0.20 · Aa · Pu = 0.20 · 0.35 · 2400.0 = 168.00 kN EXACTAMENTE.

3. Armadura requerida a tracción:
    Tu <= φ · As · fy  con φ = 0.90
    As_tension = (210.0 · 1000) / (0.90 · 420.0) = 210000 / 378 = 555.5556 mm².
"""
from __future__ import annotations

import math
import pytest
from foundationdesignjm.design.strap_beam import (
    design_tie_beam_nsr10,
)


def test_golden_nsr10_tie_beam_axial_force_exact():
    """GOLDEN. Aseveración de fuerza axial exacta según NSR-10 Artículo A.3.6.4.2."""
    Pu = 2400.0  # kN
    Aa = 0.35
    L = 5.0  # m

    # 1. Zona sísmica alta: Tu = 0.25 * Aa * Pu = 210.0 kN
    res_alta = design_tie_beam_nsr10(
        Pu_col_max_kN=Pu,
        Aa=Aa,
        length_m=L,
        seismic_zone="alta",
    )

    assert res_alta.code_article == "NSR-10 Artículo A.3.6.4.2"
    assert res_alta.axial_force_Tu_kN == 210.0
    assert res_alta.axial_force_Cu_kN == 210.0
    assert res_alta.As_tension_mm2 == pytest.approx(555.5556, rel=1e-4)
    assert res_alta.n_bars >= 4
    assert res_alta.As_provided_mm2 >= res_alta.As_tension_mm2

    # 2. Zona sísmica intermedia: Tu = 0.20 * Aa * Pu = 168.0 kN
    res_inter = design_tie_beam_nsr10(
        Pu_col_max_kN=Pu,
        Aa=Aa,
        length_m=L,
        seismic_zone="intermedia",
    )
    assert res_inter.axial_force_Tu_kN == pytest.approx(168.0, abs=1e-5)
    assert res_inter.axial_force_Cu_kN == pytest.approx(168.0, abs=1e-5)

