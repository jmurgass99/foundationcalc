"""Tests del service layer headless."""
from __future__ import annotations
import math
import pytest

from foundationcalc.services.footings import (
    IsolatedFootingInput, design_isolated_footing, FootingDesignResult,
)
from foundationcalc.services.walls import (
    CantileverWallInput, design_cantilever_wall,
)
from foundationcalc.services.piles import (
    PileAxialInput, design_pile_axial,
)
from foundationcalc.services.bearing import (
    SoilLayerSpec, BearingInput, bearing_capacity_multilayer,
)
from foundationcalc.services.seismic import (
    MononobeOkabeInput, mononobe_okabe_thrust,
)


def test_isolated_footing_axial_only():
    inp = IsolatedFootingInput(
        L_x=2.5, L_y=2.5, thickness=0.6,
        column_b=0.4, column_h=0.4,
        N=1500.0, q_allow_kPa=200.0,
    )
    res = design_isolated_footing(inp)
    assert isinstance(res, FootingDesignResult)
    assert res.pressures["q_max"] > 0
    assert res.punching["DCR"] > 0


def test_isolated_footing_biaxial():
    inp = IsolatedFootingInput(
        L_x=3.0, L_y=2.0, thickness=0.6,
        N=2000.0, M_x=300.0, M_y=200.0,
    )
    res = design_isolated_footing(inp)
    assert res.pressures["q_max"] > res.pressures["q_min"]


def test_isolated_footing_flexure_cantilever_moment():
    """Regresión: el placeholder hardcodeaba flexure Mu=0. El momento de voladizo
    en la cara de columna es estática pura: Mu = q·B·l²/2, NO cero."""
    inp = IsolatedFootingInput(
        L_x=2.5, L_y=2.5, thickness=0.5,
        column_b=0.4, column_h=0.4,
        N=1000.0, q_allow_kPa=200.0,
    )
    res = design_isolated_footing(inp)
    # q = N/Ag = 1000/6.25 = 160 kPa;  voladizo l = (2.5-0.4)/2 = 1.05 m
    # Mu = q·L_y·l²/2 = 160·2.5·1.05²/2 = 220.5 kN·m
    assert res.flexure_x["Mu"] == pytest.approx(220.5, rel=1e-3)
    assert res.flexure_y["Mu"] == pytest.approx(220.5, rel=1e-3)  # simétrico
    assert res.flexure_x["As_required"] > 0
    assert res.flexure_x["As_chosen"] >= res.flexure_x["As_min"]


def test_isolated_footing_punching_aci_square_interior():
    """ACI 318-19 §22.6.5.2 two-way (punching) shear, columna interior cuadrada.

    Caso: L=2.5 m, h=0.6 m, recubrimiento 50 mm, f'c=25 MPa, col 0.4×0.4, N=1500 kN.
      d  = 600 - 50 = 550 mm
      bo = 4·(400+550) = 3800 mm     (perímetro crítico a d/2 de la cara)
    Las 3 ecuaciones de Vc (λ=1, normalweight); gobierna el mínimo:
      a) 0.33·√f'c·bo·d                       (básica)
      b) 0.17·(1+2/βc)·√f'c·bo·d , βc=1.0
      c) 0.083·(2+αs·d/bo)·√f'c·bo·d , αs=40
    Para columna cuadrada interior gobierna (a):
      Vc = 0.33·√25·3800·550 = 3 448 500 N = 3448.5 kN
      φVc = 0.75·3448.5 = 2586.4 kN
    Demanda (cortante directo neto fuera del perímetro):
      q = N/Ag = 1500/6.25 = 240 kPa ; A_crit = 0.95² = 0.9025 m²
      Vu = N - q·A_crit = 1500 - 216.6 = 1283.4 kN
      DCR = Vu/φVc = 0.496
    """
    inp = IsolatedFootingInput(
        L_x=2.5, L_y=2.5, thickness=0.6, cover_mm=50.0,
        column_b=0.4, column_h=0.4, fc_MPa=25.0, N=1500.0,
    )
    p = design_isolated_footing(inp).punching
    assert p["d_m"] == pytest.approx(0.55, rel=1e-6)
    assert p["bo_m"] == pytest.approx(3.8, rel=1e-6)
    assert p["beta_c"] == pytest.approx(1.0, rel=1e-6)
    assert p["Vc"] == pytest.approx(3448.5, rel=1e-3)
    assert p["phiVc"] == pytest.approx(2586.375, rel=1e-3)
    assert p["Vu"] == pytest.approx(1283.4, rel=1e-3)
    assert p["DCR"] == pytest.approx(0.4962, rel=2e-3)
    assert "basic" in p["governs"]


