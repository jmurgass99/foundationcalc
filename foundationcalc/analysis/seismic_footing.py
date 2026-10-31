"""Seismic verification of spread footings per EN 1998-5.

The seismic check of a shallow foundation combines:

1. The static gravity loads (G + ψ_2·Q) factored to the EC0 seismic
   combination (`AccidentalEarthquake`).
2. The structural inertia forces transmitted by the column (N, M, V).
3. The soil inertia ("ground inertia") through the horizontal seismic
   acceleration ratio `a_g · S / g` acting on the soil mass that
   contributes to the foundation resistance — this implicitly reduces
   the available friction angle (EN 1998-5 §5.4.1.1).

The classical engineering approach is to verify:
- Bearing capacity with seismic factors on N_q, N_c, N_γ (Pecker, 1995).
- Sliding with a horizontal load including the inertia of the foundation
  block itself plus the column shear.
- Overturning treating the whole system as a rigid body.

EN 1998-5 §5.4.1.1 (3) allows the soil parameters to be the same as the
static ones with `γ_φ = 1.25` and `γ_cu = 1.40` (default in DA-3) plus
applying seismic inclination/eccentricity reduction factors on the
bearing capacity.

The check below uses the simplified envelope from EN 1998-5 Annex F:

    (1 - eH) / (β · N̄)^a + e²M / (γ · N̄)^c · ... ≤ 1

For practical design we keep the conservative approach: use the standard
`drained_bearing_capacity` with seismic eccentricity / inclination
factors computed from the seismic action ratio `k_h`, and verify all
three classical mechanisms (bearing, sliding, overturning).

Theory: docs/theory/07_seismic.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

from ..codes.eurocode7 import DesignApproach, LimitState, get_partial_factors
from ..core.geometry import Column, RectangularFoundation
from ..core.material import Concrete
from ..core.soil import SoilLayer
from .base_pressure import BasePressureAnalysis, PressureRegime
from .bearing_capacity import (
    BearingCapacityFormula,
    BearingCapacityResult,
    drained_bearing_capacity,
    undrained_bearing_capacity,
)


class SeismicAction(BaseModel):
    """Pseudo-static seismic input for the foundation check."""

    a_g: float = Field(..., gt=0, description="Reference peak ground acceleration ratio (a_g/g)")
    S: float = Field(1.0, gt=0, description="Soil amplification factor (EN 1998-1 Table 3.2)")
    importance_factor_gamma_I: float = Field(1.0, gt=0, description="Importance factor γ_I")
    behaviour_factor_q: float = Field(1.0, gt=0, description="Behaviour factor q (capacity design)")
    r_factor: float = Field(1.0, ge=1.0, le=2.0, description="EN 1998-5 §5.4.1 reduction (1.0…2.0)")

    @property
    def a_gR(self) -> float:
        """Design ground acceleration ratio  a_g · γ_I · S."""
        return self.a_g * self.importance_factor_gamma_I * self.S

    @property
    def k_h(self) -> float:
        """Horizontal seismic action ratio  k_h = α·S / r   (EN 1998-5 §5.4.1.1)."""
        return self.a_gR / self.r_factor

    @property
    def k_v_up(self) -> float:
        """Upward vertical seismic ratio  k_v = ±0.5·k_h   (or 0.33 if a_v/a_g < 0.6)."""
        return 0.5 * self.k_h


@dataclass
class SeismicFootingCheck:
    """Full seismic-design output bundle for a single footing."""

    design_approach: str
    N_d: float
    H_d: float
    M_d: float

    # Eccentricity / pressures
    e_x: float
    e_y: float
    q_max: float
    q_avg: float
    regime: str

    # Bearing
    bearing_q_Ed: float
    bearing_q_Rd: float
    bearing_utilization: float

    # Sliding
    sliding_H_Ed: float
    sliding_H_Rd: float
    sliding_utilization: float

    # Overturning
    overturning_M_dst: float
    overturning_M_stb: float
    overturning_utilization: float
    middle_third: bool

    # M-O thrust on adjacent fill (if relevant)
    seismic_thrust_kN: Optional[float] = None

    @property
    def all_ok(self) -> bool:
        return (
            self.bearing_utilization <= 1.0
            and self.sliding_utilization <= 1.0
            and self.overturning_utilization <= 1.0
        )


def _seismic_inclination_factor(k_h: float, phi_rad: float) -> float:
    """Pecker / EN 1998-5 Annex F inclination factor on N_γ (simplified).

    Returns a multiplier ≤ 1 that scales the static `q_ult` for seismic.
    A pragmatic value used in practice is:

        i_seismic = (1 - k_h / tan φ) ^ 3   for k_h < tan φ

    For k_h ≥ tan φ the bearing capacity vanishes (limit state reached
    on the slope), so we clamp to 0.05.
    """
    if k_h <= 0:
        return 1.0
    tan_phi = math.tan(phi_rad)
    if tan_phi <= 0:
        return 1.0
    ratio = k_h / tan_phi
    if ratio >= 1.0:
        return 0.05
    return (1.0 - ratio) ** 3


def seismic_footing_check(
    foundation: RectangularFoundation,
    column: Column,
    N_kN: float,
    H_kN: float,
    M_kNm: float,
    soil: SoilLayer,
    concrete: Concrete,
    seismic: SeismicAction,
    design_approach: DesignApproach = DesignApproach.DA3,
    drained: bool = True,
    soil_overburden_depth_mm: float = 0.0,
    soil_unit_weight_overburden: float = 18.0,
    bearing_formula: BearingCapacityFormula = BearingCapacityFormula.CHEN_EC7,
    delta_factor: float = 1.0,
) -> SeismicFootingCheck:
    """Run the complete EN 1998-5 seismic check for a centred spread footing.

    Args:
        N_kN: total seismic axial load at the column base (kN, +down).
              Typical from EC0 seismic combination: G_k + ψ_2·Q_k + E.
        H_kN: total horizontal seismic shear at column base (kN).
        M_kNm: total seismic moment at column base (kN·m).
        seismic: seismic action object.
        design_approach: EC7 DA (DA-3 is the EC7 recommendation when
                         seismic actions are involved).
    """
    pf = get_partial_factors(design_approach, LimitState.GEO)

    # Footing self-weight including soil overburden above
    A = foundation.area
    t = foundation.thickness_m
    W_pad = A * t * concrete.unit_weight
    W_soil = A * (soil_overburden_depth_mm / 1000.0) * soil_unit_weight_overburden
    W_total = W_pad + W_soil

    # Vertical action including the inertia of the foundation block
    # itself  N_total = N + W + ΔW_v (vertical seismic on block, optional)
    delta_W_v = -seismic.k_v_up * W_total  # upward seismic decreases V
    N_total = N_kN + W_total + delta_W_v

    # Horizontal action: column shear plus inertia of the foundation block
    H_inertia = seismic.k_h * W_total
    H_total = H_kN + H_inertia

    # Moment about base centroid:
    # M_col (column moment at top of footing) plus column shear arm of t,
    # plus inertia of the block at its mid-height.
    M_total = M_kNm + H_kN * t + H_inertia * t / 2.0

    # Eccentricity & contact pressures via BasePressureAnalysis
    from ..core.loading import (
        CombinationEntry,
        LoadCombination,
        LoadType,
        PointLoad,
    )

    seismic_combo = LoadCombination(
        name=f"seismic_{design_approach.value}",
        entries=[
            CombinationEntry(
                load=PointLoad(
                    name="column_seismic",
                    fz=N_kN + delta_W_v,        # variable parts
                    mx=M_kNm,
                    my=0.0,
                    vx=0.0,
                    vy=H_kN,
                ),
                factor=1.0,
            ),
            CombinationEntry(
                load=PointLoad(
                    name="pad_self_weight",
                    fz=W_total,
                    load_type=LoadType.PERMANENT,
                ),
                factor=1.0,
            ),
            CombinationEntry(
                load=PointLoad(
                    name="block_inertia",
                    fz=0.0,
                    mx=H_inertia * (t / 2.0),  # extra moment from block inertia
                    my=0.0,
                    vx=0.0,
                    vy=H_inertia,
                ),
                factor=1.0,
            ),
        ],
    )

    bpa = BasePressureAnalysis(foundation, column)
    press = bpa.calculate_pressures(seismic_combo, include_self_weight=False)

    # Bearing capacity (effective-area + seismic reduction)
    e_x = press.e_x
    e_y = press.e_y
    if drained:
        bc: BearingCapacityResult = drained_bearing_capacity(
            foundation=foundation,
            soil=soil,
            e_x=e_x,
            e_y=e_y,
            H_load=H_total,
            V_load=N_total,
            gamma_Rv=pf.resistance.gamma_Rv,
            gamma_phi=pf.soil.gamma_phi,
            gamma_c=pf.soil.gamma_c,
            gamma_gamma=pf.soil.gamma_gamma,
            formula=bearing_formula,
        )
        # Apply seismic reduction on N_γ term (simplified Pecker)
        phi_d_rad = math.atan(math.tan(math.radians(soil.friction_angle)) / pf.soil.gamma_phi)
        i_seismic = _seismic_inclination_factor(seismic.k_h, phi_d_rad)
        q_ult_seismic = bc.q_ult * i_seismic
    else:
        bc = undrained_bearing_capacity(
            foundation=foundation,
            soil=soil,
            e_x=e_x,
            e_y=e_y,
            H_load=H_total,
            gamma_Rv=pf.resistance.gamma_Rv,
            gamma_cu=pf.soil.gamma_cu,
        )
        # Undrained: seismic effect is captured via i_c with H/(A·c_u),
        # already included in bc.q_ult.
        q_ult_seismic = bc.q_ult

    q_Ed = N_total / max(bc.A_eff, 1e-6)
    q_Rd = q_ult_seismic / pf.resistance.gamma_Rv
    bearing_util = q_Ed / max(q_Rd, 1e-6)

    # Sliding
    phi_rad_d = math.atan(math.tan(math.radians(soil.friction_angle)) / pf.soil.gamma_phi)
    if drained:
        R_friction = N_total * math.tan(phi_rad_d * delta_factor)
        R_cohesion = (soil.cohesion / pf.soil.gamma_c) * bc.A_eff
        H_Rd = (R_friction + R_cohesion) / pf.resistance.gamma_Rh
    else:
        H_Rd = min(
            (soil.cohesion / pf.soil.gamma_cu) * bc.A_eff / pf.resistance.gamma_Rh,
            0.4 * N_total / pf.resistance.gamma_Rh,
        )
    sliding_util = H_total / max(H_Rd, 1e-6)

    # Overturning (about the shortest base edge)
    B = min(foundation.length_m, foundation.width_m)
    M_dst = abs(M_total) + H_total * 0.0  # M_total already includes block inertia
    M_stb = N_total * (B / 2.0)
    overturn_util = M_dst / max(M_stb, 1e-6)

    return SeismicFootingCheck(
        design_approach=design_approach.value,
        N_d=N_total,
        H_d=H_total,
        M_d=M_total,
        e_x=e_x,
        e_y=e_y,
        q_max=press.q_max,
        q_avg=press.q_avg,
        regime=press.regime.value,
        bearing_q_Ed=q_Ed,
        bearing_q_Rd=q_Rd,
        bearing_utilization=bearing_util,
        sliding_H_Ed=H_total,
        sliding_H_Rd=H_Rd,
        sliding_utilization=sliding_util,
        overturning_M_dst=M_dst,
        overturning_M_stb=M_stb,
        overturning_utilization=overturn_util,
        middle_third=abs(e_x) <= foundation.length_m / 6.0 and abs(e_y) <= foundation.width_m / 6.0,
    )


__all__ = [
    "SeismicAction",
    "SeismicFootingCheck",
    "seismic_footing_check",
]
