"""GOLDEN — curva U vs Tv de la consolidacion 1D de Terzaghi.

Modulo bajo prueba: ``foundationdesignjm.analysis.consolidacion_1d``.

FUENTE (solucion en serie publicada + su tabla):
    Terzaghi, K. (1943), "Theoretical Soil Mechanics", Wiley, cap. XIII
    (teoria de la consolidacion unidimensional). La solucion en serie es

        U(Tv) = 1 - sum_{m=0..inf} (2/M^2) * exp(-M^2 * Tv),  M = pi(2m+1)/2

    Tabulada en B. M. Das, "Principles of Foundation Engineering", tabla
    "Variation of time factor with degree of consolidation", y en
    Terzaghi-Peck-Mesri, "Soil Mechanics in Engineering Practice", 3a ed.,
    tabla de Uv vs Tv. Valores publicados (Tv redondeado a 3 decimales):

        U (%)   10     20     30     40     50     60     70     80     90
        Tv      0.008  0.031  0.071  0.126  0.197  0.286  0.403  0.567  0.848

APROXIMACIONES QUE USA LA IMPLEMENTACION (las mismas que publica la fuente
como formas cerradas de esa tabla):

    U <  60 %:  Tv = (pi/4) * U^2                      (rama parabolica)
    U >= 60 %:  Tv = -(4/pi^2) * ln[(1-U) * pi^2/8]    (primer termino de la serie)

DESARROLLO ESCRITO de los dos puntos que pide la campana:

  U = 50 % -> Tv = (pi/4)(0.5)^2 = 0.7853982 * 0.25 = 0.1963495
      El valor tabulado es 0.197. La diferencia (0.00065, 0.33 %) NO es ruido
      numerico: es el error conocido de la rama parabolica, que solo es exacta
      hasta U ~ 52-53 %. Por eso la tolerancia es abs=1e-3 y no rel=1e-6.
      El test asevera AMBOS numeros: el tabulado (con abs=1e-3) y el exacto
      de la rama parabolica (con rel=1e-9).

  U = 90 % -> Tv = -(4/pi^2) * ln(0.10 * pi^2/8)
              pi^2/8 = 1.2337006 ; 0.10 * 1.2337006 = 0.12337006
              ln(0.12337006) = -2.0925669
              4/pi^2 = 0.4052847
              Tv = 0.4052847 * 2.0925180 = 0.8480854
      Valor tabulado 0.848 -> coincide a las 3 decimales publicadas.
"""
from __future__ import annotations

import math

import pytest

from foundationdesignjm.analysis.consolidacion_1d import (
    ConsolidationInput,
    Tv_from_U,
    U_from_Tv,
    consolidate,
)


# (U, Tv publicado en la tabla de Terzaghi)
TABLA_U_TV = [
    (0.10, 0.008),
    (0.20, 0.031),
    (0.30, 0.071),
    (0.40, 0.126),
    (0.60, 0.286),
    (0.70, 0.403),
    (0.80, 0.567),
]


def test_golden_tv_para_u_50_terzaghi() -> None:
    """Tv(U=50%) = 0.197 publicado; 0.1963495 exacto de la rama parabolica."""
    tv_exacto_parabolico = (math.pi / 4.0) * 0.5 ** 2
    assert tv_exacto_parabolico == pytest.approx(0.19634954, abs=1e-8)

    tv = Tv_from_U(0.50)
    # (a) coincide con la forma cerrada derivada arriba, a maquina.
    assert tv == pytest.approx(tv_exacto_parabolico, rel=1e-9)
    # (b) coincide con el valor tabulado 0.197 dentro del error conocido
    #     de la rama parabolica (0.00065).
    assert tv == pytest.approx(0.197, abs=1e-3)
    assert abs(tv - 0.197) < 1.0e-3


