"""Goldens de punzonamiento EC2 §6.4 que MATAN los mutantes supervivientes.

Motivación
==========
`foundationdesignjm/design/punching_shear.py` sufrió un incidente en el que un
mutante del perímetro de control (`2.0 * c2` -> `3.0 * c2`) llegó a estar
commiteado sin que ningún test lo detectase (ver commit
"revert: restaurar punching_shear.py, que entro MUTADO"). El piloto de mutation
testing sigue reportando supervivientes en este fichero. Estos tests fijan, con
valores derivados a mano de la norma, las magnitudes que ningún test cubría.

Fuente normativa
================
EN 1992-1-1 (Eurocódigo 2) §6.4:

  §6.4.2(1) + Fig. 6.13 — perímetro de control básico u1 a 2d de la cara del
  soporte. Para un soporte rectangular c1 x c2 el contorno es el rectángulo
  desplazado 2d con las cuatro esquinas redondeadas por cuartos de círculo de
  radio 2d, de modo que:

      u1 = 2·c1 + 2·c2 + 2·π·(2d)                                        (1)

  y el área encerrada por ese contorno (rectángulo central + dos bandas
  rectangulares + los cuatro cuartos de círculo, que suman un círculo completo):

      A_u1 = c1·c2 + 2·(c1 + c2)·(2d) + π·(2d)²                          (2)

  Genéricamente, a una distancia `a` de la cara del soporte:

      u(a)   = 2·(c1 + c2) + 2·π·a                                       (3)
      A_u(a) = c1·c2 + 2·(c1 + c2)·a + π·a²                              (4)

  §6.4.3(3) — descuento de la reacción del terreno interior al perímetro:

      F_sd = N_sd · (1 - A_u / A_zapata)                                 (5)

  §6.4.3(3)/(6) — F_sd,ef = β · F_sd, con β = 1.15 para soporte interior
  (valor recomendado, Fig. 6.21N).

      τ_sd = F_sd,ef / (u · d)                                           (6)

  §6.4.4(1) — resistencia base sin armadura de punzonamiento:

      τ_Rd,c = (0.18/γ_c) · ξ · (100·ρ_l·f_ck)^(1/3)    [MPa]            (7)
      ξ      = min(1 + sqrt(200/d[mm]), 2.0)
      ρ_l    = min(sqrt(ρ_x·ρ_y), 0.02)

  §6.4.4(2) — zapatas compactas: cuando el perímetro a 2d se sale de la planta,
  se itera con perímetros interiores a < 2d y la resistencia se escala por 2d/a:

      τ_Rd(a) = τ_Rd,c · (2d / a)                                        (8)

  El rango admisible de `a` está acotado por el vuelo de la zapata: un perímetro
  de control situado fuera de la planta no tiene sentido físico.

Derivación a mano de u1 (geometría del CASO A)
==============================================
Soporte c1 = c2 = 0.400 m, canto útil d = 0.500 m  ->  2d = 1.000 m.

  Tramos rectos: los cuatro lados del soporte se trasladan 2d hacia fuera sin
  cambiar de longitud  ->  2·(0.400) + 2·(0.400) = 1.600 m
  Esquinas: cuatro cuartos de círculo de radio 2d = 1.000 m
            -> 4 · (2π·1.000/4) = 2π·1.000 = 6.283185307 m

      u1 = 1.600 + 6.283185307 = 7.883185307 m                     [ec. (1)]

  Área encerrada [ec. (2)]:
      A_u1 = 0.400·0.400 + 2·(0.800)·1.000 + π·1.000²
           = 0.160 + 1.600 + 3.141592654 = 4.901592654 m²

Mutante EQUIVALENTE (no se escribe test para él)
================================================
El mutante `(foundation.width - c2) / 2.0` -> `* 2.0` de la línea 138 vive en la
rama `else` del olfateo de unidades, alcanzable sólo si `foundation.width <= 10.0`
(mm). Es EQUIVALENTE, y la razón es estructural:

  · Entrar en esa rama exige W <= 10 mm, o sea W_m <= 0.010 m, luego el área en
    planta A_zapata = L_m · W_m es diminuta.
  · Pero esa misma rama interpreta el número bruto en milímetros como metros, así
    que dy = (W - c2)/2 vale del orden de metros. Para que dy sea la cota que
    manda hace falta dy < 2d, lo que obliga a un d comparativamente grande.
  · Con d grande, la primera distancia del barrido a_min = 0.1·d ya encierra
    A_u(a_min) >= π·(0.1d)² >> A_zapata, de modo que TODOS los candidatos caen en
    el `continue` y `best_tuple` queda a None: el resultado sale por el mismo
    fallback con y sin mutación.

Comprobación empírica (400 000 configuraciones aleatorias con W <= 10 mm,
barriendo L, c1, c2 y d en varias décadas logarítmicas):
    364 776 llegan a la rama compacta
     92 863 de ellas SÍ cambian el `max_a` al mutar
     48 161 de ellas SÍ producen un perímetro interior válido
          0 cumplen ambas cosas  ->  0 diferencias observables
"""