def test_isolated_footing_punching_betac_governs():
    """Cuando la columna es alargada (βc>2.13), gobierna la ecuación (b) de βc.

    Col 0.9×0.3 (βc=3.0), d=550 mm:
      bo = 2(900+550)+2(300+550) = 2900+1700 = 4600 mm
      (a) 0.33·√25·4600·550 = 4 174 500 N = 4174.5 kN
      (b) 0.17·(1+2/3)·√25·4600·550 = 3 584 167 N = 3584.2 kN  ← gobierna
    """
    inp = IsolatedFootingInput(
        L_x=3.0, L_y=3.0, thickness=0.6, cover_mm=50.0,
        column_b=0.9, column_h=0.3, fc_MPa=25.0, N=1500.0,
    )
    p = design_isolated_footing(inp).punching
    assert p["beta_c"] == pytest.approx(3.0, rel=1e-6)
    assert p["bo_m"] == pytest.approx(4.6, rel=1e-6)
    assert p["Vc"] == pytest.approx(3584.17, rel=1e-3)
    assert "beta" in p["governs"]


def test_isolated_footing_uniaxial_liftoff():
    """Excentricidad fuera del núcleo (e > L/6) ⇒ contacto parcial, sin tensión.

    L_x=3.0, L_y=2.0, N=1000 kN, M_y=600 kN·m ⇒ e_x = 0.6 m > L_x/6 = 0.5 m.
    Bloque triangular de presión (q_min=0):
      q_max = 2N / (3·B·(L/2 - e)) = 2·1000 / (3·2.0·(1.5-0.6)) = 370.37 kPa
    La fórmula elástica daría q_min<0 (tensión imposible bajo zapata)."""
    inp = IsolatedFootingInput(
        L_x=3.0, L_y=2.0, thickness=0.6, N=1000.0, M_y=600.0,
    )
    res = design_isolated_footing(inp)
    p = res.pressures
    assert p["q_min"] == pytest.approx(0.0, abs=1e-6)
    assert p["q_max"] == pytest.approx(370.37, rel=1e-3)
    assert p["contact"] == "partial-x"
    # Honestidad: bajo despegue la flexión se calcula con q_max en ambas caras
    # (conservador). Debe quedar documentado en las notas.
    assert any("despegue" in n.lower() and "flex" in n.lower() for n in res.notes)


def test_cantilever_wall_basic():
    inp = CantileverWallInput(
        H=4.0, base_width=2.5, stem_thickness=0.4,
        toe_width=0.8, heel_width=1.3,
        gamma_soil=18.0, phi_soil=30.0, surcharge_kPa=10.0,
    )
    res = design_cantilever_wall(inp)
    assert res.sliding_FS > 0
    assert res.overturning_FS > 0
    assert res.overturning_FS > 1.0


def test_pile_axial_two_layer():
    inp = PileAxialInput(
        D=0.6, L=15.0,
        layers_qu_kPa=(50.0, 100.0, 150.0),
        layers_thickness=(5.0, 5.0, 5.0),
    )
    res = design_pile_axial(inp)
    assert res.Q_skin_kN > 0 and res.Q_tip_kN > 0
    assert res.Q_allowable_kN < res.Q_ultimate_kN


def test_bearing_capacity_granular_soil():
    layers = (
        SoilLayerSpec(thickness=2.0, gamma=18.0, phi=30.0),
        SoilLayerSpec(thickness=10.0, gamma=19.0, phi=33.0),
    )
    inp = BearingInput(L_x=2.5, L_y=2.5, depth=1.0, layers=layers)
    res = bearing_capacity_multilayer(inp)
    assert res.qu_kPa > 0
    assert res.qa_kPa == pytest.approx(res.qu_kPa / 3.0, rel=0.01)


def test_bearing_capacity_seismic_reduces():
    layers = (SoilLayerSpec(thickness=10, gamma=18, phi=30),)
    res_static = bearing_capacity_multilayer(BearingInput(
        L_x=2, L_y=2, depth=1, layers=layers))
    res_seismic = bearing_capacity_multilayer(BearingInput(
        L_x=2, L_y=2, depth=1, layers=layers, seismic_kh=0.2))
    assert res_seismic.qu_kPa < res_static.qu_kPa


def test_mononobe_okabe_basic():
    res = mononobe_okabe_thrust(MononobeOkabeInput(
        H=5.0, gamma=18.0, phi=30.0, kh=0.15,
    ))
    # K_AE > Ka estático (0.333 para φ=30)
    assert res.K_AE > 0.33
    assert res.P_AE > 0


def test_mononobe_okabe_invalid_geometry_raises():
    # Mejora B: ahora se lanza CodeError tipado (subclase de FoundationError)
    from foundationcalc.exceptions import CodeError, FoundationError
    with pytest.raises(CodeError):
        mononobe_okabe_thrust(MononobeOkabeInput(
            H=5.0, gamma=18.0, phi=15.0, kh=0.4,
        ))
    # Tambien atrapable por la base
    with pytest.raises(FoundationError):
        mononobe_okabe_thrust(MononobeOkabeInput(
            H=5.0, gamma=18.0, phi=15.0, kh=0.4,
        ))
