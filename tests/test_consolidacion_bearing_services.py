"""CONSOLIDACIÓN DE CAPACIDAD PORTANTE (BLOQUE D) — FoundationCalc services.

Verifica la delegación hacia la implementación canónica
``foundationcalc.analysis.bearing_capacity`` (EN 1997-1:2004 Anexo D),
asevera la divergencia medida frente a W00675 §4.3 DA1-C1,
y prueba que water_table ya no es un parámetro silenciosamente ignorado (D.2).
"""
from __future__ import annotations

import pytest
import warnings

from foundationcalc.services.bearing import (
    SoilLayerSpec,
    BearingInput,
    BearingResult,
    bearing_capacity_multilayer,
    bearing_capacity_canonical,
)

# Caso W00675 §4.3 DA1-C1: L=2.5, B=1.5, Df=0.5, phi=35, c=0, gamma=18
W00675_INPUT = BearingInput(
    L_x=1.5, L_y=2.5, depth=0.5,
    layers=(SoilLayerSpec(thickness=10.0, gamma=18.0, phi=35.0, c=0.0),),
)
W00675_CANONICAL_Q_ULT = 903.466455


def test_divergencia_medida_services_vs_canonica():
    """Asevera la divergencia medida de bearing_capacity_multilayer frente a la canónica.

    W00675 publicado: 903.5 kPa
    - Canonica: 903.47 kPa (-0.004 %)
    - bearing_capacity_multilayer: 918.34 kPa (+1.64 %)
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", (DeprecationWarning, UserWarning))
        res_serv = bearing_capacity_multilayer(W00675_INPUT)

    assert res_serv.qu_kPa == pytest.approx(918.34, abs=0.5)
    ratio = res_serv.qu_kPa / W00675_CANONICAL_Q_ULT
    assert ratio == pytest.approx(1.0164, abs=1e-3)


def test_delegacion_canonica_services_reproduce_exacto():
    """bearing_capacity_canonical reproduce el valor canónico exacto 903.47 kPa."""
    res_can = bearing_capacity_canonical(W00675_INPUT)
    assert res_can.qu_kPa == pytest.approx(W00675_CANONICAL_Q_ULT, rel=1e-5)
    assert res_can.qa_kPa == pytest.approx(W00675_CANONICAL_Q_ULT / 3.0, rel=1e-5)


def test_deprecation_warning_services():
    """bearing_capacity_multilayer emite DeprecationWarning."""
    with pytest.deprecated_call(match="está deprecada"):
        bearing_capacity_multilayer(W00675_INPUT)


def test_d2_water_table_no_es_cero_silencioso():
    """D.2: water_table ya no se ignora en silencio; emite UserWarning y nota explicativa."""
    inp_con_wt = BearingInput(
        L_x=1.5, L_y=2.5, depth=0.5,
        layers=(SoilLayerSpec(thickness=10.0, gamma=18.0, phi=35.0, c=0.0),),
        water_table=1.0,
    )
    with pytest.warns(UserWarning, match="water_table=1m declarado pero no considerado"):
        res = bearing_capacity_multilayer(inp_con_wt)

    assert any("water_table=1m declarado pero ignorado" in note for note in res.notes)
