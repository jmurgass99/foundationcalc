"""
Consolidación 1D — teoría de Terzaghi (1943).

Calcula:
    1. Asentamiento primario S_c = (Cc/(1+e0))·H·log10(σ'f/σ'0)
    2. Tiempo para consolidación parcial t = Tv·H_dr²/cv
    3. Grado de consolidación U(Tv) ≈ √(4Tv/π) si U<0.6, else 1-exp(-π²Tv/4)
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, log10, pi, sqrt
from typing import Any


@dataclass(frozen=True)
class ConsolidationInput:
    H_layer_m: float
    sigma_v_0_kPa: float       # tensión inicial efectiva
    delta_sigma_kPa: float     # incremento de tensión
    Cc: float                  # índice de compresión
    e_0: float = 0.8           # relación de vacíos inicial
    cv_m2_per_year: float = 1.0
    drainage: str = "double"   # 'single' o 'double'


@dataclass(frozen=True)
class ConsolidationResult:
    Sc_mm: float
    t_50pct_days: float
    t_90pct_days: float
    H_drainage_m: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "Sc_mm": self.Sc_mm,
            "t_50pct_days": self.t_50pct_days,
            "t_90pct_days": self.t_90pct_days,
            "H_drainage_m": self.H_drainage_m,
        }


def _Tv_from_U(U: float) -> float:
    """Inversa de la curva U-Tv de Terzaghi.

        U <  0.6 :  Tv = (pi/4)·U²
        U >= 0.6 :  Tv = -(4/pi²)·ln[(1-U)·pi²/8]

    DEFECTO CORREGIDO: a la rama alta le faltaba el factor pi²/8 DENTRO del
    logaritmo (calculaba -(4/pi²)·ln(1-U)). Daba Tv90 = 0.9334 frente al
    correcto 0.8481, un +10.1 % en todos los tiempos de consolidación.

    Delega en `analysis.consolidacion_1d.Tv_from_U`, que ya era correcta, para
    que exista UNA sola fuente de verdad. Los dos módulos coexisten con campos
    distintos, y fue precisamente esa duplicación la que dejó divergir la
    fórmula sin que nada lo notara; `test_consolidacion_una_sola_verdad` lo
    vigila a partir de ahora.
    """
    from foundationdesignjm.analysis.consolidacion_1d import Tv_from_U

    return Tv_from_U(U)


def evaluate_consolidation(inp: ConsolidationInput) -> ConsolidationResult:
    sigma_f = inp.sigma_v_0_kPa + inp.delta_sigma_kPa
    if sigma_f <= inp.sigma_v_0_kPa:
        Sc_m = 0.0
    else:
        Sc_m = (inp.Cc / (1 + inp.e_0)) * inp.H_layer_m * log10(
            sigma_f / max(inp.sigma_v_0_kPa, 1e-9)
        )
    Sc_mm = Sc_m * 1000.0

    H_dr = inp.H_layer_m / 2.0 if inp.drainage == "double" else inp.H_layer_m
    Tv_50 = _Tv_from_U(0.5)
    Tv_90 = _Tv_from_U(0.9)
    t_50_yr = Tv_50 * H_dr ** 2 / inp.cv_m2_per_year
    t_90_yr = Tv_90 * H_dr ** 2 / inp.cv_m2_per_year

    return ConsolidationResult(
        Sc_mm=Sc_mm,
        t_50pct_days=t_50_yr * 365.25,
        t_90pct_days=t_90_yr * 365.25,
        H_drainage_m=H_dr,
    )


__all__ = ["ConsolidationInput", "ConsolidationResult", "evaluate_consolidation"]