from __future__ import annotations

import math

import pytest

from foundationdesignjm.core.geometry import Column, RectangularFoundation
from foundationdesignjm.design.punching_shear import punching_shear_check

# (100 · ρ_l · f_ck)^(1/3) con ρ_l = 0.005 y f_ck = 25 MPa -> 12.5^(1/3)
CUBE_ROOT_12_5 = 12.5 ** (1.0 / 3.0)  # = 2.320794417


def test_golden_punching_standard_branch_u1_and_tau_sd_ec2():
    """CASO A — zapata estándar 3.00 x 3.00 m: u1 a 2d cabe dentro de la planta.

    Datos:
        Zapata  L = W = 3000 mm -> A_zapata = 9.000 m²
        Soporte c1 = c2 = 400 mm, centrado (pos 1500, 1500) -> β = 1.15 (interior)
        d = 0.500 m, N_sd = 800 kN, f_ck = 25 MPa, ρ_x = ρ_y = 0.005, γ_c = 1.5

    Derivación (EC2 §6.4, ecuaciones (1)-(8) del docstring del módulo):

      u1   = 2·0.4 + 2·0.4 + 2π·1.0            = 7.883185307 m
      A_u1 = 0.16 + 2·0.8·1.0 + π·1.0²         = 4.901592654 m²
      A_u1 (4.9016) < A_zapata (9.0)  ->  rama estándar, a_crit = 2d = 1.000 m

      F_sd    = 800 · (9.000 - 4.901592654)/9.000
              = 800 · 0.455378594                = 364.302875236 kN      [ec. (5)]
      F_sd,ef = 1.15 · 364.302875236                = 418.948306522 kN
      τ_sd    = 418.948306522 / (7.883185307·0.500)
              = 418.948306522 / 3.941592654         = 106.289092593 kPa     [ec. (6)]

      ξ       = 1 + sqrt(200/500) = 1 + 0.632455532 = 1.632455532
      τ_Rd,c  = (0.18/1.5)·1.632455532·12.5^(1/3)
              = 0.12·1.632455532·2.320794417 = 0.454631242 MPa
              = 454.631242131 kPa                                        [ec. (7)]

      η       = 106.289092593 / 454.631242131          = 0.233791880

    MATA al mutante `u1 * d > 0` -> `u1 * d < 0`: con la guarda invertida la
    condición nunca se cumple, τ_sd colapsa al literal 0.0 y η = 0, pero el
    veredicto sigue siendo "PASS". Sólo aseverar el NÚMERO lo detecta.
    """
    foundation = RectangularFoundation(length=3000.0, width=3000.0, thickness=600.0)
    column = Column(length=400.0, width=400.0, pos_x=1500.0, pos_y=1500.0)

    res = punching_shear_check(
        foundation=foundation,
        column=column,
        N_sd_kN=800.0,
        fck_MPa=25.0,
        rho_x=0.005,
        rho_y=0.005,
        d_eff_m=0.5,
        gamma_c=1.5,
    )

    assert res.is_compact is False
    assert res.applicable is True

    # Perímetro de control básico y distancia de control
    assert res.u1 == pytest.approx(7.883185307, rel=1e-8)
    assert res.u_crit_m == pytest.approx(7.883185307, rel=1e-8)
    assert res.a_crit_m == pytest.approx(1.000, rel=1e-8)

    # Cadena de acciones
    assert res.beta == pytest.approx(1.15, rel=1e-12)
    assert res.F_sd == pytest.approx(364.302875236, rel=1e-8)
    assert res.F_sd_ef == pytest.approx(418.948306522, rel=1e-8)

    # ---- La aserción que mata al mutante de la guarda `u1 * d > 0` ----
    assert res.tau_sd == pytest.approx(106.289092593, rel=1e-8)

    # Resistencia y utilización
    assert res.xi == pytest.approx(1.632455532, rel=1e-8)
    assert res.tau_rd == pytest.approx(454.631242131, rel=1e-8)
    assert res.utilization == pytest.approx(0.233791880, rel=1e-8)


