"""Design of counterfort (buttressed) retaining walls.

A counterfort wall has a thin stem propped by **vertical RC buttresses**
behind the wall, connected to a base slab. Used for heights > 8 m where
a plain cantilever wall becomes too thick.

The stem spans **horizontally** between counterforts as a one-way slab
under the soil pressure, while the counterforts act as tapered
cantilevers reacting against the base.

This module gives:

- The cantilever-wall global ULS checks (bearing, sliding, overturning)
  — re-using `CantileverWallDesigner` because the global picture is the
  same (T-shape with self-weight, active thrust, etc.).
- The **horizontal stem moment** at midspan + at supports (counterforts)
  treating the stem as a one-way slab continuous over `n_counterforts`.
- The **counterfort tie force** at the heel-stem connection (where the
  buttress acts as a tension tie to transfer the stem reaction back to
  the heel that pulls down).

Theory: docs/theory/06_retaining_walls.md §6.1 + Bowles 2001 §14.6.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

from ..analysis.earth_pressure import active_thrust
from ..codes.eurocode7 import DesignApproach, LimitState, get_partial_factors
from ..core.material import Concrete
from ..core.soil import SoilLayer
from .retaining_wall import (
    CantileverWallDesigner, CantileverWallGeometry,
    RetainingWallCheck, RetainingWallLoading,
)


class CounterfortWallGeometry(BaseModel):
    """Counterfort wall geometry. Inherits the cantilever T-shape plus the
    counterfort spacing and dimensions."""

    H: float = Field(..., gt=4.0, description="Stem height (m)")
    stem_thickness: float = Field(..., gt=0.15, description="Stem thickness (m, uniform)")
    toe: float = Field(..., ge=0)
    heel: float = Field(..., ge=0)
    base_thickness: float = Field(..., gt=0)
    embedment_front: float = Field(0.8, ge=0)

    counterfort_spacing_m: float = Field(
        ..., gt=2.0, description="Centre-to-centre spacing of counterforts (m)",
    )
    counterfort_thickness_m: float = Field(
        ..., gt=0.20, description="Counterfort thickness (m)",
    )
    counterfort_top_width_m: float = Field(
        0.30, gt=0.10, description="Counterfort top width (m, tapered)",
    )

    @property
    def B(self) -> float:
        return self.toe + self.stem_thickness + self.heel


@dataclass
class CounterfortWallResult:
    """Bundle of global ULS + stem horizontal bending + counterfort tie."""

    global_check: RetainingWallCheck
    stem_M_midspan_kNm_per_m: float
    stem_M_support_kNm_per_m: float
    stem_V_at_support_kN_per_m: float
    counterfort_tie_T_kN: float
    counterfort_M_base_kNm: float
    counterfort_V_base_kN: float


class CounterfortWallDesigner:
    """Global stability + stem horizontal bending + counterfort tie design."""

    def __init__(
        self,
        geometry: CounterfortWallGeometry,
        loading: RetainingWallLoading,
        concrete: Concrete,
        design_approach: DesignApproach = DesignApproach.DA2,
    ):
        self.geo = geometry
        self.load = loading
        self.concrete = concrete
        self.da = design_approach

    def check(self) -> CounterfortWallResult:
        # ----- Global stability via the equivalent cantilever ------------
        eq_geo = CantileverWallGeometry(
            H=self.geo.H,
            stem_top=self.geo.stem_thickness,
            stem_bottom=self.geo.stem_thickness,
            toe=self.geo.toe,
            heel=self.geo.heel,
            base_thickness=self.geo.base_thickness,
            embedment_front=self.geo.embedment_front,
        )
        eq_des = CantileverWallDesigner(eq_geo, self.load, self.concrete,
                                       design_approach=self.da)
        eq_res = eq_des.check()

        # ----- Horizontal stem moments (one-way slab over counterforts) --
        # Pressure at the bottom of the stem (worst case, governs slab):
        pf = get_partial_factors(self.da, LimitState.STR)
        gG = pf.actions.gamma_G_unfav
        gQ = pf.actions.gamma_Q_unfav

        phi = self.load.backfill.friction_angle
        gamma = self.load.backfill.unit_weight
        delta = phi * self.load.delta_over_phi if self.load.use_coulomb else 0.0
        H = self.geo.H
        # Use Coulomb / Rankine K_a from active_thrust at full H:
        thrust = active_thrust(
            H=H, gamma=gamma, phi_deg=phi,
            c_prime=self.load.backfill.cohesion,
            surcharge_q=self.load.surcharge_q,
            use_coulomb=self.load.use_coulomb,
            delta_deg=delta, beta_deg=90.0, alpha_deg=0.0,
        )
        Ka = thrust.coefficient_K
        p_base_kPa = gG * Ka * gamma * H + gQ * Ka * self.load.surcharge_q
        L_span = self.geo.counterfort_spacing_m
        # Continuous-beam (4 spans or more): M_support = w·L²/12,  M_midspan = w·L²/24
        # Per metre vertical run of the stem at the bottom:
        M_support = p_base_kPa * L_span ** 2 / 12.0   # kN·m/m
        M_midspan = p_base_kPa * L_span ** 2 / 24.0   # kN·m/m
        V_support = p_base_kPa * L_span / 2.0          # kN/m

        # ----- Counterfort acting as a tapered cantilever ----------------
        # Tributary load on one counterfort = soil thrust over its tributary width.
        # The counterfort acts as a triangular cantilever held by the base.
        P_h_d = gG * thrust.thrust_P * L_span        # kN total horizontal per counterfort
        z_arm = thrust.point_of_application_z        # m
        # Tie at the top of the counterfort (connects to heel slab) to balance
        # the vertical component (Coulomb δ): roughly T_tie ≈ P_h_d · tan δ
        delta_rad = math.radians(delta) if self.load.use_coulomb else 0.0
        T_tie = P_h_d * math.tan(delta_rad)

        # Counterfort base moment and shear:
        M_cf_base = P_h_d * z_arm                    # kN·m
        V_cf_base = P_h_d                            # kN

        return CounterfortWallResult(
            global_check=eq_res,
            stem_M_midspan_kNm_per_m=M_midspan,
            stem_M_support_kNm_per_m=M_support,
            stem_V_at_support_kN_per_m=V_support,
            counterfort_tie_T_kN=T_tie,
            counterfort_M_base_kNm=M_cf_base,
            counterfort_V_base_kN=V_cf_base,
        )


__all__ = [
    "CounterfortWallGeometry",
    "CounterfortWallResult",
    "CounterfortWallDesigner",
]
