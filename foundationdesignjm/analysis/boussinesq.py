"""Distribucion de tension vertical sigma_z bajo zapata (Boussinesq, 1885).

Soluciones cerradas:
    - Carga puntual: sigma_z = 3P/(2*pi*z^2) * cos^5(theta)
    - Carga rectangular (Newmark/Fadum): factor de influencia I bajo esquina.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan, pi, sqrt


@dataclass(frozen=True)
class BoussinesqPoint:
    P_kN: float
    z_m: float
    r_m: float = 0.0


@dataclass(frozen=True)
class BoussinesqRect:
    qo_kPa: float
    B_m: float
    L_m: float
    z_m: float
    code: str = "EU"


def sigma_z_point(p: BoussinesqPoint) -> float:
    R = sqrt(p.r_m ** 2 + p.z_m ** 2)
    if R == 0:
        return float("inf")
    return 3 * p.P_kN / (2 * pi * R ** 2) * (p.z_m / R) ** 3


def influence_corner(B: float, L: float, z: float) -> float:
    """Factor de influencia I bajo la esquina de un rectangulo cargado uniformemente
    (Fadum 1948 / Newmark). sigma_z = qo * I.

    Con m = B/z, n = L/z, V = m^2 + n^2 + 1, V1 = m^2*n^2:

        I = 1/(4*pi) * [ 2*m*n*sqrt(V)/(V + V1) * (V + 1)/V
                         + arctan( 2*m*n*sqrt(V)/(V - V1) ) ]

    El arctan debe ser positivo: si (V - V1) < 0 se suma pi.

    NOTA (correccion): la version anterior de esta funcion usaba (V + V1) como
    denominador del segundo factor del primer termino y como argumento del
    arctan (en vez de V y (V - V1) respectivamente). Daba I(1,1) = 0.1257
    frente al valor publicado 0.1752 (-28%). Coincide ahora con
    `analysis.stress.newmark_influence_factor`, que ya era correcta.
    """
    m = B / z
    n = L / z
    V = m * m + n * n + 1
    V1 = m * m * n * n
    num = 2 * m * n * sqrt(V)
    term1 = num / (V + V1) * (V + 1) / V
    den2 = V - V1
    if den2 == 0:
        ang = pi / 2.0          # limite: arctan(+inf)
    elif den2 > 0:
        ang = atan(num / den2)
    else:
        ang = atan(num / den2) + pi
    return (1.0 / (4 * pi)) * (term1 + ang)


def sigma_z_rect_center(r: BoussinesqRect) -> float:
    """sigma_z en el centro de una zapata rectangular (4 cuadrantes)."""
    Ic = influence_corner(r.B_m / 2.0, r.L_m / 2.0, r.z_m)
    return 4.0 * r.qo_kPa * Ic


def stress_profile(qo: float, B: float, L: float,
                    z_max: float, n: int = 20,
                    code: str = "EU") -> list[tuple[float, float]]:
    if code not in {"EU", "AU", "SG", "US", "CO"}:
        raise ValueError(f"code invalido: {code}")
    zs = [(i + 1) * z_max / n for i in range(n)]
    return [(z, sigma_z_rect_center(BoussinesqRect(qo, B, L, z, code))) for z in zs]


__all__ = ["BoussinesqPoint", "BoussinesqRect",
           "sigma_z_point", "sigma_z_rect_center",
           "influence_corner", "stress_profile"]
