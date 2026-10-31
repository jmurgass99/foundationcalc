"""Golden test del asentamiento en la cadena de cimentacion.

QUE ESTABA MAL
--------------
La version anterior de este test derivaba a mano, en su propio docstring, la
solucion de CARGA PUNTUAL de Boussinesq:

    delta_sigma = 3*N/(2*pi*z^2)  con  z = D_f + H/2 = 3.00 m  ->  53.05 kPa

y comprobaba que la implementacion daba eso mismo. Es decir: un "golden" que
aseveraba el metodo equivocado, con la derivacion del metodo equivocado escrita
al lado para dar confianza. Dos errores compuestos:

  1. La carga puntual solo vale para z >~ 2-3B. Aqui B = 2.25 m y z = 1.5 m, es
     decir z/B = 0.67: fuera de rango. (El informe de entrega lo llamaba ademas
     "Boussinesq (bulbo 2:1 / Newmark)", que son TRES metodos distintos citados
     como uno.)
  2. z se medi­a desde la SUPERFICIE del terreno, no desde el plano de aplicacion
     de la carga, que es la base de la zapata — pese a que el propio docstring
     decia "estrato compresible inmediatamente bajo la cimentacion".

Resultado: 53.05 kPa frente a 108.42 reales, y Sc = 92.05 mm frente a 155.02.
Un ~40 % INSEGURO. La implementacion correcta, `sigma_z_rect_center`, ya existia
en `analysis/boussinesq.py` (corregida en 684cf78) y la cadena no la usaba: era
un defecto de cableado, no de capacidad ausente.

DERIVACION A MANO DEL VALOR CORRECTO
------------------------------------
N = 1000 kN de servicio, q_adm = 200 kPa -> la cadena dimensiona B = L = 2.25 m.
Estrato compresible H = 3.00 m inmediatamente bajo la base; se evalua en su plano
medio, z = H/2 = 1.50 m POR DEBAJO DE LA BASE.

Presion de contacto:
    qo = N/(B*L) = 1000/2.25^2 = 1000/5.0625 = 197.530864 kPa

Factor de influencia bajo el CENTRO por superposicion de 4 cuadrantes
(Fadum 1948 / Newmark), con m = n = (B/2)/z = 1.125/1.50 = 0.75:
    V  = m^2 + n^2 + 1 = 2.125
    V1 = m^2*n^2       = 0.31640625
    num = 2*m*n*sqrt(V) = 1.125 * 1.45773797 = 1.63995522
    term1 = num/(V+V1) * (V+1)/V = 0.67172047 * 1.47058824 = 0.98782422
    arctan(num/(V-V1)) = arctan(0.90675700) = 0.73653610 rad
    I = (0.98782422 + 0.73653610)/(4*pi) = 1.72436032/12.56637061 = 0.13722082

    delta_sigma = 4*qo*I = 4 * 197.530864 * 0.13722082 = 108.421386 kPa

Consolidacion primaria (Terzaghi 1943), Cc = 0.25, e0 = 0.80, H = 3.00 m:
    Sc = [Cc/(1+e0)]*H*log10(sigma'_f/sigma'_0)
       = (0.25/1.80)*3.00*log10(188.421386/80.0)
       = 0.41666667 * 0.37204020 = 0.15501675 m = 155.016753 mm
"""
from __future__ import annotations

import math

import pytest
from foundationcalc._common.model import Reaction

from foundationcalc.analysis.boussinesq import (
    BoussinesqRect,
    influence_corner,
    sigma_z_rect_center,
)
from foundationcalc.integration.foundation_chain import foundation_package

N_KN = 1000.0
H_LAYER_M = 3.00
SIGMA_V0_KPA = 80.0
CC, E0 = 0.25, 0.80

SOIL = {
    "allowable_bearing_kPa": 200.0,
    "founding_depth_m": 1.50,
    "compressible_layer": {
        "H_layer_m": H_LAYER_M,
        "sigma_v_0_kPa": SIGMA_V0_KPA,
        "Cc": CC,
        "e_0": E0,
        "cv_m2_per_year": 1.20,
    },
}


def _paquete():
    return foundation_package(
        etabs_or_reactions=[Reaction(node_id="COL1", case="ELU_1", fz_kN=N_KN)],
        soil_params=SOIL,
    )


def test_golden_incremento_de_tension_por_newmark_bajo_el_centro():
    """GOLDEN — delta_sigma = 108.421386 kPa (Fadum/Newmark, 4 cuadrantes).

    Se re-deriva aqui con los numeros del docstring, sin llamar a la cadena, y
    luego se comprueba que la cadena produce ese mismo valor.
    """
    B = L = 2.25
    z = H_LAYER_M / 2.0
    qo = N_KN / (B * L)
    assert qo == pytest.approx(197.530864, rel=1e-8)

    # El factor de influencia, contra la aritmetica del docstring.
    m = n = (B / 2.0) / z
    assert m == pytest.approx(0.75, rel=1e-12)
    V = m * m + n * n + 1.0
    V1 = m * m * n * n
    num = 2.0 * m * n * math.sqrt(V)
    I_mano = (num / (V + V1) * (V + 1.0) / V
              + math.atan(num / (V - V1))) / (4.0 * math.pi)
    assert I_mano == pytest.approx(0.13722082, rel=1e-7)
    assert influence_corner(B / 2.0, L / 2.0, z) == pytest.approx(I_mano, rel=1e-9)

    ds = sigma_z_rect_center(BoussinesqRect(qo_kPa=qo, B_m=B, L_m=L, z_m=z))
    assert ds == pytest.approx(108.421386, rel=1e-7)


def test_golden_asentamiento_por_consolidacion_en_el_entregable():
    """GOLDEN — Sc = 155.016753 mm en el paquete de cimentacion."""
    pkg = _paquete()
    assert "COL1" in pkg.settlement_results
    s_res = pkg.settlement_results["COL1"]

    ds = 108.421386
    esperado_mm = (CC / (1.0 + E0)) * H_LAYER_M * math.log10(
        (SIGMA_V0_KPA + ds) / SIGMA_V0_KPA
    ) * 1000.0
    assert esperado_mm == pytest.approx(155.016753, rel=1e-6)
    assert s_res.Sc_mm == pytest.approx(esperado_mm, abs=0.01)

    assert "Asentamiento por Consolidación 1D" in pkg.memoria_markdown
    assert f"{s_res.Sc_mm:.2f}" in pkg.memoria_markdown


def test_la_carga_puntual_habria_subestimado_un_40_por_ciento():
    """GUARDA ANTI-REGRESION.

    Fija la magnitud del error corregido: si alguien vuelve a cablear la
    solucion de carga puntual con z desde la superficie, el asentamiento cae de
    155.02 a 92.05 mm sin que nada mas se rompa. Este test es lo unico que lo
    notaria.
    """
    z_malo = 1.50 + H_LAYER_M / 2.0          # desde la superficie
    ds_malo = (3.0 * N_KN) / (2.0 * math.pi * z_malo ** 2)
    assert ds_malo == pytest.approx(53.051648, rel=1e-6)

    sc_malo = (CC / (1.0 + E0)) * H_LAYER_M * math.log10(
        (SIGMA_V0_KPA + ds_malo) / SIGMA_V0_KPA
    ) * 1000.0
    assert sc_malo == pytest.approx(92.0548, rel=1e-4)

    pkg = _paquete()
    real = pkg.settlement_results["COL1"].Sc_mm
    assert real > sc_malo
    assert sc_malo / real == pytest.approx(0.594, abs=0.01), (
        "el metodo antiguo subestimaba el asentamiento un ~40 %"
    )
