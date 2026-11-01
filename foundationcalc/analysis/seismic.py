"""Seismic analysis — Mononobe-Okabe and liquefaction screening (EC8 + EN 1998-5).

Theory: docs/theory/07_seismic.md.
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field


class LiquefactionCheck(BaseModel):
    """EC8-5 §4.1.4 liquefaction screening result."""

    required: bool
    reason: str
    N_1_60: Optional[float] = None
    tau_e_over_sigma_v0: Optional[float] = None


class MononobeOkabeResult(BaseModel):
    K: float = Field(..., description="M-O lateral pressure coefficient")
    theta_deg: float = Field(..., description="Seismic inertia angle (deg)")
    seismic_thrust: float = Field(..., description="Total thrust E_d (kN/m)")
    dynamic_increment: float = Field(..., description="ΔP_d, dynamic component (kN/m)")


def normalised_SPT(N_SPT: int, sigma_v0_eff_kPa: float) -> float:
    """N_1(60) = (100/σ'_v0)^(1/2) · N_SPT, with 0.5 < (·)^(1/2) < 2."""
    if sigma_v0_eff_kPa <= 0:
        raise ValueError("σ'_v0 must be positive.")
    Cn = math.sqrt(100.0 / sigma_v0_eff_kPa)
    Cn = max(0.5, min(2.0, Cn))
    return Cn * N_SPT


def cyclic_stress_ratio(alpha_S: float, sigma_v0_kPa: float, depth_m: float) -> Optional[float]:
    """τ_e = 0.65 · α · S · σ_v0, valid for z ≤ 20 m."""
    if depth_m > 20.0:
        return None
    return 0.65 * alpha_S * sigma_v0_kPa


def liquefaction_screening(
    depth_m: float,
    alpha_S: float,
    clay_fraction: float = 0.0,
    plasticity_index: float = 0.0,
    silt_fraction: float = 0.0,
    N_1_60: Optional[float] = None,
) -> LiquefactionCheck:
    """EC8-5 screening — return whether a full liquefaction analysis is required.

    Args:
        depth_m: depth from surface of the saturated cohesionless layer.
        alpha_S: α · S design ground acceleration ratio.
        clay_fraction: percentage clay (0–100).
        plasticity_index: PI (%).
        silt_fraction: percentage silt (0–100).
        N_1_60: normalised SPT (if available).
    """
    if depth_m > 15.0:
        return LiquefactionCheck(required=False, reason="Saturated sand layer below 15 m.")

    if alpha_S < 0.15:
        if clay_fraction > 20 and plasticity_index > 10:
            return LiquefactionCheck(required=False, reason="Clay > 20% with PI > 10 (α·S < 0.15).")
        # EN 1998-5 §4.1.4: arenas con más de un 35 % de limo y N1(60) > 20.
        # DEFECTO CORREGIDO (1.1.0): el código exigía N1(60) > 30 (el umbral
        # de las arenas limpias) y pedía el análisis completo de más.
        if silt_fraction > 35 and N_1_60 is not None and N_1_60 > 20:
            return LiquefactionCheck(
                required=False, reason="Silt > 35% with N_1(60) > 20 (α·S < 0.15).",
                N_1_60=N_1_60,
            )
        if N_1_60 is not None and N_1_60 > 30:
            return LiquefactionCheck(
                required=False, reason="Clean sand with N_1(60) > 30 (α·S < 0.15).",
                N_1_60=N_1_60,
            )

    return LiquefactionCheck(
        required=True,
        reason="Full liquefaction analysis required (criteria not satisfied).",
        N_1_60=N_1_60,
    )


# ---------------------------------------------------------------------------
# Mononobe-Okabe pseudo-static earth pressure
# ---------------------------------------------------------------------------

def mononobe_okabe_K(
    phi_deg: float,
    delta_deg: float,
    psi_deg: float = 90.0,
    beta_deg: float = 0.0,
    kh: float = 0.0,
    kv: float = 0.0,
    gamma_phi: float = 1.0,
) -> tuple[float, float]:
    """Mononobe-Okabe K coefficient for active seismic earth pressure.

    Args:
        phi_deg:   characteristic friction angle φ' (deg).
        delta_deg: wall-soil friction angle δ (deg).
        psi_deg:   angle between wall front face and horizontal (90° = vertical).
        beta_deg:  backfill slope from horizontal.
        kh, kv:    seismic acceleration ratios (horizontal, vertical).
        gamma_phi: partial factor on tan φ'.

    Returns:
        (K, θ_deg) where θ is the seismic inertia angle.
    """
    phi_d = math.atan(math.tan(math.radians(phi_deg)) / gamma_phi)
    delta_d = math.atan(math.tan(math.radians(delta_deg)) / gamma_phi)
    psi = math.radians(psi_deg)
    beta = math.radians(beta_deg)
    theta = math.atan(kh / max(1e-12, (1.0 - kv if kv >= 0 else 1.0 + kv)))

    common_num = math.sin(psi + phi_d - theta) ** 2
    common_den = math.cos(theta) * math.sin(psi) ** 2 * math.sin(psi - theta - delta_d)

    if beta <= phi_d - theta:
        sub_num = math.sin(phi_d + delta_d) * math.sin(phi_d - beta - theta)
        sub_den = math.sin(psi - theta - delta_d) * math.sin(psi + beta)
        sub = max(sub_num / max(sub_den, 1e-12), 0.0)
        denom = common_den * (1.0 + math.sqrt(sub)) ** 2
    else:
        denom = common_den

    K = common_num / max(denom, 1e-12)
    return K, math.degrees(theta)


def seismic_thrust(
    H: float,
    gamma_star: float,
    K_mo: float,
    kv: float = 0.0,
    E_ws: float = 0.0,
    E_wd: float = 0.0,
) -> MononobeOkabeResult:
    """Design seismic earth thrust (M-O, EN 1998-5 Annex E):

        E_d = (1/2) · γ* · (1 ± k_v) · K · H² + E_ws + E_wd

    `dynamic_increment` is E_d minus ½·γ*·K·H² and minus the static water
    thrust E_ws, i.e. the vertical-acceleration part plus the hydrodynamic
    E_wd. It is NOT the increment over the static active thrust (this
    function does not know K_a). `theta_deg` is not known here and is 0.

    DEFECTO CORREGIDO (1.1.0): `dynamic_increment` era E_d − estático
    + E_ws + E_wd: contaba el agua dos veces y la hidrostática como dinámica
    (con k_v = 0, E_ws = 10 y E_wd = 5 daba 30 en vez de 5 kN/m).
    """
    factor = (1.0 + kv) if kv >= 0 else (1.0 - kv)
    static = 0.5 * gamma_star * K_mo * H ** 2
    E_d = factor * static + E_ws + E_wd
    return MononobeOkabeResult(
        K=K_mo,
        theta_deg=0.0,
        seismic_thrust=E_d,
        dynamic_increment=E_d - static - E_ws,
    )


def rigid_wall_dynamic_increment(
    H: float, gamma: float, alpha_S: float
) -> float:
    """For walls that cannot generate the active state (EC8-5 §7.3.2.2):

        ΔP_d = α · S · γ · H²

    Applied at mid-height of the wall.
    """
    return alpha_S * gamma * H ** 2


def reinforced_earth_external(
    a_max_g: float,
    gamma_b: float,
    gamma_r: float,
    H: float,
    L: float,
    g: float = 9.81,
) -> dict:
    """External stability of a reinforced earth wall under seismic action.

    Returns dict with a_c, ΔP_AE, P_IR.
    """
    a_c = (1.45 - a_max_g) * a_max_g * g  # m/s²
    delta_P_AE = 0.375 * a_c * gamma_b * H ** 2 / g
    P_IR = a_c * gamma_r * H * L / g
    return {"a_c_ms2": a_c, "delta_P_AE": delta_P_AE, "P_IR": P_IR}
