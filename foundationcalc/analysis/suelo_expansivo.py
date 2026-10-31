"""Suelos expansivos - presion de hinchamiento y levantamiento.

Modelo simplificado tipo Nelson & Miller (1992) con multi-codigo.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log10


@dataclass(frozen=True)
class ExpansiveInput:
    PI: float                      # indice plastico
    w_natural_pct: float           # humedad natural
    w_final_pct: float             # humedad final saturada
    e0: float = 0.8
    H_activa_m: float = 2.0
    Cs: float = 0.05               # indice de hinchamiento
    sigma_v0_kPa: float = 30.0
    code: str = "US"               # US (Nelson&Miller), CO (NSR-10)


@dataclass(frozen=True)
class ExpansiveResult:
    swell_potential_pct: float
    swelling_pressure_kPa: float
    heave_mm: float
    risk: str
    code: str


def swell_potential(PI: float, w: float) -> float:
    # Seed (1962) correlacion: SP = K*PI^a (en %)
    K = 0.00216
    return K * (PI ** 2.44)


def swelling_pressure(PI: float, e0: float) -> float:
    # Komornik & David (1969)
    log_ps = -2.132 + 0.0208 * PI + 0.000665 * (1.0) - 0.0269 * e0
    return 10 ** log_ps  # kPa-ish (orden de magnitud)


def expansive_assessment(inp: ExpansiveInput) -> ExpansiveResult:
    if inp.code not in {"EU", "AU", "SG", "US", "CO"}:
        raise ValueError(f"code invalido: {inp.code}")
    sp = swell_potential(inp.PI, inp.w_natural_pct)
    ps = swelling_pressure(inp.PI, inp.e0)
    # Levantamiento por estratos saturados
    sigma_f = max(inp.sigma_v0_kPa, 1.0)
    heave_m = inp.Cs / (1 + inp.e0) * inp.H_activa_m * log10(ps / sigma_f) if ps > sigma_f else 0.0
    if inp.PI < 15:
        risk = "BAJO"
    elif inp.PI < 25:
        risk = "MEDIO"
    elif inp.PI < 35:
        risk = "ALTO"
    else:
        risk = "MUY ALTO"
    return ExpansiveResult(sp, ps, max(heave_m, 0) * 1000, risk, inp.code)


__all__ = ["ExpansiveInput", "ExpansiveResult",
           "expansive_assessment", "swell_potential", "swelling_pressure"]
