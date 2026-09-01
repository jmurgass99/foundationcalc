"""Golden test para detección de solape y sustitución por zapata combinada.

Caso de derivación analítica a mano:
-------------------------------------
Dos columnas adyacentes C1 y C2 con separación entre ejes s = 2.00 m.
Capacidad portante admisible del terreno: q_adm = 200.0 kPa.
Cargas axiales de servicio:
    C1: N1 = 800.0 kN
    C2: N2 = 1200.0 kN

1. Dimensionado aislado independiente:
    Zapata C1: A1 = 800 / 200 = 4.00 m² -> B1 = L1 = 2.00 m. Ocupa [-1.00 m, +1.00 m] en X.
    Zapata C2: A2 = 1200 / 200 = 6.00 m² -> B2 = L2 = 2.45 m. Ocupa [2.00 - 1.225, 2.00 + 1.225] = [0.775 m, 3.225 m] en X.
    Solape geométrico:
        B1/2 + B2/2 = 1.00 + 1.225 = 2.225 m > Separación (2.00 m).
        Existe solape real de 0.225 m (más el margen de clearance).

2. Sustitución por Zapata Combinada:
    Carga total: R = N1 + N2 = 800 + 1200 = 2000.0 kN.
    Posición de la resultante desde C1:
        x_R = (N2 * s) / R = (1200 * 2.00) / 2000 = 1.20 m.
    Área requerida:
        A_req = R / q_adm = 2000 / 200 = 10.00 m².

3. Verificación de sustitución en el paquete de entregables:
    - Las zapatas aisladas C1 y C2 son sustituidas por COMB_C1_C2.
    - Se verifica la conservación del equilibrio y la no coexistencia de aisladas solapadas.
"""
from __future__ import annotations

import math
import pytest
from jmstructural_common.model import Reaction
from foundationdesignjm.integration.foundation_chain import (
    foundation_package,
    _detect_and_design_combined_footings,
)
from foundationdesignjm.core.material import Concrete, ReinforcingSteel


def test_golden_combined_footing_overlap_detection_and_substitution():
    """GOLDEN. Derivación analítica cerrada de solape y sustitución combinada."""
    reactions = [
        Reaction(node_id="C1", case="ELU_1", fz_kN=800.0),
        Reaction(node_id="C2", case="ELU_1", fz_kN=1200.0),
    ]
    col_coords = {"C1": (0.0, 0.0), "C2": (2.0, 0.0)}
    soil_params = {"allowable_bearing_kPa": 200.0}

    pkg = foundation_package(
        etabs_or_reactions=reactions,
        soil_params=soil_params,
        column_coordinates=col_coords,
        substitute_overlapping_footings=True,
    )

    # 1. Detección del solape
    assert len(pkg.combined_footings) == 1
    cf = pkg.combined_footings[0]

    # Derivación a mano de la resultante y área requerida
    assert cf.A_required_m2 == pytest.approx(10.0, abs=1e-3)
    assert cf.x_resultant_m == pytest.approx(1.20, abs=1e-3)

    # 2. Sustitución efectiva en el resumen de diseño
    assert "C1" not in pkg.design_summary, "La zapata aislada C1 debe haber sido sustituida"
    assert "C2" not in pkg.design_summary, "La zapata aislada C2 debe haber sido sustituida"
    assert "COMB_C1_C2" in pkg.design_summary, "Debe existir la zapata combinada COMB_C1_C2"

    comb_summary = pkg.design_summary["COMB_C1_C2"]
    assert comb_summary["N_max_kN"] == 2000.0
    assert comb_summary["is_combined"] is True
    assert comb_summary["combined_nodes"] == ["C1", "C2"]

    # 3. La memoria Markdown documenta la combinada
    assert "Zapatas Combinadas por Solape" in pkg.memoria_markdown
    assert "COMB_C1_C2" in pkg.memoria_markdown or "Combinada" in pkg.memoria_markdown
