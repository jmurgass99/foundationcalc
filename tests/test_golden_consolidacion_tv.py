"""Golden de la curva U-Tv de Terzaghi, y la guarda contra la duplicacion.

DEFECTO CORREGIDO
-----------------
`foundationdesignjm/consolidacion_1d.py::_Tv_from_U` calculaba la rama alta como

    -(4/pi^2) * log10(1 - U) * 2.303        # ~ -(4/pi^2)*ln(1-U)

es decir, SIN el factor pi^2/8 dentro del logaritmo. Daba Tv90 = 0.9334 en vez
de 0.8481: un +10.1 % en todos los tiempos de consolidacion, en la direccion de
predecir asentamientos mas lentos de lo real.

Lo revelador es que la version CORRECTA ya vivia en el mismo paquete, en
`analysis/consolidacion_1d.py::Tv_from_U`. Dos modulos duplicados con las mismas
clases y campos distintos (`sigma_v0_kPa` vs `sigma_v_0_kPa`), y la formula
divergio en uno de los dos sin que nada lo notara. Por eso el test que mas vale
de este fichero no es el golden, sino
`test_una_sola_fuente_de_verdad_para_Tv`: la duplicacion sigue ahi y esto es lo
unico que impide que vuelva a separarse.

FUENTE
------
Terzaghi (1943), solucion de la consolidacion unidimensional. Inversa de la
curva U-Tv:

    U <  0.6 :  Tv = (pi/4)*U^2
    U >= 0.6 :  Tv = -(4/pi^2)*ln[(1-U)*pi^2/8]
"""
from __future__ import annotations

import math

import pytest

from foundationdesignjm.analysis.consolidacion_1d import Tv_from_U, U_from_Tv
from foundationdesignjm.consolidacion_1d import (
    ConsolidationInput,
    _Tv_from_U,
    evaluate_consolidation,
)


def test_golden_Tv50_rama_baja():
    """GOLDEN — Tv50 = (pi/4)*0.5^2 = pi/16 = 0.196349540849."""
    assert _Tv_from_U(0.5) == pytest.approx(math.pi / 16.0, rel=1e-12)
    assert _Tv_from_U(0.5) == pytest.approx(0.196349540849, rel=1e-11)


def test_golden_Tv90_rama_alta():
    """GOLDEN — Tv90 = -(4/pi^2)*ln(0.1*pi^2/8) = 0.848085405629.

    Es el valor tabulado clasico (0.848). El defecto corregido daba 0.9334.
    """
    esperado = -(4.0 / math.pi ** 2) * math.log(0.1 * math.pi ** 2 / 8.0)
    assert esperado == pytest.approx(0.848085405629, rel=1e-11)
    assert _Tv_from_U(0.9) == pytest.approx(esperado, rel=1e-12)

    # Y el valor defectuoso queda explicitamente descartado.
    defectuoso = -(4.0 / math.pi ** 2) * math.log10(1 - 0.9) * 2.303
    assert defectuoso == pytest.approx(0.9334, rel=1e-3)
    assert _Tv_from_U(0.9) != pytest.approx(defectuoso, rel=1e-3)


def test_una_sola_fuente_de_verdad_para_Tv():
    """EL TEST QUE SOSTIENE LA CORRECCION.

    Los dos modulos de consolidacion coexisten. Mientras coexistan, sus curvas
    U-Tv tienen que coincidir en todo el dominio: fue justo su divergencia
    silenciosa la que produjo el defecto.
    """
    for U in [0.05, 0.2, 0.4, 0.55, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]:
        assert _Tv_from_U(U) == pytest.approx(Tv_from_U(U), rel=1e-12), (
            f"las dos implementaciones de Tv(U) divergen en U = {U}"
        )


def test_U_y_Tv_son_inversas_en_la_rama_alta():
    """Invariante: U(Tv(U)) = U. Una constante equivocada dentro del logaritmo
    rompe esta identidad, que es lo que pasaba antes."""
    for U in [0.6, 0.7, 0.8, 0.9, 0.95]:
        assert U_from_Tv(Tv_from_U(U)) == pytest.approx(U, rel=1e-9)


def test_la_curva_es_monotona_creciente():
    Us = [0.1, 0.3, 0.5, 0.59, 0.6, 0.75, 0.9, 0.99]
    Tvs = [_Tv_from_U(u) for u in Us]
    assert all(b > a for a, b in zip(Tvs, Tvs[1:])), Tvs


def test_los_tiempos_de_consolidacion_usan_la_Tv_corregida():
    """t = Tv*H_dr^2/cv. Con H = 3 m, drenaje doble (H_dr = 1.5 m) y
    cv = 1.2 m^2/ano:

        t90 = 0.848085405629 * 1.5^2 / 1.2 * 365.25 = 580.805990 dias

    Con la Tv defectuosa habrian salido 639.2 dias (+10.1 %).
    """
    res = evaluate_consolidation(ConsolidationInput(
        H_layer_m=3.0, sigma_v_0_kPa=80.0, delta_sigma_kPa=100.0,
        Cc=0.25, e_0=0.80, cv_m2_per_year=1.2, drainage="double",
    ))
    assert res.H_drainage_m == pytest.approx(1.5)
    esperado = 0.848085405629 * 1.5 ** 2 / 1.2 * 365.25
    assert esperado == pytest.approx(580.805990, rel=1e-6)
    assert res.t_90pct_days == pytest.approx(esperado, rel=1e-9)
