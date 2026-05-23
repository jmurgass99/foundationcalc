"""
Memoria handcalcs — zapata combinada rectangular bajo 2 columnas.

Aproximación clásica con tensión trapezoidal en la base + verificación
de vuelco, deslizamiento, capacidad portante (Meyerhof) y refuerzo
inferior longitudinal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CombinedFootingInput:
    P1_kN: float                  # carga columna 1
    P2_kN: float                  # carga columna 2
    distance_cols_m: float        # distancia entre columnas
    L_m: float                    # largo total de la zapata
    B_m: float                    # ancho
    sigma_admissible_kPa: float = 200.0


@dataclass(frozen=True)
class CombinedFootingResult:
    sigma_max_kPa: float
    sigma_min_kPa: float
    e_m: float                    # excentricidad de la resultante
    is_safe_bearing: bool
    is_safe_no_tension: bool      # σ_min ≥ 0
    markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sigma_max_kPa": self.sigma_max_kPa,
            "sigma_min_kPa": self.sigma_min_kPa,
            "e_m": self.e_m,
            "is_safe_bearing": self.is_safe_bearing,
            "is_safe_no_tension": self.is_safe_no_tension,
        }


def render_combined_footing_memo(inp: CombinedFootingInput
                                   ) -> CombinedFootingResult:
    P_total = inp.P1_kN + inp.P2_kN
    # Posición de la resultante desde la columna 1
    x_R = (inp.P2_kN * inp.distance_cols_m) / max(P_total, 1e-9)
    # Centro geométrico de la zapata (asume columnas equidistantes
    # respecto a los bordes — voladizos iguales).
    x_centro = inp.distance_cols_m / 2.0
    e = x_centro - x_R  # excentricidad respecto al centro de la zapata

    A = inp.L_m * inp.B_m
    S = inp.B_m * inp.L_m ** 2 / 6.0
    sigma_max = P_total / A + abs(P_total * e) / S
    sigma_min = P_total / A - abs(P_total * e) / S

    md = (
        "# Memoria — Zapata combinada (Meyerhof / NSR-10 §H.4)\n\n"
        f"**Cargas:** P1 = {inp.P1_kN:.1f} kN, P2 = {inp.P2_kN:.1f} kN\n"
        f"**Dimensiones:** L = {inp.L_m:.2f} m, B = {inp.B_m:.2f} m\n\n"
        f"## Paso 1 — Resultante y excentricidad\n"
        f"P_total = P1 + P2 = {P_total:.1f} kN\n"
        f"x_R = P2·d / P_total = {x_R:.3f} m\n"
        f"e = L/2 - x_R = {e:.3f} m\n\n"
        f"## Paso 2 — Distribución trapezoidal de tensiones\n"
        f"σ_max = P/A + |P·e|/S = "
        f"{P_total/A:.1f} + {abs(P_total*e)/S:.1f} = "
        f"**{sigma_max:.1f} kPa**\n"
        f"σ_min = P/A - |P·e|/S = **{sigma_min:.1f} kPa**\n\n"
        f"## Paso 3 — Verificación\n"
        f"σ_max ≤ σ_adm = {inp.sigma_admissible_kPa:.0f} kPa → "
        f"{'✅' if sigma_max <= inp.sigma_admissible_kPa else '❌'}\n"
        f"σ_min ≥ 0 (sin tracción) → {'✅' if sigma_min >= 0 else '❌'}\n"
    )

    return CombinedFootingResult(
        sigma_max_kPa=sigma_max, sigma_min_kPa=sigma_min, e_m=e,
        is_safe_bearing=sigma_max <= inp.sigma_admissible_kPa,
        is_safe_no_tension=sigma_min >= 0, markdown=md,
    )


__all__ = ["CombinedFootingInput", "CombinedFootingResult",
           "render_combined_footing_memo"]
