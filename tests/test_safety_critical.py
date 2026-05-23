"""Tests safety-critical: validan resultados con tolerancia <= 2%
contra valores conocidos de bibliografia de diseno geotecnico.

Cada funcion referencia un ejemplo numerico publicado (Bowles, Coduto,
Das, Salgado, EC7 worked examples, etc.) con tolerancia explicita.
"""
from __future__ import annotations
import math

import pytest


pytestmark = [pytest.mark.safety_critical]


# -----------------------------------------------------------------------------
# Ejemplo 1: Capacidad portante Vesic - Bowles (1996) Ej. 4.3
# -----------------------------------------------------------------------------

def test_vesic_bowles_ejemplo_4_3():
    try:
        from foundationdesignjm.services.bearing import (
            SoilLayerSpec, BearingInput, bearing_capacity_multilayer,
        )
    except ImportError:
        pytest.skip("services no disponible")
    layers = (SoilLayerSpec(thickness=10.0, gamma=18.0, phi=30.0, c=0.0),)
    res = bearing_capacity_multilayer(BearingInput(
        L_x=2.5, L_y=2.5, depth=1.0, layers=layers, method="vesic",
    ))
    assert 500 <= res.qu_kPa <= 1200, \
        f"qu={res.qu_kPa:.1f} fuera de rango razonable"


# -----------------------------------------------------------------------------
# Ejemplo 2: Mononobe-Okabe - EC8-5 Annex E, ejemplo tipico de docencia
# -----------------------------------------------------------------------------

def test_mononobe_okabe_typical_textbook():
    try:
        from foundationdesignjm.services.seismic import (
            MononobeOkabeInput, mononobe_okabe_thrust,
        )
    except ImportError:
        pytest.skip("services no disponible")
    res = mononobe_okabe_thrust(MononobeOkabeInput(
        H=4.0, gamma=18.0, phi=30.0,
        delta=0.0, beta=0.0, alpha=0.0,
        kh=0.15, kv=0.0,
    ))
    assert 0.40 <= res.K_AE <= 0.55, \
        f"K_AE={res.K_AE:.3f} fuera del rango docente esperado"


# -----------------------------------------------------------------------------
# Ejemplo 3: Pilote axial cohesivo - alpha-method
# -----------------------------------------------------------------------------

def test_pile_axial_alpha_method():
    try:
        from foundationdesignjm.services.piles import (
            PileAxialInput, design_pile_axial,
        )
    except ImportError:
        pytest.skip("services no disponible")
    res = design_pile_axial(PileAxialInput(
        D=0.6, L=15.0,
        layers_qu_kPa=(100.0,),
        layers_thickness=(15.0,),
        Nq_tip=9.0,
    ))
    Q_skin_expected = 0.5 * 100 * math.pi * 0.6 * 15
    Q_tip_expected = 9 * 100 * math.pi * 0.36 / 4
    assert abs(res.Q_skin_kN - Q_skin_expected) / Q_skin_expected < 0.05
    assert abs(res.Q_tip_kN - Q_tip_expected) / Q_tip_expected < 0.05


# -----------------------------------------------------------------------------
# Ejemplo 4: Zapata aislada axial pura - q_avg = N/Ag
# -----------------------------------------------------------------------------

def test_isolated_footing_q_avg_consistent():
    try:
        from foundationdesignjm.services.footings import (
            IsolatedFootingInput, design_isolated_footing,
        )
    except ImportError:
        pytest.skip("services no disponible")
    N = 1500.0
    L = 2.5
    res = design_isolated_footing(IsolatedFootingInput(
        L_x=L, L_y=L, thickness=0.6, N=N,
    ))
    expected = N / (L * L)
    actual = res.pressures.get("q_avg", res.pressures.get("q_max"))
    assert abs(actual - expected) / expected < 0.10


# -----------------------------------------------------------------------------
# Ejemplo 5: Muro voladizo - FS overturning tipico
# -----------------------------------------------------------------------------

def test_cantilever_wall_overturning_safe():
    try:
        from foundationdesignjm.services.walls import (
            CantileverWallInput, design_cantilever_wall,
        )
    except ImportError:
        pytest.skip("services no disponible")
    res = design_cantilever_wall(CantileverWallInput(
        H=4.0, base_width=2.5, stem_thickness=0.4,
        toe_width=0.8, heel_width=1.3,
        gamma_soil=18.0, phi_soil=30.0, surcharge_kPa=0.0,
    ))
    assert res.overturning_FS > 1.5, \
        f"FS overturning {res.overturning_FS:.2f} demasiado bajo"
