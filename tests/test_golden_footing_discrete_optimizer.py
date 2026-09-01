"""Golden test para el optimizador discreto de zapatas aisladas (planta + canto).

Objetivo y Aserción Obligatoria:
1. El candidato óptimo pasa todos los chequeos de diseño (tensión admisible, punzonamiento, flexión).
2. Ningún candidato más barato en la malla evaluada pasa todos los chequeos (demostración de optimalidad estricta).
"""
from __future__ import annotations

import pytest
from foundationdesignjm.services.footings import (
    optimize_isolated_footing_discrete_grid,
)


def test_golden_footing_discrete_optimizer_strict_optimality():
    """GOLDEN. El óptimo cumple y ninguna opción de menor coste cumple."""
    N_test = 900.0  # kN
    q_adm = 220.0  # kPa
    # Malla de búsqueda
    lx_grid = [1.2, 1.5, 1.8, 2.0, 2.2, 2.5]
    ly_grid = [1.2, 1.5, 1.8, 2.0, 2.2, 2.5]
    h_grid = [0.35, 0.45, 0.55, 0.65]

    res = optimize_isolated_footing_discrete_grid(
        N_kN=N_test,
        q_allow_kPa=q_adm,
        M_x_kNm=30.0,
        M_y_kNm=20.0,
        L_x_grid=lx_grid,
        L_y_grid=ly_grid,
        thickness_grid=h_grid,
        unit_cost_concrete_eur_m3=130.0,
        unit_cost_steel_eur_kg=2.00,
        unit_cost_formwork_eur_m2=40.0,
    )

    best = res.best_candidate

    # 1. El óptimo pasa todos los chequeos
    assert best.passes_all is True
    assert best.q_max_kPa <= q_adm
    assert best.punching_dcr <= 1.0
    assert len(best.failure_reasons) == 0

    # 2. Prueba estricta de optimalidad:
    # Para cualquier candidato de la malla con coste estrictamente menor al óptimo,
    # DEBE haber fallado al menos un chequeo de ingeniería.
    cheaper_candidates = [
        c for c in res.all_evaluated_candidates if c.cost_eur < best.cost_eur
    ]
    assert len(cheaper_candidates) > 0, "Deben existir opciones de menor coste que resultaron inviables"

    for c in cheaper_candidates:
        assert c.passes_all is False, (
            f"El candidato ({c.L_x}x{c.L_y}x{c.thickness}) con coste {c.cost_eur:.2f} < óptimo {best.cost_eur:.2f} "
            f"no debió pasar los chequeos: {c.failure_reasons}"
        )
        assert len(c.failure_reasons) > 0

    # 3. Todos los candidatos válidos tienen coste >= coste óptimo
    passed_candidates = [c for c in res.all_evaluated_candidates if c.passes_all]
    assert len(passed_candidates) == res.total_passed
    for c in passed_candidates:
        assert c.cost_eur >= best.cost_eur - 1e-9
