"""Golden test para cambio automático de zapata aislada a encepado con pilotes.

Criterios de conmutación:
1. Lado de zapata B_req excede el umbral máximo configurable (p.ej. max_footing_side_m = 4.50 m).
2. Capacidad portante admisible del suelo q_adm es insuficiente (inferior a min_bearing_capacity_kPa = 50.0 kPa).

El criterio de cambio se declara EXPLÍCITAMENTE en la salida de cada nudo y en la memoria técnica.
"""
from __future__ import annotations

import pytest
from foundationcalc._common.model import Reaction
from foundationcalc.integration.foundation_chain import (
    foundation_chain_from_etabs,
    foundation_package,
)


def test_golden_auto_switch_to_piles_when_side_exceeds_maximum():
    """GOLDEN. Conmutación automática a pilotes por exceso de dimensión en planta."""
    # Nudo N1 con carga pesada N = 4500 kN en suelo de q_adm = 180 kPa -> B_req = sqrt(4500/180) = 5.00 m
    # Con max_footing_side_m = 4.00 m, debe conmutar a encepado
    reactions = [Reaction(node_id="N1", case="ELU", fz_kN=4500.0)]
    soil_params = {"allowable_bearing_kPa": 180.0}

    chain = foundation_chain_from_etabs(
        etabs_or_reactions=reactions,
        soil_params=soil_params,
        max_footing_side_m=4.0,
        pile_design_capacity_kN=1200.0,
        auto_switch_to_piles=True,
    )

    node_sum = chain.design_summary["N1"]
    assert node_sum["foundation_type"] == "pile_cap"
    assert "excede el máximo permitido (4.00 m)" in node_sum["switch_reason"]
    assert "SWITCH_A_PILOTES" in node_sum["status"]

    # Verificación del dimensionado del encepado: n_piles = ceil(4500 / 1200) = 4 pilotes
    assert "N1" in chain.pile_cap_designs
    pcap = chain.pile_cap_designs["N1"]
    assert pcap["n_piles"] == 4
    assert pcap["pile_capacity_kN"] == 1200.0
    assert "tie_result_x" in pcap
    assert "tie_result_y" in pcap
    assert pcap["tie_result_x"].A_s > 0


def test_golden_auto_switch_to_piles_when_bearing_capacity_insufficient():
    """GOLDEN. Conmutación automática a pilotes por suelo de baja capacidad portante."""
    # Suelo blando con q_adm = 35.0 kPa < min_bearing_capacity_kPa = 50.0 kPa
    reactions = [Reaction(node_id="N2", case="ELU", fz_kN=800.0)]
    soil_params = {"allowable_bearing_kPa": 35.0}

    chain = foundation_chain_from_etabs(
        etabs_or_reactions=reactions,
        soil_params=soil_params,
        min_bearing_capacity_kPa=50.0,
        pile_design_capacity_kN=500.0,
        auto_switch_to_piles=True,
    )

    node_sum = chain.design_summary["N2"]
    assert node_sum["foundation_type"] == "pile_cap"
    assert "inferior al mínimo (50.0 kPa)" in node_sum["switch_reason"]

    pcap = chain.pile_cap_designs["N2"]
    # n_piles = ceil(800 / 500) = 2 pilotes
    assert pcap["n_piles"] == 2
    assert "tie_result" in pcap
    assert pcap["tie_result"].A_s > 0