def test_golden_punching_compact_control_perimeter_identities_ec2():
    """CASO B — zapata compacta 1.40 x 1.40 m: identidades cerradas de EC2 §6.4.4(2).

    Datos:
        Zapata  L = W = 1400 mm -> A_zapata = 1.960 m²
        Soporte c1 = c2 = 400 mm, centrado -> β = 1.15
        d = 0.450 m, N_sd = 600 kN, f_ck = 25 MPa, ρ = 0.005, γ_c = 1.5

    Comprobación de que la rama compacta se activa:
        A_u1 = 0.16 + 2·0.8·0.9 + π·0.9² = 0.16 + 1.44 + 2.544690 = 4.144690 m²
        A_u1 (4.1447) >= A_zapata (1.9600)  ->  EC2 §6.4.4(2)

    Una vez el código informa la distancia crítica a_crit, TODAS las magnitudes
    restantes quedan fijadas en forma cerrada por las ecuaciones (3)-(8) —
    no hay ningún grado de libertad. Este test las recalcula desde la norma con
    el a_crit informado y exige coincidencia exacta.

    La única magnitud absoluta que se asevera aquí es la resistencia base, que
    NO depende de a:
        ξ      = 1 + sqrt(200/450)                = 1.666666667
        τ_Rd,c = (0.18/1.5)·1.666666667·12.5^(1/3)
               = 0.12·1.666666667·2.320794417     = 0.464158883 MPa
               = 464.158883361 kPa                                     [ec. (7)]

    A modo de ilustración, con el a_crit que hoy devuelve el barrido
    (a = 0.220000 m) las ecuaciones dan:
        u(a)    = 2·0.8 + 2π·0.22                     = 2.982300768 m  [ec. (3)]
        A_u(a)  = 0.16 + 0.352 + 0.152053             = 0.664053084 m² [ec. (4)]
        F_sd    = 600·(1 - 0.664053084/1.960)         = 396.718443541 kN
        τ_sd    = 1.15·396.718443541/(2.982300768·0.45) = 339.950964505 kPa
        τ_Rd(a) = 464.158883361·(0.90/0.22)           = 1898.831795569 kPa
        η       = 339.950964505/1898.831795569        = 0.179031637
    Estos valores NO se aseveran como literales: el valor concreto de a_crit sale
    de un barrido discreto de 40 puntos, es decir, es detalle de implementación.
    Aseverarlo sería caracterización, no golden. Lo que sí es normativo — y lo
    que se asevera — son las identidades (3)-(8) evaluadas en el a_crit informado.

    MATA al mutante `u_a = 2.0 * (c1 + c2) + ...` -> `2.0 / (c1 + c2) + ...`
    (perímetro de control): la ec. (3) deja de cumplirse.
    MATA al mutante `A_u_a = ... + 2.0 * (c1 + c2) * a + ...` ->
    `... + 2.0 / (c1 + c2) * a + ...`: el perímetro sigue siendo correcto, pero
    el área encerrada y por tanto F_sd y τ_sd dejan de cumplir las ecs. (4)-(6).
    """
    c1 = c2 = 0.400  # m
    d = 0.450  # m
    A_footing = 1.400 * 1.400  # m²
    N_sd = 600.0  # kN
    beta = 1.15

    foundation = RectangularFoundation(length=1400.0, width=1400.0, thickness=500.0)
    column = Column(length=400.0, width=400.0, pos_x=700.0, pos_y=700.0)

    res = punching_shear_check(
        foundation=foundation,
        column=column,
        N_sd_kN=N_sd,
        fck_MPa=25.0,
        rho_x=0.005,
        rho_y=0.005,
        d_eff_m=d,
        gamma_c=1.5,
    )

    assert res.is_compact is True
    assert res.applicable is True
    assert 0.0 < res.a_crit_m < 2.0 * d

    a = res.a_crit_m

    # --- ec. (3): perímetro de control a distancia a (mata al mutante de u_a) ---
    u_expected = 2.0 * (c1 + c2) + 2.0 * math.pi * a
    assert res.u_crit_m == pytest.approx(u_expected, rel=1e-12)
    assert res.u1 == pytest.approx(u_expected, rel=1e-12)

    # --- ecs. (4)-(6): área encerrada -> F_sd -> τ_sd (mata al mutante de A_u_a) ---
    A_u_expected = c1 * c2 + 2.0 * (c1 + c2) * a + math.pi * a**2
    F_sd_expected = N_sd * (1.0 - A_u_expected / A_footing)
    assert res.F_sd == pytest.approx(F_sd_expected, rel=1e-12)
    assert res.F_sd_ef == pytest.approx(beta * F_sd_expected, rel=1e-12)
    assert res.tau_sd == pytest.approx(
        beta * F_sd_expected / (u_expected * d), rel=1e-12
    )

    # --- ecs. (7)-(8): resistencia base y escalada ---
    xi_expected = 1.0 + math.sqrt(200.0 / (d * 1000.0))
    tau_rd_expected = 0.12 * xi_expected * CUBE_ROOT_12_5 * 1000.0
    assert res.tau_rd == pytest.approx(tau_rd_expected, rel=1e-12)
    assert res.tau_rd_scaled_kPa == pytest.approx(
        tau_rd_expected * (2.0 * d) / a, rel=1e-12
    )
    assert res.utilization == pytest.approx(
        res.tau_sd / res.tau_rd_scaled_kPa, rel=1e-12
    )

    # Único absoluto normativo (independiente de a): τ_Rd,c [ec. (7)]
    assert res.xi == pytest.approx(1.666666667, rel=1e-8)
    assert res.tau_rd == pytest.approx(464.158883361, rel=1e-8)


