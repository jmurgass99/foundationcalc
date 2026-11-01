"""
Consolidación 1D — teoría de Terzaghi (1943).

Fachada sobre ``foundationcalc.analysis.consolidacion_1d`` (única fuente de verdad
para el factor de tiempo ``Tv_from_U``, ``U_from_Tv`` y el asentamiento primario).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from foundationcalc.analysis.consolidacion_1d import (
    ConsolidationInput as _AnalysisConsolidationInput,
    Tv_from_U,
    consolidate as _consolidate_canonical,
)


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
    """Delega en ``foundationcalc.analysis.consolidacion_1d.Tv_from_U``."""
    return Tv_from_U(U)


def evaluate_consolidation(inp: ConsolidationInput) -> ConsolidationResult:
    """Evalúa asentamiento primario y tiempos t50/t90 delegando en ``analysis.consolidacion_1d``."""
    H_dr = inp.H_layer_m / 2.0 if inp.drainage == "double" else inp.H_layer_m
    if inp.delta_sigma_kPa <= 0.0:
        Sc_mm = 0.0
        Tv_50 = _Tv_from_U(0.5)
        Tv_90 = _Tv_from_U(0.9)
    else:
        res = _consolidate_canonical(
            _AnalysisConsolidationInput(
                H_layer_m=inp.H_layer_m,
                sigma_v0_kPa=max(inp.sigma_v_0_kPa, 1e-9),
                delta_sigma_kPa=inp.delta_sigma_kPa,
                Cc=inp.Cc,
                Cr=0.0,
                e0=inp.e_0,
                cv_m2_per_year=inp.cv_m2_per_year,
                drainage=inp.drainage,
                OCR=1.0,
            )
        )
        Sc_mm = res.Sc_mm
        Tv_50 = res.Tv_50
        Tv_90 = res.Tv_90

    t_50_yr = Tv_50 * H_dr ** 2 / inp.cv_m2_per_year
    t_90_yr = Tv_90 * H_dr ** 2 / inp.cv_m2_per_year

    return ConsolidationResult(
        Sc_mm=Sc_mm,
        t_50pct_days=t_50_yr * 365.25,
        t_90pct_days=t_90_yr * 365.25,
        H_drainage_m=H_dr,
    )


__all__ = ["ConsolidationInput", "ConsolidationResult", "evaluate_consolidation"]
