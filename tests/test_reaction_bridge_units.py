# -*- coding: utf-8 -*-
"""test_reaction_bridge_units.py — Pruebas de unidades físicas para el puente FoundationDesignJm.

Verifica rigurosamente la consistencia dimensional en el predimensionamiento geotécnico:
    N_max [kN], qa [kPa = kN/m^2]
    A_req [m^2] = N_max [kN] / qa [kN/m^2]
    side_req [m] = sqrt(A_req)
    q_act [kPa] = N_max [kN] / (B [m] * L [m])

Cálculo a mano independiente (Derivación analítica):
  - Caso 1:
    N_max = 450.0 kN, qa = 150.0 kPa
    A_req = 450.0 / 150.0 = 3.000 m^2
    side_raw = sqrt(3.0) = 1.73205 m
    Redondeo con step 0.05 m -> B = L = 1.75 m
    Área real = 1.75 * 1.75 = 3.0625 m^2
    q_act = 450.0 / 3.0625 = 146.938775 kPa <= 150.0 kPa (Status: OK)
"""
from __future__ import annotations

import math
import pytest

from foundationdesignjm.reaction_bridge import (
    design_footings_from_model,
    reaction_to_point_load,
    size_isolated_footing_from_reactions,
)
from jmstructural_common.model import Model, Node, Reaction, Restraint


class TestReactionBridgePhysicalUnits:
    def test_isolated_footing_sizing_units_hand_calculation(self) -> None:
        """Verifica el dimensionado en planta de zapata contra derivación a mano paso a paso."""
        r1 = Reaction(node_id="N_BASE_1", case="COMB_MAX", fx_kN=15.0, fy_kN=5.0, fz_kN=450.0, mx_kNm=10.0, my_kNm=20.0, mz_kNm=0.0)
        r2 = Reaction(node_id="N_BASE_1", case="COMB_MIN", fx_kN=5.0, fy_kN=2.0, fz_kN=200.0, mx_kNm=5.0, my_kNm=10.0, mz_kNm=0.0)

        qa_kPa = 150.0
        results = size_isolated_footing_from_reactions(
            reactions=[r1, r2],
            allowable_bearing_kPa=qa_kPa,
            min_size_m=1.0,
            size_step_m=0.05,
        )

        res_n1 = results["N_BASE_1"]

        # Derivación a mano independiente:
        # N_max = max(450.0, 200.0) = 450.0 kN
        assert res_n1["N_max_kN"] == 450.0
        # A_req = 450.0 / 150.0 = 3.0 m^2 -> side_raw = 1.732 m -> step 0.05 -> 1.75 m
        assert pytest.approx(res_n1["B_m"], rel=1e-6) == 1.75
        assert pytest.approx(res_n1["L_m"], rel=1e-6) == 1.75
        assert pytest.approx(res_n1["area_m2"], rel=1e-6) == 3.0625
        # q_act = 450.0 / 3.0625 = 146.9388 kPa
        expected_q_act = 450.0 / 3.0625
        assert pytest.approx(res_n1["q_act_kPa"], rel=1e-5) == expected_q_act
        assert res_n1["q_act_kPa"] <= qa_kPa
        assert res_n1["status"] == "OK"

    def test_reaction_to_point_load_conversion_preserves_magnitudes(self) -> None:
        """Verifica que reaction_to_point_load mantenga fuerzas y momentos con sus signos reales (sin abs)."""
        rx = Reaction(
            node_id="N1",
            case="GRAV",
            fx_kN=-12.5,
            fy_kN=8.3,
            fz_kN=-350.0,
            mx_kNm=-45.0,
            my_kNm=60.0,
            mz_kNm=-5.0,
        )

        pl = reaction_to_point_load(rx)
        assert pl.name == "Reaction_N1_GRAV"
        assert pl.fz == -350.0
        assert pl.vx == -12.5
        assert pl.vy == 8.3
        assert pl.mx == -45.0
        assert pl.my == 60.0


    def test_design_footings_from_model_integration(self) -> None:
        """Verifica la extracción y dimensionado completo a partir de un Model canónico."""
        n1 = Node("N_BASE_1", 0.0, 0.0, 0.0)
        n2 = Node("N_BASE_2", 4.0, 0.0, 0.0)
        rx1 = Reaction(node_id="N_BASE_1", case="ULS", fx_kN=10.0, fy_kN=0.0, fz_kN=300.0)
        rx2 = Reaction(node_id="N_BASE_2", case="ULS", fx_kN=10.0, fy_kN=0.0, fz_kN=600.0)

        model = Model(
            nodes=(n1, n2),
            reactions=(rx1, rx2),
        )

        footings = design_footings_from_model(model, allowable_bearing_kPa=200.0)
        assert "N_BASE_1" in footings
        assert "N_BASE_2" in footings
        
        # N_BASE_1: 300 / 200 = 1.5 m^2 -> side = sqrt(1.5) = 1.2247 m -> step 0.05 -> 1.25 m
        assert footings["N_BASE_1"]["B_m"] == 1.25
        # N_BASE_2: 600 / 200 = 3.0 m^2 -> side = sqrt(3.0) = 1.7320 m -> step 0.05 -> 1.75 m
        assert footings["N_BASE_2"]["B_m"] == 1.75

    def test_invalid_bearing_capacity_raises_value_error(self) -> None:
        """Presión admisible <= 0 debe ser rechazada."""
        with pytest.raises(ValueError, match="allowable_bearing_kPa"):
            size_isolated_footing_from_reactions([], allowable_bearing_kPa=0.0)
        with pytest.raises(ValueError, match="allowable_bearing_kPa"):
            size_isolated_footing_from_reactions([], allowable_bearing_kPa=-100.0)
