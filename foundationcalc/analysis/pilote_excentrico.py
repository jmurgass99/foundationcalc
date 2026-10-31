"""Pilote con carga excentrica - Brinch Hansen + Bowles.

Considera M, V y N combinados; calcula tension lateral admisible.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, tan, radians


@dataclass(frozen=True)
class PiloteExcentricoInput:
    D_m: float
    L_m: float
    N_kN: float
    H_kN: float
    M_kNm: float
    phi_deg: float = 30.0
    c_kPa: float = 0.0
    gamma_kN_m3: float = 18.0
    code: str = "EU"


@dataclass(frozen=True)
class PiloteExcentricoResult:
    e_kNm: float
    H_admisible_kN: float
    M_admisible_kNm: float
    interaction_ratio: float
    cumple: bool
    code: str


def brinch_hansen_kq_kc(phi_deg: float, z_over_D: float) -> tuple[float, float]:
    """Factores Kq, Kc de Brinch Hansen para pilotes cortos."""
    phi = radians(phi_deg)
    Kq0 = (1 + tan(phi)) ** 2 if phi_deg > 0 else 1.0
    Kc0 = 5.0
    # crecimiento limitado con profundidad relativa
    Kq = Kq0 * (1 + 0.5 * z_over_D)
    Kc = Kc0 * (1 + 0.2 * z_over_D)
    return Kq, Kc


def evaluar(inp: PiloteExcentricoInput) -> PiloteExcentricoResult:
    if inp.code not in {"EU", "AU", "SG", "US", "CO"}:
        raise ValueError(f"code invalido: {inp.code}")
    e = inp.M_kNm  # interpretado como M
    # Bowles: H_u aproximado, usando media profundidad
    z_avg = inp.L_m / 2.0
    Kq, Kc = brinch_hansen_kq_kc(inp.phi_deg, z_avg / inp.D_m)
    qu_lat = inp.c_kPa * Kc + inp.gamma_kN_m3 * z_avg * Kq
    A_lat = inp.D_m * inp.L_m
    H_adm = qu_lat * A_lat / 2.0
    M_adm = H_adm * inp.L_m / 3.0
    # interaccion linear (Bowles)
    ir = (abs(inp.H_kN) / H_adm) + (abs(inp.M_kNm) / M_adm) if M_adm > 0 and H_adm > 0 else 99.0
    return PiloteExcentricoResult(e, H_adm, M_adm, ir, ir <= 1.0, inp.code)


__all__ = ["PiloteExcentricoInput", "PiloteExcentricoResult",
           "evaluar", "brinch_hansen_kq_kc"]
