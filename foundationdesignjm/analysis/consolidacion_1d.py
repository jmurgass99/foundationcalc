"""Consolidacion 1D de Terzaghi - solucion completa con T_v.

Code-aware via parametro `code` (EU/AU/SG/US/CO). Solo cambia los FS y
factores de seguridad recomendados, la fisica es identica.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, log10, pi


_CODE_FS = {
    "EU": 1.5, "AU": 1.5, "SG": 1.5, "US": 1.5, "CO": 1.5,
}


@dataclass(frozen=True)
class ConsolidationInput:
    H_layer_m: float
    sigma_v0_kPa: float
    delta_sigma_kPa: float
    Cc: float
    Cr: float = 0.03
    e0: float = 0.8
    cv_m2_per_year: float = 1.0
    drainage: str = "double"     # 'single' o 'double'
    OCR: float = 1.0
    code: str = "EU"


@dataclass(frozen=True)
class ConsolidationResult:
    Sc_mm: float
    t_50_days: float
    t_90_days: float
    Tv_50: float
    Tv_90: float
    code: str


def U_from_Tv(Tv: float) -> float:
    if Tv <= 0:
        return 0.0
    if Tv < 0.2:
        return (4.0 * Tv / pi) ** 0.5
    return 1.0 - (8.0 / pi ** 2) * exp(-pi ** 2 * Tv / 4.0)


def Tv_from_U(U: float) -> float:
    if U <= 0:
        return 0.0
    if U < 0.6:
        return pi / 4.0 * U ** 2
    return -(4.0 / pi ** 2) * (-pi ** 2 * 0.25) * 1.0 + (
        (-4.0 / pi ** 2) * (log((1.0 - U) * pi ** 2 / 8.0))
    ) if False else (-4.0 / pi ** 2) * _safe_log((1.0 - U) * pi ** 2 / 8.0)


def _safe_log(x: float) -> float:
    from math import log
    return log(max(x, 1e-12))


def consolidate(inp: ConsolidationInput) -> ConsolidationResult:
    if inp.code not in _CODE_FS:
        raise ValueError(f"code invalido: {inp.code}")
    sigma_f = inp.sigma_v0_kPa + inp.delta_sigma_kPa
    sigma_p = inp.sigma_v0_kPa * inp.OCR
    if sigma_f <= sigma_p:
        Sc_m = inp.Cr / (1 + inp.e0) * inp.H_layer_m * log10(sigma_f / inp.sigma_v0_kPa)
    else:
        Sc_m = (
            inp.Cr / (1 + inp.e0) * inp.H_layer_m * log10(sigma_p / inp.sigma_v0_kPa)
            + inp.Cc / (1 + inp.e0) * inp.H_layer_m * log10(sigma_f / sigma_p)
        )
    H_dr = inp.H_layer_m / 2.0 if inp.drainage == "double" else inp.H_layer_m
    Tv50 = Tv_from_U(0.5)
    Tv90 = Tv_from_U(0.9)
    t50 = Tv50 * H_dr ** 2 / inp.cv_m2_per_year * 365.0
    t90 = Tv90 * H_dr ** 2 / inp.cv_m2_per_year * 365.0
    return ConsolidationResult(Sc_m * 1000, t50, t90, Tv50, Tv90, inp.code)


__all__ = ["ConsolidationInput", "ConsolidationResult",
           "consolidate", "U_from_Tv", "Tv_from_U"]
