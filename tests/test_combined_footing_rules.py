"""TDD — reglas de sustitución por zapata combinada (foundation_chain).

MEDIDO el 2026-09-05 con el pipeline maestro de fastsap (planta 1×1, 2 plantas,
4 columnas de ~144 kN a 4.5 m, qa = 250 kPa): las cuatro zapatas aisladas NO
convergían (5.0-5.3 m de lado por excentricidad sísmica y deslizamiento;
estados SWITCH_A_PILOTES / SLIDING_GOVERNS) y, aun así, la detección de solape
las sustituyó por SEIS zapatas combinadas -- una por cada par de columnas,
incluidas las dos diagonales a 6.36 m -- de 0.17 a 0.24 m de ANCHO y 4.9 a 6.8 m
de largo, todas con estado "OK (ZAPATA COMBINADA POR SOLAPE)". Cada columna
aparecía en tres zapatas a la vez. Cimentaciones imposibles con un OK.

Tres defectos, tres reglas:
  1. Sólo se combinan zapatas aisladas que CONVERGIERON. Combinar no arregla un
     deslizamiento ni una excentricidad que ya desbordó el tamaño máximo.
  2. Un nodo participa como mucho en UNA combinada (la de menor separación).
  3. Una combinada tiene que ser construible: ancho >= columna + 0.30 m y largo
     >= separación + columna. Si no, NO se sustituye y se deja constancia.
"""
from __future__ import annotations

from foundationcalc._common.model import Reaction

from foundationcalc.design.combined_footing import CombinedFootingResult
from foundationcalc.integration.foundation_chain import (
    _combined_footing_is_plausible,
    foundation_package,
)


def _pkg(reactions, coords, qa=200.0):
    return foundation_package(
        etabs_or_reactions=reactions,
        soil_params={"allowable_bearing_kPa": qa},
        column_coordinates=coords,
    )


def _combinadas(pkg):
    return {k: v for k, v in pkg.design_summary.items() if v.get("is_combined")}


# --- regla 1: sólo convergidas ------------------------------------------------------

def test_no_se_combinan_zapatas_que_no_convergieron():
    # Cuatro columnas a 4.5 m con axial pequeña y momentos/cortantes grandes: las
    # aisladas se disparan al tamaño máximo (no convergen). Antes salían 6 combinadas.
    coords = {"A": (0.0, 0.0), "B": (4.5, 0.0), "C": (0.0, 4.5), "D": (4.5, 4.5)}
    reactions = [
        Reaction(node_id=n, case="SISMO", fz_kN=144.0, fx_kN=120.0, fy_kN=120.0,
                 mx_kNm=400.0, my_kNm=400.0)
        for n in coords
    ]
    pkg = _pkg(reactions, coords, qa=250.0)
    assert _combinadas(pkg) == {}, "combinar no arregla una aislada que no convergió"
    assert set(pkg.design_summary) == set(coords), "una zapata por columna, con su estado honesto"
    assert all(not str(v["status"]).startswith("OK (ZAPATA COMBINADA") for v in pkg.design_summary.values())


# --- regla 2: un nodo, una combinada como mucho ------------------------------------

def test_un_nodo_participa_como_mucho_en_una_combinada():
    # Tres columnas en fila a 2.0 m, cargas que hacen solapar a las vecinas.
    coords = {"C1": (0.0, 0.0), "C2": (2.0, 0.0), "C3": (4.0, 0.0)}
    reactions = [
        Reaction(node_id="C1", case="ELU", fz_kN=800.0),
        Reaction(node_id="C2", case="ELU", fz_kN=1200.0),
        Reaction(node_id="C3", case="ELU", fz_kN=800.0),
    ]
    pkg = _pkg(reactions, coords)
    comb = _combinadas(pkg)
    assert comb, "las vecinas a 2.0 m solapan: debe haber al menos una combinada"
    usados = [n for v in comb.values() for n in v["combined_nodes"]]
    assert len(usados) == len(set(usados)), f"un nodo aparece en dos combinadas: {usados}"
    # Los nodos no combinados siguen con su zapata aislada: ninguna columna se queda sin cimentación.
    cubiertos = set(usados) | {k for k in pkg.design_summary if k in coords}
    assert cubiertos == set(coords)


def test_la_pareja_elegida_es_la_de_menor_separacion():
    # C2 solapa con C1 (1.8 m) y con C3 (2.2 m): se combina con la más cercana, C1.
    coords = {"C1": (0.0, 0.0), "C2": (1.8, 0.0), "C3": (4.0, 0.0)}
    reactions = [
        Reaction(node_id="C1", case="ELU", fz_kN=900.0),
        Reaction(node_id="C2", case="ELU", fz_kN=1200.0),
        Reaction(node_id="C3", case="ELU", fz_kN=900.0),
    ]
    pkg = _pkg(reactions, coords)
    comb = _combinadas(pkg)
    assert any(set(v["combined_nodes"]) == {"C1", "C2"} for v in comb.values()), comb
    assert not any("C3" in v["combined_nodes"] and "C2" in v["combined_nodes"] for v in comb.values())


# --- regla 3: construible ----------------------------------------------------------

def _cf(B, L):
    return CombinedFootingResult(shape="rectangular", L_m=L, B_m=B)


def test_una_combinada_de_17_cm_de_ancho_no_es_construible():
    ok, motivo = _combined_footing_is_plausible(_cf(B=0.17, L=6.8), column_size_m=0.40, spacing_m=6.36)
    assert ok is False
    assert "ancho" in motivo.lower()


def test_una_combinada_mas_corta_que_la_separacion_no_es_construible():
    ok, motivo = _combined_footing_is_plausible(_cf(B=1.2, L=2.0), column_size_m=0.40, spacing_m=2.2)
    assert ok is False
    assert "largo" in motivo.lower()


def test_una_combinada_razonable_si_es_construible():
    ok, motivo = _combined_footing_is_plausible(_cf(B=3.6, L=2.8), column_size_m=0.40, spacing_m=2.0)
    assert ok is True and motivo == ""


# --- la golden existente sigue valiendo: dos columnas a 2 m se combinan -------------

def test_dos_columnas_que_solapan_siguen_combinandose():
    coords = {"C1": (0.0, 0.0), "C2": (2.0, 0.0)}
    reactions = [Reaction(node_id="C1", case="ELU_1", fz_kN=800.0), Reaction(node_id="C2", case="ELU_1", fz_kN=1200.0)]
    pkg = _pkg(reactions, coords)
    assert len(pkg.combined_footings) == 1
    assert list(_combinadas(pkg).values())[0]["combined_nodes"] == ["C1", "C2"]
