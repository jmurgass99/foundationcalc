"""Tests del service layer headless."""
from __future__ import annotations
import math
import pytest

from foundationdesignjm.services.footings import (
    IsolatedFootingInput, design_isolated_footing, FootingDesignResult,
)
from foundationdesignjm.services.walls import (
    CantileverWallInput, design_cantilever_wall,
)
from foundationdesignjm.services.piles import (
    PileAxialInput, design_pile_axial,
)
from foundationdesignjm.services.bearing import (
    SoilLayerSpec, BearingInput, bearing_capacity_multilayer,
)
from foundationdesignjm.services.seismic import (
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
    from foundationdesignjm.exceptions import CodeError, FoundationError
    with pytest.raises(CodeError):
        mononobe_okabe_thrust(MononobeOkabeInput(
            H=5.0, gamma=18.0, phi=15.0, kh=0.4,
        ))
    # Tambien atrapable por la base
    with pytest.raises(FoundationError):
        mononobe_okabe_thrust(MononobeOkabeInput(
            H=5.0, gamma=18.0, phi=15.0, kh=0.4,
        ))