def test_golden_tv_para_u_90_terzaghi() -> None:
    """Tv(U=90%) = 0.848 publicado; 0.8480854 del primer termino de la serie."""
    tv_exacto_serie = -(4.0 / math.pi ** 2) * math.log(0.10 * math.pi ** 2 / 8.0)
    assert tv_exacto_serie == pytest.approx(0.84808541, abs=1e-8)

    tv = Tv_from_U(0.90)
    assert tv == pytest.approx(tv_exacto_serie, rel=1e-9)
    assert tv == pytest.approx(0.848, abs=1e-3)


@pytest.mark.parametrize("U,Tv_pub", TABLA_U_TV)
def test_golden_tabla_completa_u_tv(U: float, Tv_pub: float) -> None:
    """Resto de la tabla publicada de Terzaghi, a la resolucion de la fuente
    (3 decimales -> abs = 5e-4).
    """
    assert Tv_from_U(U) == pytest.approx(Tv_pub, abs=5e-4)


def test_golden_u_from_tv_inverso_en_los_dos_anclajes() -> None:
    """La funcion directa U(Tv) debe devolver los U de la tabla.

    U(Tv = 0.848) = 1 - (8/pi^2) exp(-pi^2 * 0.848/4)
                  = 1 - 0.8105695 * exp(-2.0923561)
                  = 1 - 0.8105695 * 0.1233961 = 0.8999789  -> 90.0 %

    U(Tv = 0.197): la implementacion usa la rama parabolica para Tv < 0.2,
        U = sqrt(4*0.197/pi) = sqrt(0.2508282) = 0.5008275  -> 50.08 %
        (mismo error de la rama parabolica ya documentado arriba).
    """
    u90 = 1.0 - (8.0 / math.pi ** 2) * math.exp(-math.pi ** 2 * 0.848 / 4.0)
    assert u90 == pytest.approx(0.8999789, abs=1e-6)
    assert U_from_Tv(0.848) == pytest.approx(u90, rel=1e-9)
    assert U_from_Tv(0.848) == pytest.approx(0.90, abs=1e-4)

    u50 = math.sqrt(4.0 * 0.197 / math.pi)
    assert u50 == pytest.approx(0.5008275, abs=1e-6)
    assert U_from_Tv(0.197) == pytest.approx(u50, rel=1e-9)
    assert U_from_Tv(0.197) == pytest.approx(0.50, abs=1e-3)


def test_golden_asentamiento_y_tiempos_calculo_a_mano() -> None:
    """Zapata sobre arcilla NC — calculo a mano completo.

    Datos: H = 4.00 m, drenaje doble, sigma'_v0 = 100 kPa, delta_sigma = 100 kPa,
           Cc = 0.30, e0 = 0.80, OCR = 1.0, cv = 2.0 m2/ano.

    Asentamiento primario (arcilla normalmente consolidada, sigma'_p = sigma'_v0):
        Sc = Cc/(1+e0) * H * log10(sigma'_f / sigma'_v0)
           = 0.30/1.80 * 4.00 * log10(200/100)
           = 0.1666667 * 4.00 * 0.3010300
           = 0.2006867 m = 200.69 mm

    Tiempos (H_dr = H/2 = 2.00 m con drenaje doble, t = Tv*H_dr^2/cv):
        t50 = 0.1963495 * 2.00^2 / 2.0 = 0.3926991 anos = 143.34 dias (365 d/ano)
        t90 = 0.8480854 * 2.00^2 / 2.0 = 1.6961708 anos = 619.10 dias
    """
    res = consolidate(ConsolidationInput(
        H_layer_m=4.0,
        sigma_v0_kPa=100.0,
        delta_sigma_kPa=100.0,
        Cc=0.30,
        e0=0.80,
        cv_m2_per_year=2.0,
        drainage="double",
        OCR=1.0,
    ))
    assert res.Sc_mm == pytest.approx(200.69, abs=0.01)
    assert res.Tv_50 == pytest.approx(0.1963495, abs=1e-6)
    assert res.Tv_90 == pytest.approx(0.8480854, abs=1e-6)
    assert res.t_50_days == pytest.approx(143.34, abs=0.01)
    assert res.t_90_days == pytest.approx(619.10, abs=0.01)
