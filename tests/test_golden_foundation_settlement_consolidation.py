"""Golden test para integración de asentamientos Boussinesq + Consolidación 1D en entregables de cimentación.

Derivación analítica cerrada (Boussinesq 1885 + Terzaghi 1943):
---------------------------------------------------------------
Zapata con carga axial de servicio N = 1000.0 kN, cimentada a D_f = 1.50 m.
Estrato compresible de arcilla con espesor H = 3.00 m inmediatamente bajo la cimentación.
Profundidad al plano medio del estrato: z_mid = D_f + H/2 = 1.50 + 1.50 = 3.00 m.

1. Incremento de esfuerzo vertical por Boussinesq bajo el centro (r = 0):
    Δσ_v = (3 · N) / (2 · π · z²)
         = (3 · 1000) / (2 · π · 3.00²) = 3000 / (18 · π) = 500 / (3 · π)
         = 53.051647697... kPa

2. Esfuerzos efectivos:
    σ'_v0 = 80.0 kPa
    σ'_vf = σ'_v0 + Δσ_v = 80.0 + 53.051647697 = 133.051647697 kPa

3. Asentamiento por consolidación primaria (Terzaghi 1D):
    Parámetros: Cc = 0.25, e0 = 0.80
    S_c = [Cc / (1 + e0)] · H · log10(σ'_vf / σ'_v0)
        = [0.25 / 1.80] · 3.00 · log10(133.051647697 / 80.0)
        = (0.75 / 1.80) · log10(1.663145596)
        = 0.41666667 · 0.220931535 = 0.0920548 m = 92.0548 mm.

4. Verificación en la memoria de entregables de FoundationDesignJm.
"""
from __future__ import annotations

import math
import pytest
from jmstructural_common.model import Reaction
from foundationdesignjm.integration.foundation_chain import (
    foundation_package,
    foundation_chain_from_etabs,
)


def test_golden_boussinesq_and_consolidation_in_foundation_package():
    """GOLDEN. Asentamiento por Boussinesq + Consolidación 1D en entregable FDJM."""
    reactions = [Reaction(node_id="COL1", case="ELU_1", fz_kN=1000.0)]
    soil_params = {
        "allowable_bearing_kPa": 200.0,
        "founding_depth_m": 1.50,
        "compressible_layer": {
            "H_layer_m": 3.00,
            "sigma_v_0_kPa": 80.0,
            "Cc": 0.25,
            "e_0": 0.80,
            "cv_m2_per_year": 1.20,
        }
    }

    pkg = foundation_package(
        etabs_or_reactions=reactions,
        soil_params=soil_params,
    )

    # 1. Resultados numéricos exactos de asentamiento
    assert "COL1" in pkg.settlement_results
    s_res = pkg.settlement_results["COL1"]

    # Derivación a mano:
    z_mid = 1.50 + 1.50  # 3.0 m
    delta_sigma = (3.0 * 1000.0) / (2.0 * math.pi * (z_mid ** 2))
    assert delta_sigma == pytest.approx(53.051648, rel=1e-4)

    expected_Sc_mm = (0.25 / 1.80) * 3.0 * math.log10((80.0 + delta_sigma) / 80.0) * 1000.0
    assert expected_Sc_mm == pytest.approx(92.0548, rel=1e-3)
    assert s_res.Sc_mm == pytest.approx(expected_Sc_mm, abs=0.01)

    # 2. Integración en la memoria Markdown técnica
    assert "Asentamiento por Consolidación 1D" in pkg.memoria_markdown
    assert f"{s_res.Sc_mm:.2f}" in pkg.memoria_markdown
