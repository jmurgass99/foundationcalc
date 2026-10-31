"""Sliding and overturning checks for shallow foundations and retaining walls.

Theory: docs/theory/03_shallow_foundations.md, 04_eurocode7_examples.md.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from ..core.soil import SoilLayer


class SlidingCheck(BaseModel):
    """Sliding resistance check at the foundation base."""

    H_Ed: float = Field(..., description="Design horizontal action (kN)")
    H_Rd: float = Field(..., description="Design sliding resistance (kN)")
    delta_d_deg: float
    N_Ed: float
    A_eff: float
    cohesion_term: float = 0.0
    passive_term: float = 0.0
    gamma_Rh: float = 1.0

    @property
    def utilization(self) -> float:
        return self.H_Ed / self.H_Rd if self.H_Rd > 0 else float("inf")

    @property
    def is_ok(self) -> bool:
        return self.utilization <= 1.0


class OverturningCheck(BaseModel):
    """Toppling (overturning) check about a base edge."""

    M_Ed_dst: float = Field(..., description="Destabilising moment (kN·m)")
    M_Ed_stb: float = Field(..., description="Stabilising moment (kN·m)")
    e_B: float = Field(..., description="Resulting eccentricity (m)")
    B: float = Field(..., description="Footing width (m)")

    @property
    def utilization(self) -> float:
        return self.M_Ed_dst / self.M_Ed_stb if self.M_Ed_stb > 0 else float("inf")

    @property
    def is_ok(self) -> bool:
        return self.utilization <= 1.0

    @property
    def middle_third(self) -> bool:
        return abs(self.e_B) <= self.B / 6.0


def sliding_resistance_drained(
    N_Ed: float,
    soil: SoilLayer,
    A_eff: float,
    H_Ed: float,
    delta_factor: float = 1.0,
    passive_force: float = 0.0,
    gamma_phi: float = 1.0,
    gamma_c: float = 1.0,
    gamma_Rh: float = 1.0,
) -> SlidingCheck:
    """Drained sliding check (effective stress).

    H_Rd = (N_Ed · tan δ_d + c'_d · A_eff) / γ_Rh + P_p,d

    δ_d ≈ δ_factor · φ_d (δ_factor = 2/3 for precast, 1 for cast-in-place).
    """
    phi_d_rad = math.atan(math.tan(math.radians(soil.friction_angle)) / gamma_phi)
    delta_d_rad = math.atan(delta_factor * math.tan(phi_d_rad))
    c_d = soil.cohesion / gamma_c

    friction_term = N_Ed * math.tan(delta_d_rad)
    cohesion_term = c_d * A_eff
    H_Rd = (friction_term + cohesion_term) / gamma_Rh + passive_force

    return SlidingCheck(
        H_Ed=H_Ed,
        H_Rd=H_Rd,
        delta_d_deg=math.degrees(delta_d_rad),
        N_Ed=N_Ed,
        A_eff=A_eff,
        cohesion_term=cohesion_term,
        passive_term=passive_force,
        gamma_Rh=gamma_Rh,
    )


def sliding_resistance_undrained(
    N_Ed: float,
    soil: SoilLayer,
    A_eff: float,
    H_Ed: float,
    passive_force: float = 0.0,
    gamma_cu: float = 1.0,
    gamma_Rh: float = 1.0,
) -> SlidingCheck:
    """Undrained sliding check.

    H_Rd = c_u,d · A_eff / γ_Rh + P_p,d
    """
    if soil.undrained_shear_strength is None:
        raise ValueError("Soil layer must define c_u for undrained sliding.")
    cu_d = soil.undrained_shear_strength / gamma_cu
    H_Rd = cu_d * A_eff / gamma_Rh + passive_force

    return SlidingCheck(
        H_Ed=H_Ed,
        H_Rd=H_Rd,
        delta_d_deg=0.0,
        N_Ed=N_Ed,
        A_eff=A_eff,
        cohesion_term=cu_d * A_eff,
        passive_term=passive_force,
        gamma_Rh=gamma_Rh,
    )


def overturning_check(
    M_dst_d: float,
    M_stb_d: float,
    V_d: float,
    B: float,
) -> OverturningCheck:
    """Compute toppling utilization and eccentricity.

    e_B = B/2 − (M_stb − M_dst) / V
    """
    if V_d <= 0:
        raise ValueError("V_d must be > 0 to compute the eccentricity.")
    e_B = B / 2.0 - (M_stb_d - M_dst_d) / V_d
    return OverturningCheck(
        M_Ed_dst=M_dst_d,
        M_Ed_stb=M_stb_d,
        e_B=e_B,
        B=B,
    )
