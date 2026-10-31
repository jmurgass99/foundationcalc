"""GOLDEN — factor de influencia de Newmark/Fadum bajo esquina de rectangulo.

Modulo bajo prueba: ``foundationcalc.analysis.boussinesq``.

FUENTE (solucion cerrada publicada, reproducida y derivada aqui):
    Newmark, N. M. (1935), "Simplified computation of vertical pressures in
    elastic foundations", Univ. of Illinois Eng. Exp. Station Circular 24;
    tabulada por Fadum, R. E. (1948), "Influence values for estimating stress
    in elastic foundations", Proc. 2nd ICSMFE, Rotterdam, Vol. 3, pp. 77-84.
    Reproducida en B. M. Das, "Principles of Foundation Engineering",
    ecuacion del factor de influencia bajo esquina y su tabla de valores I(m,n)
    (tabla "Variation of influence value I with m and n").

    Con m = B/z, n = L/z, V = m^2 + n^2 + 1, V1 = m^2 * n^2:

        I = 1/(4*pi) * [ 2*m*n*sqrt(V)/(V + V1) * (V + 1)/V
                         + arctan( 2*m*n*sqrt(V)/(V - V1) ) ]

    y el arctan se toma en (0, pi): si (V - V1) < 0 se suma pi.

VALORES DE REFERENCIA (tabulados; recalculados aqui con la formula cerrada
para dejar el desarrollo escrito):

  (m, n)      V        V1     V - V1   rama        I publicado   I formula
  (0.5,0.5)  1.50     0.0625  +1.4375  arctan>0      0.0840       0.084027
  (1.0,1.0)  3.00     1.0000  +2.0000  arctan>0      0.1752       0.175221
  (1.0,2.0)  6.00     4.0000  +2.0000  arctan>0      0.1999       0.199941
  (2.0,2.0)  9.00    16.0000  -7.0000  +pi           0.2325       0.232466

Desarrollo explicito para (m, n) = (1, 1):
    V = 1 + 1 + 1 = 3 ; V1 = 1
    2*m*n*sqrt(V) = 2*sqrt(3) = 3.464102
    termino 1 = 3.464102/(3+1) * (3+1)/3 = 0.866025 * 1.333333 = 1.154701
    arctan(3.464102/(3-1)) = arctan(1.732051) = 1.047198 rad  (= pi/3)
    I = (1.154701 + 1.047198)/(4*pi) = 2.201899/12.566371 = 0.175221

El caso (2, 2) es el unico que ejerce la rama "+pi" (V - V1 = -7 < 0);
se conserva deliberadamente por eso.

HISTORIA: hasta esta campana ``influence_corner`` devolvia I(1,1) = 0.12571
(-28 % frente a 0.1752) por usar (V + V1) donde la formula pide V y (V - V1).
El unico test que la tocaba (``test_ideas20_group_abc.py``) solo comprobaba
``0 < sigma <= qo``, de modo que el error pasaba desapercibido.
"""
from __future__ import annotations

import math

import pytest

from foundationcalc.analysis.boussinesq import (
    BoussinesqRect,
    influence_corner,
    sigma_z_rect_center,
)
from foundationcalc.analysis.stress import newmark_influence_factor


# (m, n, I publicado en la tabla de Fadum/Newmark a 4 decimales,
#  I de la forma cerrada del docstring del modulo a 6 decimales)
CASOS_MN = [
    (0.5, 0.5, 0.0840, 0.084027),
    (1.0, 1.0, 0.1752, 0.175221),
    (1.0, 2.0, 0.1999, 0.199941),
    (2.0, 2.0, 0.2325, 0.232466),
]


@pytest.mark.parametrize("m,n,I_pub,I_formula", CASOS_MN)
def test_influence_corner_vs_tabla_fadum(m: float, n: float, I_pub: float,
                                          I_formula: float) -> None:
    """I(m,n) bajo esquina frente a la tabla publicada (z = 1 m => m = B, n = L).

    Se aseveran LAS DOS columnas del docstring del modulo:
      - el valor tabulado, con abs=5e-5 (la tabla esta a 4 decimales, asi que
        +/-0.00005 es la resolucion de la fuente, no un margen de ajuste);
      - el valor de la forma cerrada escrito en el docstring, con abs=5e-7
        (resolucion de los 6 decimales que ahi se dan).
    """
    assert influence_corner(m, n, 1.0) == pytest.approx(I_pub, abs=5e-5)
    assert influence_corner(m, n, 1.0) == pytest.approx(I_formula, abs=5e-7)


@pytest.mark.parametrize("m,n,I_pub,I_formula", CASOS_MN)
def test_influence_corner_coincide_con_stress_py(m: float, n: float, I_pub: float,
                                                  I_formula: float) -> None:
    """Las dos implementaciones del repo (analysis.boussinesq y analysis.stress)
    deben dar el mismo I. Divergieron durante meses; este test lo impide.
    """
    assert influence_corner(m, n, 1.0) == pytest.approx(
        newmark_influence_factor(m, n, 1.0), rel=1e-12
    )


def test_influence_corner_1_1_valor_derivado_inline() -> None:
    """Valor exacto derivado en el docstring del modulo de test.

        I(1,1) = (2*sqrt(3)/4 * 4/3 + pi/3) / (4*pi) = 0.1752215...

    Se asevera el numero derivado, no solo el tabulado.
    """
    I_exacto = (2 * math.sqrt(3) / 4.0 * (4.0 / 3.0) + math.pi / 3.0) / (4 * math.pi)
    assert I_exacto == pytest.approx(0.17522148, abs=1e-8)
    assert influence_corner(1.0, 1.0, 1.0) == pytest.approx(I_exacto, rel=1e-12)


def test_sigma_z_centro_cuadrado_B_igual_2z() -> None:
    """sigma_z bajo el CENTRO de una zapata cuadrada B = L = 2 m a z = 1 m.

    Por superposicion de 4 cuadrantes de B/2 = L/2 = 1 m:
        m = n = (B/2)/z = 1  ->  I = 0.175221 (tabla: 0.1752)
        sigma_z = 4 * qo * I = 4 * 100 kPa * 0.175221 = 70.09 kPa
    """
    sigma = sigma_z_rect_center(BoussinesqRect(qo_kPa=100.0, B_m=2.0, L_m=2.0, z_m=1.0))
    assert sigma == pytest.approx(70.088, abs=0.02)


def test_influence_corner_tiende_a_025_para_area_infinita() -> None:
    """Limite teorico: bajo esquina de un area cargada infinita, I -> 1/4
    (la esquina 've' un cuarto del semiespacio cargado).
    """
    assert influence_corner(500.0, 500.0, 1.0) == pytest.approx(0.25, abs=1e-3)
