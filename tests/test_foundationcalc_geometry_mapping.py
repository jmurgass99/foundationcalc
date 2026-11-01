"""Tests para SoilSublayerMapping en FoundationCalc."""
from foundationcalc.geometry_mapping import (
    SemanticSoilLayer,
    build_foundation_sublayer_mesh,
)


def test_foundation_sublayer_mapping_refinement():
    layers = [
        SemanticSoilLayer("CLAY-UPPER", thickness_m=3.0, gamma_eff_kN_m3=9.5, e0=0.85, C_c=0.28),
        SemanticSoilLayer("CLAY-LOWER", thickness_m=4.0, gamma_eff_kN_m3=10.2, e0=0.75, C_c=0.22),
    ]
    sub_2, map_2, sum_2 = build_foundation_sublayer_mesh(
        B_m=2.5, L_m=2.5, q_net_kPa=160.0, layers=layers, divisions_per_layer=2, time_years=2.0
    )
    sub_8, map_8, sum_8 = build_foundation_sublayer_mesh(
        B_m=2.5, L_m=2.5, q_net_kPa=160.0, layers=layers, divisions_per_layer=8, time_years=2.0
    )

    assert len(sub_2) == 4
    assert len(sub_8) == 16
    assert len(map_8.layer_to_sublayers["CLAY-UPPER"]) == 8
    assert len(map_8.layer_to_sublayers["CLAY-LOWER"]) == 8
    assert sum_8["s_ult_mm"] > 10.0
    assert abs(sum_2["s_ult_mm"] - sum_8["s_ult_mm"]) / sum_8["s_ult_mm"] < 0.08
