"""
EN 1992-1-1 §7.3 — Cálculo de ancho de fisura wk en elementos RC.

Fórmula §7.3.4 Eq. (7.8):
    wk = sr,max · (ε_sm - ε_cm)

Con sr,max = k3·c + k1·k2·k4·φ/ρ_p,eff   (Eq. 7.11)
    k1 = 0.8 (alta adherencia), k2 = 0.5 flexión / 1.0 tracción
    k3 = 3.4, k4 = 0.425
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CrackWidthInput:
    bar_diameter_mm: float
    cover_mm: float
    fct_eff_MPa: float = 2.6       # fctm para C25/30
    sigma_s_MPa: float = 220.0     # tensión en armadura bajo carga cuasi-permanente
    Es_MPa: float = 200_000.0
    Ecm_MPa: float = 31_000.0      # C25/30
    rho_p_eff: float = 0.02        # As / Ac,eff
    k1: float = 0.8                # alta adherencia
    k2: float = 0.5                # flexión
    k3: float = 3.4
    k4: float = 0.425
    kt: float = 0.4                # carga larga duración


@dataclass(frozen=True)
class CrackWidthResult:
    sr_max_mm: float
    eps_sm_minus_eps_cm: float
    wk_mm: float
    is_within_limit: bool          # wk ≤ wmax típico 0.3 mm

    def to_dict(self) -> dict[str, Any]:
        return {
            "sr_max_mm": self.sr_max_mm,
            "eps_sm_minus_eps_cm": self.eps_sm_minus_eps_cm,
            "wk_mm": self.wk_mm,
            "is_within_limit": self.is_within_limit,
        }


def crack_width_EC2(inp: CrackWidthInput, w_max_mm: float = 0.3
                      ) -> CrackWidthResult:
    """EN 1992-1-1 §7.3.4."""
    # Eq. 7.11
    sr_max = inp.k3 * inp.cover_mm + (
        inp.k1 * inp.k2 * inp.k4 * inp.bar_diameter_mm / max(inp.rho_p_eff, 1e-9)
    )
    # Eq. 7.9 — (ε_sm - ε_cm)
    alpha_e = inp.Es_MPa / inp.Ecm_MPa
    eps_diff_num = inp.sigma_s_MPa - inp.kt * (inp.fct_eff_MPa / inp.rho_p_eff) * (
        1 + alpha_e * inp.rho_p_eff
    )
    eps_diff_num = max(eps_diff_num, 0.6 * inp.sigma_s_MPa)
    eps_diff = eps_diff_num / inp.Es_MPa

    wk = sr_max * eps_diff
    return CrackWidthResult(
        sr_max_mm=sr_max, eps_sm_minus_eps_cm=eps_diff,
        wk_mm=wk, is_within_limit=wk <= w_max_mm,
    )


__all__ = ["CrackWidthInput", "CrackWidthResult", "crack_width_EC2"]
