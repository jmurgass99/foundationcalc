"""
Capacidad de pilotes multi-código.

Componentes:
    Q_ult = Q_s (lateral fuste) + Q_p (punta)

Factores parciales:
    EU/SG (EN 1997-1 §7.6.3 R2/R3):
        γ_s = 1.10, γ_p = 1.10  (R2 hincado)
        γ_s = 1.40, γ_p = 1.40  (R3 excavados)
    US/CO (AASHTO LRFD §10.7 / NSR-10 §H.4):
        φ_s = 0.55, φ_p = 0.50  (típico estático)
    AU (AS 2159):
        Φ_g = 0.40–0.70 según riesgo geotécnico
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class PileCapacityInput:
    Q_shaft_ult_kN: float          # capacidad fuste última (sin factor)
    Q_tip_ult_kN: float            # capacidad punta última
    pile_type: Literal["driven", "bored"] = "driven"
    geotechnical_risk: Literal["low", "medium", "high"] = "medium"


@dataclass(frozen=True)
class PileCapacityResult:
    Q_design_kN: float
    factor_shaft: float
    factor_tip: float
    code: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "Q_design_kN": self.Q_design_kN,
            "factor_shaft": self.factor_shaft,
            "factor_tip": self.factor_tip,
            "code": self.code,
        }


def design_pile_capacity(inp: PileCapacityInput, code: str = "EU"
                           ) -> PileCapacityResult:
    code = code.upper()
    if code in ("EU", "SG"):
        # EN 1997-1 R2 hincado, R3 excavado
        if inp.pile_type == "driven":
            g_s, g_p = 1.10, 1.10
        else:
            g_s, g_p = 1.40, 1.40
        Q = inp.Q_shaft_ult_kN / g_s + inp.Q_tip_ult_kN / g_p
        factor_s, factor_p = 1 / g_s, 1 / g_p
    elif code in ("US", "CO"):
        # AASHTO LRFD §10.7.3.8 (estatic analysis)
        phi_s = 0.55 if inp.pile_type == "driven" else 0.45
        phi_p = 0.50 if inp.pile_type == "driven" else 0.40
        Q = phi_s * inp.Q_shaft_ult_kN + phi_p * inp.Q_tip_ult_kN
        factor_s, factor_p = phi_s, phi_p
    elif code == "AU":
        # AS 2159 Tabla 4.3.2 — geotechnical strength reduction
        phi_g_table = {"low": 0.70, "medium": 0.55, "high": 0.40}
        phi = phi_g_table[inp.geotechnical_risk]
        Q = phi * (inp.Q_shaft_ult_kN + inp.Q_tip_ult_kN)
        factor_s = factor_p = phi
    else:
        raise ValueError(f"código '{code}' no soportado")

    return PileCapacityResult(
        Q_design_kN=Q, factor_shaft=factor_s, factor_tip=factor_p, code=code,
    )


__all__ = ["PileCapacityInput", "PileCapacityResult", "design_pile_capacity"]
