"""
Memoria — Zapata corrida (continua) bajo muro / fila de columnas.

Carga línea w (kN/m) → ancho B requerido por capacidad portante.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StripFootingInput:
    w_kN_per_m: float
    H_footing_m: float = 0.50
    sigma_admissible_kPa: float = 200.0
    gamma_concrete_kN_m3: float = 24.0


@dataclass(frozen=True)
class StripFootingResult:
    B_required_m: float
    weight_self_kN_per_m: float
    sigma_actual_kPa: float
    is_safe: bool
    markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "B_required_m": self.B_required_m,
            "weight_self_kN_per_m": self.weight_self_kN_per_m,
            "sigma_actual_kPa": self.sigma_actual_kPa,
            "is_safe": self.is_safe,
        }


def render_strip_footing_memo(inp: StripFootingInput) -> StripFootingResult:
    # B_req = w / σ_adm (sin peso propio, iterar)
    B = inp.w_kN_per_m / inp.sigma_admissible_kPa
    # Peso propio por metro lineal
    W_sf = B * inp.H_footing_m * inp.gamma_concrete_kN_m3
    sigma_actual = (inp.w_kN_per_m + W_sf) / B

    md = (
        "# Memoria — Zapata corrida\n\n"
        f"**Carga línea:** w = {inp.w_kN_per_m:.1f} kN/m\n"
        f"**Tensión admisible:** σ_adm = {inp.sigma_admissible_kPa:.0f} kPa\n\n"
        f"## Paso 1 — Ancho mínimo\n"
        f"B = w / σ_adm = {B*1000:.0f} mm = **{B:.2f} m**\n\n"
        f"## Paso 2 — Peso propio\n"
        f"W_sf = B·H·γ_c = {B:.2f}·{inp.H_footing_m:.2f}·{inp.gamma_concrete_kN_m3} "
        f"= {W_sf:.1f} kN/m\n\n"
        f"## Paso 3 — Verificación\n"
        f"σ_actual = (w + W_sf) / B = {sigma_actual:.1f} kPa\n"
        f"{'✅ PASS' if sigma_actual <= inp.sigma_admissible_kPa else '❌ FAIL'}\n"
    )

    return StripFootingResult(
        B_required_m=B, weight_self_kN_per_m=W_sf,
        sigma_actual_kPa=sigma_actual,
        is_safe=sigma_actual <= inp.sigma_admissible_kPa,
        markdown=md,
    )


__all__ = ["StripFootingInput", "StripFootingResult",
           "render_strip_footing_memo"]
