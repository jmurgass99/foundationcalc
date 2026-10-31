"""Tests for the FoundationCalc <- jmstructural-common / fastsap reaction bridge."""
from __future__ import annotations
import pytest

from foundationcalc.reaction_bridge import (
    reaction_to_point_load,
    size_isolated_footing_from_reactions,
    design_footings_from_model,
)
from foundationcalc._common.model import (
    Model,
    Node,
    Element,
    SectionRef,
    Material,
    Restraint,
    Reaction,
)


class TestReactionToFoundationBridge:
    def test_reaction_to_point_load_conversion(self) -> None:
        """Canonical Reaction transforms into FoundationCalc PointLoad correctly."""
        rx = Reaction(
            node_id="N1",
            fx_kN=15.0,
            fy_kN=-25.0,
            fz_kN=450.0,
            mx_kNm=30.0,
            my_kNm=-40.0,
            mz_kNm=5.0,
            case="COMB_ULS1",
        )

        pload = reaction_to_point_load(rx)
        assert pload.fz == 450.0
        assert pload.vx == 15.0
        assert pload.vy == -25.0
        assert pload.mx == 30.0
        assert pload.my == -40.0


    def test_size_isolated_footing_from_reactions_hand_derived(self) -> None:
        """Hand-derived anchor:

        N_max = 800 kN
        q_a = 200 kPa (kN/m2)
        A_req = 800 / 200 = 4.00 m2
        B = L = sqrt(4.00) = 2.00 m
        q_act = 800 / 4.00 = 200 kPa <= 200 kPa -> OK
        """
        reactions = (
            Reaction("N1", fx_kN=10.0, fy_kN=5.0, fz_kN=500.0, mx_kNm=0.0, my_kNm=0.0, mz_kNm=0.0, case="DEAD"),
            Reaction("N1", fx_kN=20.0, fy_kN=15.0, fz_kN=800.0, mx_kNm=10.0, my_kNm=20.0, mz_kNm=0.0, case="ULS"),
            Reaction("N2", fx_kN=5.0, fy_kN=5.0, fz_kN=350.0, mx_kNm=0.0, my_kNm=0.0, mz_kNm=0.0, case="ULS"),
        )

        results = size_isolated_footing_from_reactions(
            reactions=reactions,
            allowable_bearing_kPa=200.0,
            min_size_m=1.0,
            size_step_m=0.05,
        )

        assert "N1" in results
        assert "N2" in results

        r_n1 = results["N1"]
        assert pytest.approx(r_n1["N_max_kN"], rel=1e-4) == 800.0
        # Con momentos Mx=10, My=20: ex = 20/800 = 0.025 m, ey = 10/800 = 0.0125 m
        # B=2.00 m daría q_eff = 800 / (1.95 * 1.975) = 207.7 kPa > 200 kPa.
        # Meyerhof exige crecer a B = 2.05 m -> q_eff = 800 / (2.00 * 2.025) = 197.53 kPa <= 200 kPa
        assert pytest.approx(r_n1["B_m"], rel=1e-4) == 2.05
        assert pytest.approx(r_n1["L_m"], rel=1e-4) == 2.05
        assert r_n1["q_act_kPa"] <= 200.0
        assert r_n1["status"] == "BEARING_GOVERNS"

        r_n2 = results["N2"]
        # Sin momentos: A_req = 350 / 200 = 1.75 m2 -> sqrt(1.75) = 1.32287 -> round up to 0.05 step = 1.35 m
        assert pytest.approx(r_n2["N_max_kN"], rel=1e-4) == 350.0
        assert pytest.approx(r_n2["B_m"], rel=1e-4) == 1.35
        assert pytest.approx(r_n2["L_m"], rel=1e-4) == 1.35
        assert r_n2["status"] == "OK"

    def test_design_footings_from_canonical_model(self) -> None:
        """Direct integration from canonical Model containing reactions."""
        model = Model(
            nodes=(Node("N1", 0, 0, 0), Node("N2", 0, 0, 3)),
            restraints=(Restraint("N1", True, True, True, True, True, True),),
            elements=(Element("C1", "N1", "N2", SectionRef("COL", "I"), "S355"),),
            materials=(Material("S355", E_MPa=210000.0, nu=0.3, fy_MPa=355.0, rho_kg_m3=7850.0),),
            sections=(SectionRef("COL", "I"),),
            reactions=(Reaction("N1", 0.0, 0.0, 600.0, 0.0, 0.0, 0.0, "ULS"),),
        )

        results = design_footings_from_model(model, allowable_bearing_kPa=150.0)
        # A_req = 600 / 150 = 4.0 m2 -> B = L = 2.0 m
        assert "N1" in results
        assert pytest.approx(results["N1"]["B_m"], rel=1e-4) == 2.00
