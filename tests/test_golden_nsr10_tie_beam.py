"""Golden test de vigas de amarre segun NSR-10 Articulo A.3.6.4.2.

Fuente normativa
----------------
NSR-10 (Reglamento Colombiano de Construccion Sismo Resistente), Titulo A,
Articulo A.3.6.4.2 — "Vigas de amarre en la cimentacion". Texto del articulado:

    "...una fuerza no menor de 0,25*A_a veces la carga vertical total del
    elemento que tenga la mayor carga entre los que interconecta, ademas de las
    fuerzas que le transmita la superestructura."

EL COEFICIENTE ES UNICO Y NO ESTA ZONIFICADO
--------------------------------------------
La version anterior de este test aseveraba como EXACTOS dos numeros que la norma
citada no contiene:

    assert res_inter.axial_force_Tu_kN == pytest.approx(168.0, abs=1e-5)

Ese 168.0 salia de aplicar 0.20 en "amenaza intermedia", con 0.15 para "baja".
Esa gradacion NO EXISTE en NSR-10: A.3.6.4.2 da un coeficiente unico, sin
zonificacion y sin exencion para amenaza baja (comprobado tambien contra
A.3.6.5-A.3.6.13 y A.3.7). La gradacion de tres niveles que probablemente la
inspiro es la de C.15.13.3.1, y es de DIMENSION MINIMA segun capacidad de
disipacion (DES L/20, DMO L/30, DMI L/40), no del coeficiente sismico.

Un numero fabricado, envuelto en una cita normativa correcta y aseverado al
microgramo, es el patron exacto que esta campana persigue. Por eso el test que
mas importa aqui es `test_el_coeficiente_no_depende_de_la_zona`: es el unico que
falla si alguien reintroduce la gradacion.

Derivacion a mano
-----------------
P = 2400.0 kN (carga vertical total del elemento de cimentacion mas cargado),
Aa = 0.35, L = 5.00 m, f'c = 21.0 MPa, fy = 420.0 MPa.

    Tu = Cu = 0.25 * Aa * P = 0.25 * 0.35 * 2400.0 = 210.00 kN EXACTAMENTE
    As_tension = Tu/(phi*fy) = 210000 N / (0.90 * 420.0 MPa) = 555.5556 mm^2
"""
from __future__ import annotations

import pytest

from foundationcalc.design.strap_beam import (
    NSR10_TIE_BEAM_FACTOR,
    design_tie_beam_nsr10,
)

PU_KN = 2400.0
AA = 0.35
L_M = 5.0


def test_golden_nsr10_tie_beam_axial_force_exact():
    """GOLDEN — Tu = 0.25*Aa*P = 210.00 kN exactamente (NSR-10 A.3.6.4.2)."""
    res = design_tie_beam_nsr10(
        Pu_col_max_kN=PU_KN, Aa=AA, length_m=L_M, seismic_zone="alta",
    )

    assert res.code_article == "NSR-10 Artículo A.3.6.4.2"
    assert res.axial_force_Tu_kN == 210.0
    assert res.axial_force_Cu_kN == 210.0
    assert res.As_tension_mm2 == pytest.approx(555.5556, rel=1e-4)
    assert res.n_bars >= 4
    assert res.As_provided_mm2 >= res.As_tension_mm2


@pytest.mark.parametrize(
    "zona", ["alta", "intermedia", "baja", "high", "medium", "low", "CUALQUIERA"]
)
def test_el_coeficiente_no_depende_de_la_zona(zona):
    """EL TEST QUE SOSTIENE LA CORRECCION.

    NSR-10 A.3.6.4.2 no zonifica el coeficiente, asi que la fuerza debe salir
    identica sea cual sea la zona declarada. Si alguien reintroduce la gradacion
    0.25/0.20/0.15, "intermedia" daria 168.0 y "baja" 126.0, y este test lo caza.
    """
    res = design_tie_beam_nsr10(
        Pu_col_max_kN=PU_KN, Aa=AA, length_m=L_M, seismic_zone=zona,
    )
    assert res.axial_force_Tu_kN == 210.0, (
        f"la zona '{zona}' cambio la fuerza axial: el coeficiente de "
        f"A.3.6.4.2 es unico y no depende de la amenaza sismica"
    )
    # La zona se reporta, pero no interviene.
    assert res.seismic_zone == zona
    assert "no la zonifica" in res.note or "ÚNICO" in res.note


def test_la_constante_es_la_del_articulado():
    assert NSR10_TIE_BEAM_FACTOR == 0.25


def test_la_fuerza_es_lineal_en_Aa_y_en_P():
    """Invariante de la formula: Tu = 0.25*Aa*P es lineal en ambos factores."""
    base = design_tie_beam_nsr10(Pu_col_max_kN=1000.0, Aa=0.20, length_m=L_M)
    doble_P = design_tie_beam_nsr10(Pu_col_max_kN=2000.0, Aa=0.20, length_m=L_M)
    doble_Aa = design_tie_beam_nsr10(Pu_col_max_kN=1000.0, Aa=0.40, length_m=L_M)

    assert base.axial_force_Tu_kN == pytest.approx(0.25 * 0.20 * 1000.0)
    assert doble_P.axial_force_Tu_kN == pytest.approx(2.0 * base.axial_force_Tu_kN)
    assert doble_Aa.axial_force_Tu_kN == pytest.approx(2.0 * base.axial_force_Tu_kN)


def test_la_nota_declara_que_P_no_es_mayorada():
    """El nombre del parametro (Pu_col_max_kN) sugiere carga mayorada de COLUMNA,
    y la norma pide carga vertical TOTAL del ELEMENTO DE CIMENTACION. El nombre
    se conserva por compatibilidad, asi que la aclaracion tiene que viajar con el
    resultado o nadie la vera."""
    res = design_tie_beam_nsr10(Pu_col_max_kN=PU_KN, Aa=AA, length_m=L_M)
    assert "no mayorada" in res.note.lower()
    assert "cimentación" in res.note or "cimentacion" in res.note
