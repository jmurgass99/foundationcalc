"""Tests de las mejoras de ingeniería en foundationcalc:
- Capacidad portante multicapa real (Meyerhof & Hanna 1978) en services.bearing y endpoint REST.
- Evaluación de capacidad portante en muros en ménsula (evaluate_bearing=True y design_cantilever_wall_ec7).
- Unificación de consolidación 1D en foundationcalc.consolidacion_1d con analysis.consolidacion_1d.
"""
from __future__ import annotations

import pytest

from foundationcalc.consolidacion_1d import ConsolidationInput, evaluate_consolidation
from foundationcalc.services.bearing import (
    BearingInput,
    SoilLayerSpec,
    bearing_capacity_meyerhof_hanna,
    bearing_capacity_multilayer,
)
from foundationcalc.services.walls import (
    CantileverWallInput,
    design_cantilever_wall,
    design_cantilever_wall_ec7,
)


def test_multilayer_meyerhof_hanna_strong_over_weak_reduces_capacity():
    # Arena densa (phi=38, H=1.5 m) sobre arcilla blanda (c=25 kPa, phi=0)
    strong_only = BearingInput(
        L_x=2.0,
        L_y=2.0,
        depth=0.5,
        method="meyerhof_hanna",
        layers=(
            SoilLayerSpec(thickness=10.0, gamma=19.0, phi=38.0, c=0.0),
        ),
    )
    strong_over_weak = BearingInput(
        L_x=2.0,
        L_y=2.0,
        depth=0.5,
        method="meyerhof_hanna",
        layers=(
            SoilLayerSpec(thickness=1.5, gamma=19.0, phi=38.0, c=0.0),
            SoilLayerSpec(thickness=8.0, gamma=17.0, phi=0.0, c=25.0, qu=50.0),
        ),
    )
    r_strong = bearing_capacity_meyerhof_hanna(strong_only)
    r_punch = bearing_capacity_multilayer(strong_over_weak)
    assert r_punch.method == "meyerhof_hanna"
    assert r_punch.qu_kPa < r_strong.qu_kPa
    assert any("punching" in n for n in r_punch.notes)


def test_cantilever_wall_evaluate_bearing_and_ec7():
    inp = CantileverWallInput(
        H=4.0,
        base_width=2.8,
        stem_thickness=0.4,
        toe_width=0.9,
        heel_width=1.5,
        gamma_soil=18.0,
        phi_soil=32.0,
        surcharge_kPa=10.0,
        evaluate_bearing=True,
    )
    res = design_cantilever_wall(inp)
    assert res.bearing_FS is not None
    assert res.bearing_FS > 0.0
    assert "bearing_q_Ed_kPa" in res.stem_design
    assert "bearing_q_Rd_kPa" in res.stem_design

    res_ec7 = design_cantilever_wall_ec7(inp)
    assert res_ec7.bearing_FS == pytest.approx(res.bearing_FS)


def test_consolidacion_facade_delegates_to_canonical():
    res = evaluate_consolidation(
        ConsolidationInput(
            H_layer_m=4.0,
            sigma_v_0_kPa=100.0,
            delta_sigma_kPa=50.0,
            Cc=0.25,
            e_0=0.80,
            cv_m2_per_year=2.0,
            drainage="double",
        )
    )
    assert res.Sc_mm > 0.0
    assert res.t_90pct_days > res.t_50pct_days
