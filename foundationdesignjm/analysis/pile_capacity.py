"""Pile axial capacity (calculation method per EN 1997-1 §7.6.2.3).

R_ck = R_bk + R_sk
R_bk = A_b · q_bk          (base resistance)
R_sk = Σ A_s,i · q_sk,i    (shaft resistance, sum over layers)

Theory: docs/theory/05_pile_foundations.md.
"""

from __future__ import annotations

import math
from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.piles import Pile
from ..core.soil import SoilLayer, SoilProfile


class PileCapacityResult(BaseModel):
    R_bk: float = Field(..., description="Characteristic base resistance (kN)")
    R_sk: float = Field(..., description="Characteristic shaft resistance (kN)")
    R_ck: float = Field(..., description="Characteristic total compression (kN)")
    R_cd: float = Field(..., description="Design total compression (kN)")
    R_sd_tension: float = Field(0.0, description="Design tension resistance (kN)")
    note: str = ""


def base_resistance_drained(area_m2: float, sigma_v_eff_kPa: float, Nq: float) -> float:
    """q_bk · A_b for cohesionless soils:  q_bk = N_q · σ'_v at tip level."""
    return area_m2 * Nq * sigma_v_eff_kPa


def base_resistance_undrained(area_m2: float, cu_kPa: float, Nc: float = 9.0) -> float:
    """q_bk · A_b for undrained clay:  q_bk = N_c · c_u (with N_c ≈ 9 for piles)."""
    return area_m2 * Nc * cu_kPa


def shaft_resistance_alpha(perimeter_m: float, length_m: float, alpha: float, cu_kPa: float) -> float:
    """α-method (cohesive soils):  q_sk = α · c_u."""
    return perimeter_m * length_m * alpha * cu_kPa


def shaft_resistance_beta(
    perimeter_m: float,
    length_m: float,
    sigma_v_eff_avg_kPa: float,
    beta: float,
) -> float:
    """β-method (cohesionless):  q_sk = β · σ'_v (mean)."""
    return perimeter_m * length_m * beta * sigma_v_eff_avg_kPa


def pile_axial_capacity(
    pile: Pile,
    soil_profile: SoilProfile,
    base_soil: SoilLayer,
    Nq: float = 0.0,
    alpha_shaft: Optional[float] = None,
    beta_shaft: Optional[float] = None,
    xi3: float = 1.40,
    xi4: float = 1.40,
    gamma_b: float = 1.0,
    gamma_s: float = 1.0,
    gamma_t: float = 1.0,
    tip_depth_m: Optional[float] = None,
) -> PileCapacityResult:
    """Calculation method (EC7 §7.6.2.3) — single profile from ground tests.

    Args:
        pile: pile model.
        soil_profile: layered profile.
        base_soil: layer at the pile tip.
        Nq: bearing factor at base (drained) or 0 for undrained.
        alpha_shaft: α factor (cohesive) — uses c_u from each layer.
        beta_shaft: β factor (cohesionless) — uses σ'_v from each layer.
        xi3, xi4: ξ correlation factors (EC7 Table A.10) — default 1.40 for n=1.
        gamma_b, gamma_s, gamma_t: pile resistance partial factors.
        tip_depth_m: tip depth from surface (defaults to pile.length_m).
    """
    if tip_depth_m is None:
        tip_depth_m = pile.length_m

    sigma_v_eff_tip = soil_profile.effective_stress_at(tip_depth_m)
    if base_soil.soil_type.value == "cohesive" and base_soil.undrained_shear_strength is not None:
        R_b = base_resistance_undrained(pile.area, base_soil.undrained_shear_strength)
    else:
        if Nq <= 0:
            phi_rad = math.radians(base_soil.friction_angle)
            if phi_rad > 0:
                sin_phi = math.sin(phi_rad)
                Nq = ((1.0 + sin_phi) / (1.0 - sin_phi)) * math.exp(math.pi * math.tan(phi_rad))
            else:
                import warnings
                warnings.warn(
                    "phi_rad <= 0 for granular base soil; using conservative "
                    "fallback Nq=30.0 instead of Nc=9.0. Verify friction angle.",
                    stacklevel=2,
                )
                Nq = 30.0
        R_b = base_resistance_drained(pile.area, sigma_v_eff_tip, Nq)

    # Shaft resistance — accumulate per layer from surface down to tip
    R_s = 0.0
    z_top = 0.0
    for layer in soil_profile.layers:
        z_bottom = min(z_top + layer.thickness, tip_depth_m)
        if z_bottom <= z_top:
            break
        L_in_layer = z_bottom - z_top
        if layer.undrained_shear_strength is not None and alpha_shaft is not None:
            R_s += shaft_resistance_alpha(
                pile.shaft_perimeter, L_in_layer, alpha_shaft, layer.undrained_shear_strength
            )
        else:
            sigma_avg = soil_profile.effective_stress_at((z_top + z_bottom) / 2.0)
            beta = beta_shaft if beta_shaft is not None else 0.3
            R_s += shaft_resistance_beta(pile.shaft_perimeter, L_in_layer, sigma_avg, beta)
        z_top = z_bottom
        if z_top >= tip_depth_m:
            break

    # EC7 §7.6.2.3(8): apply ξ on the TOTAL calculated resistance, not on each
    # component independently. We pass the calculated R_b and R_s through the
    # combination ξ = min(ξ_3, ξ_4) applied to R_calc = R_b + R_s, then split
    # back into base/shaft proportionally for partial-factor application.
    xi = min(xi3, xi4)
    R_calc_total = R_b + R_s
    R_ck = R_calc_total / xi
    R_bk = R_ck * (R_b / R_calc_total) if R_calc_total > 0 else 0.0
    R_sk = R_ck - R_bk
    # EC7 design resistance: either separate γ_b / γ_s on R_bk / R_sk
    # (preferred), OR γ_t on the total. Only use γ_t when explicitly > 1.0
    # AND γ_b, γ_s are both at default 1.0:
    use_gamma_t = (gamma_t != 1.0 and gamma_b == 1.0 and gamma_s == 1.0)
    if use_gamma_t:
        R_cd = R_ck / gamma_t
        note = f"ξ={xi}, γ_t={gamma_t} on total"
    else:
        R_cd = R_bk / gamma_b + R_sk / gamma_s
        note = f"ξ={xi}, γ_b={gamma_b}, γ_s={gamma_s} (separate)"

    return PileCapacityResult(
        R_bk=R_bk,
        R_sk=R_sk,
        R_ck=R_ck,
        R_cd=R_cd,
        note=note,
    )
