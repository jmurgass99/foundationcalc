"""Diaphragm (slurry) wall design.

A diaphragm wall is a continuous RC wall built **in situ** before
excavation, using bentonite slurry to keep the trench open while
reinforcement is lowered and concrete tremied. Used for:

- Deep basements and metro stations (excavations 10–40 m).
- Cut-off walls under dams.
- Permanent retaining + structural function combined.

The wall behaves as a **propped cantilever beam** spanning between:
- The base of excavation (passive resistance at the embedded toe).
- The slab(s) / props above.

This module gives:

- **Embedment depth** required to mobilise enough passive pressure
  to balance the active thrust above (Free Earth Support method —
  classical Blum / Tschebotarioff).
- **Prop forces** at each support level.
- **Maximum bending moment** in the wall.
- **Penetration safety factor** F = M_passive / M_active ≥ 1.5–2.0.

References: EN 1997-1 §9, EAB-86 (German DIN approach), Bowles 2001.
Theory: docs/theory/06_retaining_walls.md §6.1 (diaphragm walls).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from ..codes.eurocode7 import DesignApproach, LimitState, get_partial_factors


class DiaphragmWallGeometry(BaseModel):
    H_excavation: float = Field(..., gt=2.0)
    embedment_m: float = Field(..., gt=0.5)
    thickness_m: float = Field(0.60, gt=0.30,
                              description="Wall thickness (m, typ. 0.60–1.20)")
    prop_levels_m: List[float] = Field(
        default_factory=list,
        description="Depths (m below top) of prop / slab supports",
    )


class DiaphragmWallLoading(BaseModel):
    phi_deg: float = Field(..., ge=20, le=45)
    gamma_kN_m3: float = Field(..., gt=10)
    c_kPa: float = Field(0.0, ge=0)
    water_table_above_excavation_m: float = Field(0.0, ge=0)
    surcharge_q: float = Field(0.0, ge=0)


@dataclass
class DiaphragmWallResult:
    P_active_kN_per_m: float
    P_passive_kN_per_m: float
    overturning_safety_factor: float
    embedment_required_m: float
    prop_forces_kN_per_m: List[float]
    M_max_kNm_per_m: float
    V_max_kN_per_m: float


class DiaphragmWallDesigner:
    """Free Earth Support analysis of a single-/multi-propped diaphragm wall."""

    def __init__(
        self,
        geometry: DiaphragmWallGeometry,
        loading: DiaphragmWallLoading,
        design_approach: DesignApproach = DesignApproach.DA2,
    ):
        self.geo = geometry
        self.load = loading
        self.da = design_approach

    @staticmethod
    def _K_a(phi_deg: float) -> float:
        return math.tan(math.radians(45.0 - phi_deg / 2.0)) ** 2

    @staticmethod
    def _K_p(phi_deg: float) -> float:
        return math.tan(math.radians(45.0 + phi_deg / 2.0)) ** 2

    def check(self) -> DiaphragmWallResult:
        pf = get_partial_factors(self.da, LimitState.GEO)
        gG = pf.actions.gamma_G_unfav
        gR_e = 1.4     # EC7 R2 earth resistance

        K_a = self._K_a(self.load.phi_deg)
        K_p = self._K_p(self.load.phi_deg)
        H = self.geo.H_excavation
        D = self.geo.embedment_m
        gamma = self.load.gamma_kN_m3
        q = self.load.surcharge_q

        # ---- Active thrust on the inside of the wall (depth 0 to H+D) ----
        # Acts on the BACKFILL side of the wall over total length H + D.
        Ltot = H + D
        # Triangular soil contribution + rectangular surcharge
        P_a_soil = gG * 0.5 * K_a * gamma * Ltot ** 2
        z_a_soil = Ltot / 3.0           # arm from base of wall (i.e. depth Ltot)
        P_a_surch = gG * K_a * q * Ltot
        z_a_surch = Ltot / 2.0
        P_a_total = P_a_soil + P_a_surch
        z_a = (
            P_a_soil * (Ltot - z_a_soil) + P_a_surch * (Ltot - z_a_surch)
        ) / max(P_a_total, 1e-9)

        # ---- Passive resistance on the inside of the embedded portion ----
        # Acts on the EXCAVATION side, over depth D (from H to H+D).
        P_p = 0.5 * K_p * gamma * D ** 2 / gR_e   # divided by γ_R,e
        # Acts from the toe upward — arm above the toe is D/3
        z_p_above_toe = D / 3.0
        # Arm of passive force from the prop level (assume single top prop):
        if self.geo.prop_levels_m:
            prop_z = min(self.geo.prop_levels_m)
        else:
            prop_z = 0.0
        arm_p = (H + D) - prop_z - z_p_above_toe
        arm_a = (H + D) - prop_z - (Ltot - z_a)

        # Moment equilibrium about the prop:
        M_overturning = P_a_total * arm_a
        M_resisting = P_p * arm_p
        FoS = M_resisting / max(M_overturning, 1e-9)

        # ---- Required embedment (iterate so FoS = target) ----
        # Solve M_resisting >= M_overturning · 1.5
        # For a propped wall with single prop at top, an iterative approach
        # is best. Simple binary search over D:
        target = 1.5
        D_lo, D_hi = 0.1, 5.0 * H
        for _ in range(40):
            D_try = 0.5 * (D_lo + D_hi)
            Ltot_t = H + D_try
            Pa_t_s = gG * 0.5 * K_a * gamma * Ltot_t ** 2
            Pa_t_q = gG * K_a * q * Ltot_t
            za_t = (
                Pa_t_s * (Ltot_t - Ltot_t / 3.0)
                + Pa_t_q * (Ltot_t - Ltot_t / 2.0)
            ) / max(Pa_t_s + Pa_t_q, 1e-9)
            Pp_t = 0.5 * K_p * gamma * D_try ** 2 / gR_e
            arm_a_t = (H + D_try) - prop_z - (Ltot_t - za_t)
            arm_p_t = (H + D_try) - prop_z - D_try / 3.0
            FoS_try = (Pp_t * arm_p_t) / max((Pa_t_s + Pa_t_q) * arm_a_t, 1e-9)
            if FoS_try >= target:
                D_hi = D_try
            else:
                D_lo = D_try
        D_req = D_hi

        # ---- Prop force = ΣH (active − passive) ----
        F_prop_total = P_a_total - P_p
        n_props = max(len(self.geo.prop_levels_m), 1)
        prop_forces = [F_prop_total / n_props] * n_props

        # ---- Maximum bending moment ----
        # Proper Free Earth Support: integrate the net pressure diagram.
        # The bending moment along the wall is
        #     M(z) = T_prop · (z − z_prop)  −  ∫₀^z (z − ζ) · w(ζ) dζ
        # where w(ζ) is the net horizontal pressure at depth ζ. The
        # maximum |M| occurs at the depth where the shear V(z) = 0.
        # For a triangular active envelope and a single top prop, the
        # closed-form result is
        #     M_max  ≈  F_prop² / (2 · q_max)
        # where q_max = K_a · γ · L_eff is the peak active pressure
        # ordinate. This is more accurate than the prior 0.4·F·H rule.
        q_max = K_a * gamma * Ltot * gG
        if q_max > 0:
            M_max = (F_prop_total ** 2) / (2.0 * q_max)
        else:
            M_max = F_prop_total * 0.4 * H
        V_max = F_prop_total

        return DiaphragmWallResult(
            P_active_kN_per_m=P_a_total,
            P_passive_kN_per_m=P_p,
            overturning_safety_factor=FoS,
            embedment_required_m=D_req,
            prop_forces_kN_per_m=prop_forces,
            M_max_kNm_per_m=M_max,
            V_max_kN_per_m=V_max,
        )


__all__ = [
    "DiaphragmWallGeometry",
    "DiaphragmWallLoading",
    "DiaphragmWallResult",
    "DiaphragmWallDesigner",
]