def test_golden_punching_compact_utilization_is_a_true_maximum_over_admissible_a():
    """CASO C — la utilización devuelta es un MÁXIMO sobre las distancias admisibles.

    Datos:
        Zapata  L = W = 600 mm -> A_zapata = 0.360 m²
        Soporte c1 = c2 = 400 mm, centrado -> β = 1.15
        d = 0.400 m (2d = 0.800 m), N_sd = 800 kN, f_ck = 25 MPa, ρ = 0.005

    Rama compacta:
        A_u1 = 0.16 + 2·0.8·0.8 + π·0.8² = 0.16 + 1.28 + 2.010619 = 3.450619 m²
        A_u1 (3.4506) >= A_zapata (0.3600)  ->  EC2 §6.4.4(2)

    Rango admisible de `a` (EC2 §6.4.4(2)): a <= 2d = 0.800 m, y además el
    perímetro de control debe caber en la planta, es decir
        a <= vuelo = (0.600 - 0.400)/2 = 0.100 m.
    Luego a in [·, 0.100] m.

    ARGUMENTO: el resultado es el máximo de η sobre el rango admisible de `a`.
    El código lo busca con un muestreo de 40 puntos, así que la desigualdad
    exacta "η_devuelta >= η(a) para todo a admisible" sólo se cumple hasta la
    resolución del muestreo. Lo que sí se puede exigir sin ambigüedad es que el
    rango muestreado siga siendo el admisible: si el rango se acota en el vuelo
    (0.100 m), los 40 puntos caen todos dentro y encuadran el pico, y el máximo
    devuelto (η = 0.0492102) queda un 1.9 % POR ENCIMA de η(a0) para el a0 de
    abajo. Si el rango se escapa hasta 2d = 0.800 m con los mismos 40 puntos,
    el pico queda sub-resuelto y el máximo cae a η = 0.0475354, un 1.6 % POR
    DEBAJO de η(a0). El umbral η(a0) separa limpiamente ambos casos.

    Tomamos a0 = 0.042500 m, que es admisible (0 < 0.0425 <= 0.100), y
    calculamos η(a0) en forma cerrada con las ecs. (3)-(8):

        u(a0)    = 2·0.8 + 2π·0.0425            = 1.867035376 m
        A_u(a0)  = 0.16 + 1.6·0.0425 + π·0.0425²
                 = 0.16 + 0.068 + 0.0056745     = 0.233674502 m²
        F_sd     = 800·(1 - 0.233674502/0.360)    = 280.723329488 kN
        F_sd,ef  = 1.15·280.723329488              = 322.831828911 kN
        τ_sd     = 322.831828911/(1.867035376·0.400)  = 432.278671762 kPa
        ξ        = 1 + sqrt(200/400)            = 1.707106781
        τ_Rd,c   = 0.12·1.707106781·2.320794417 = 475.421266400 kPa
        τ_Rd(a0) = 475.421266400·(0.800/0.0425)    = 8949.106191066 kPa
        η(a0)    = 432.278671762/8949.106191066       = 0.048304117

    MATA a los mutantes `foundation.length > 10.0` -> `< 10.0` y
    `foundation.width > 10.0` -> `< 10.0`.
    Esas comparaciones deciden si las dimensiones de la zapata se leen en mm
    (dividiendo por 1000) o en m. Invertidas, el vuelo calculado es
    (600 - 0.4)/2 = 299.8 "m" en lugar de 0.100 m, el barrido deja de estar
    acotado por la planta y se extiende hasta 2d = 0.800 m con el mismo número
    de puntos: sub-resuelve el pico y devuelve un máximo MENOR (η = 0.047535),
    por debajo de η(a0). Subestimar la utilización a punzonamiento es
    inseguro — exactamente la clase de defecto del incidente `2.0*c2 -> 3.0*c2`.
    """
    c1 = c2 = 0.400  # m
    d = 0.400  # m
    A_footing = 0.600 * 0.600  # m²
    N_sd = 800.0  # kN
    beta = 1.15
    overhang = (0.600 - 0.400) / 2.0  # 0.100 m

    foundation = RectangularFoundation(length=600.0, width=600.0, thickness=500.0)
    column = Column(length=400.0, width=400.0, pos_x=300.0, pos_y=300.0)

    res = punching_shear_check(
        foundation=foundation,
        column=column,
        N_sd_kN=N_sd,
        fck_MPa=25.0,
        rho_x=0.005,
        rho_y=0.005,
        d_eff_m=d,
        gamma_c=1.5,
    )

    assert res.is_compact is True

    # η(a0) en forma cerrada para a0 admisible
    a0 = 0.042500  # m
    assert 0.0 < a0 <= overhang  # admisible por geometría
    assert a0 <= 2.0 * d  # admisible por EC2 §6.4.4(2)

    u_a0 = 2.0 * (c1 + c2) + 2.0 * math.pi * a0
    A_u_a0 = c1 * c2 + 2.0 * (c1 + c2) * a0 + math.pi * a0**2
    tau_sd_a0 = beta * N_sd * (1.0 - A_u_a0 / A_footing) / (u_a0 * d)
    xi = 1.0 + math.sqrt(200.0 / (d * 1000.0))
    tau_rd_c = 0.12 * xi * CUBE_ROOT_12_5 * 1000.0
    eta_a0 = tau_sd_a0 / (tau_rd_c * (2.0 * d) / a0)

    # Los números derivados a mano en el docstring
    assert u_a0 == pytest.approx(1.867035376, rel=1e-8)
    assert A_u_a0 == pytest.approx(0.233674502, rel=1e-7)
    assert tau_sd_a0 == pytest.approx(432.278671762, rel=1e-8)
    assert tau_rd_c == pytest.approx(475.421266400, rel=1e-8)
    assert eta_a0 == pytest.approx(0.048304117, rel=1e-8)

    # ---- La aserción que mata a los mutantes de la comparación de unidades ----
    assert res.utilization >= eta_a0, (
        f"La utilización devuelta ({res.utilization:.7f}) es menor que la de una "
        f"distancia admisible a0={a0} m (η={eta_a0:.7f}); el barrido no está "
        f"acotado por el vuelo de la zapata ({overhang} m)."
    )

    # El perímetro crítico evaluado debe caber en la planta
    assert res.a_crit_m <= overhang + 1e-12
