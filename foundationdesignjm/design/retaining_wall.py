"""End-to-end design of a cantilever retaining wall.

Handles all the checks for a T-shaped cantilever wall:

1. Geometry validation and self-weight assembly.
2. Earth-pressure thrust (active + surcharge + water) on a notional
   vertical plane through the back of the heel — the "virtual back".
3. Sliding, overturning and middle-third (EQU) checks.
4. Bearing capacity verification (effective-width method) — delegated to
   `analysis.bearing_capacity`.
5. Structural checks at the **stem base**, **heel** and **toe** —
   producing bending moments and shears per metre run for EC2 design.

Sign convention: x measured from the toe (front face of the wall);
positive moments cause tension at the inner face (stem) / top (heel) /
bottom (toe). All loads per metre run of wall length.

Theory: docs/theory/06_retaining_walls.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from ..analysis.bearing_capacity import (
    BearingCapacityFormula,
    drained_bearing_capacity,
    undrained_bearing_capacity,
)
from ..analysis.earth_pressure import (
    active_thrust,
    at_rest_thrust,
    passive_thrust,
)
from ..codes.eurocode7 import DesignApproach, LimitState, get_partial_factors
from ..core.geometry import RectangularFoundation
from ..core.material import Concrete
from ..core.soil import SoilLayer


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class CantileverWallGeometry(BaseModel):
    """T-shaped cantilever retaining wall geometry (per metre run).

    All dimensions in metres. The wall is assumed vertical (β = 90°).

           |‾‾‾| ← top of stem (thickness `stem_top`)
           |   |
           |   |
           |   | H (total height above base level)
           |   |
           |___|________ ← top of base slab
           |             |
        ___|_____________|__________
        ←  toe → ← stem → ←  heel  →   (widths)
                     ↑ base slab thickness `base_thickness`
    """

    H: float = Field(..., gt=0, description="Total height of stem above base slab top, m")
    stem_top: float = Field(..., gt=0.05, description="Stem thickness at top, m")
    stem_bottom: float = Field(..., gt=0.05, description="Stem thickness at base, m")
    toe: float = Field(..., ge=0, description="Toe length (in front of stem), m")
    heel: float = Field(..., ge=0, description="Heel length (behind stem), m")
    base_thickness: float = Field(..., gt=0, description="Base slab thickness, m")
    embedment_front: float = Field(0.8, ge=0, description="Soil depth above the toe, m")
    key_depth: float = Field(0.0, ge=0, description="Optional shear key under the base, m")

    @property
    def B(self) -> float:
        """Total base slab width = toe + stem_bottom + heel (m)."""
        return self.toe + self.stem_bottom + self.heel

    @property
    def H_total(self) -> float:
        """Total height from base bottom to top of stem (m)."""
        return self.H + self.base_thickness

    @property
    def x_back_of_heel(self) -> float:
        """X-coordinate of the back of the heel, measured from the toe (m)."""
        return self.B

    @model_validator(mode="after")
    def _check_consistency(self):
        if self.stem_bottom < self.stem_top:
            raise ValueError("stem_bottom must be ≥ stem_top (taper inward only)")
        if self.B < 0.5:
            raise ValueError("Base width too small (< 0.5 m)")
        return self


# ---------------------------------------------------------------------------
# Load case
# ---------------------------------------------------------------------------

class RetainingWallLoading(BaseModel):
    """All actions acting on the retaining wall.

    The active thrust on a cantilever wall is computed on a **virtual
    vertical plane** through the back of the heel. Two analyses are
    standard:

    - **Rankine** on the virtual back (recommended for cantilever walls
      with a heel ≥ H·tan(45 − φ/2)). The thrust direction follows the
      backfill slope (δ_virtual = α).
    - **Coulomb on the actual stem back** (used when the heel is too
      short to develop a Rankine zone). The thrust acts inclined at δ_w
      relative to the back face normal.

    Use `analysis_method` to choose.

    `delta_over_phi` is ONLY used when `analysis_method = "coulomb"` and
    represents the wall-soil friction on the actual stem back.
    """

    backfill: SoilLayer
    foundation_soil: SoilLayer
    surcharge_q: float = Field(0.0, ge=0, description="Uniform surcharge on backfill, kN/m²")
    water_height: float = Field(0.0, ge=0, description="Water-table height above base, m")
    backfill_slope_deg: float = Field(0.0, ge=-30, le=30,
        description="Backfill slope angle α (deg). Used as δ on the virtual "
                    "back in Rankine analysis.")
    drained_design: bool = Field(True, description="Use drained shear strength")
    analysis_method: str = Field(
        "rankine_virtual_back",
        description="'rankine_virtual_back' (default) or 'coulomb_actual_back'",
    )
    # Kept for backwards compatibility (deprecated):
    use_coulomb: bool = Field(
        True, description="DEPRECATED — use `analysis_method` instead",
    )
    delta_over_phi: float = Field(2.0 / 3.0, ge=0, le=1,
        description="δ/φ' on the actual stem back (Coulomb method only)")

    @property
    def gamma_w(self) -> float:
        return 9.81  # kN/m^3


# ---------------------------------------------------------------------------
# Check result bundle
# ---------------------------------------------------------------------------

@dataclass
class WallActionResult:
    """All actions reduced to the base-slab toe (per metre run)."""

    V_d: float       # Total vertical force [kN/m] (positive down)
    H_d: float       # Total horizontal force [kN/m] (positive towards the toe)
    M_dst: float     # Destabilising moment about toe [kN·m/m]
    M_stb: float     # Stabilising moment about toe [kN·m/m]
    x_R: float       # Distance from toe to the resultant on the base plane [m]
    e_x: float       # Eccentricity from base centroid [m]
    qty_components: List[Tuple[str, float, float, float]] = field(default_factory=list)
    # (label, F_v, F_h, lever_arm_about_toe)

    @property
    def M_net(self) -> float:
        return self.M_stb - self.M_dst

    @property
    def overturning_FoS(self) -> float:
        return self.M_stb / self.M_dst if self.M_dst > 0 else float("inf")


@dataclass
class RetainingWallCheck:
    """Full ULS check bundle for one (DA, loading) configuration."""

    design_approach: str
    actions: WallActionResult

    # Bearing
    bearing_q_Ed: float
    bearing_q_Rd: float
    bearing_utilization: float

    # Sliding
    sliding_H_Ed: float
    sliding_H_Rd: float
    sliding_utilization: float
    include_passive: bool

    # Overturning
    overturning_utilization: float
    middle_third: bool

    # Structural critical-section forces (per metre run)
    M_stem_base: float
    V_stem_base: float
    M_heel: float
    V_heel: float
    M_toe: float
    V_toe: float

    @property
    def all_ok(self) -> bool:
        return (
            self.bearing_utilization <= 1.0
            and self.sliding_utilization <= 1.0
            and self.overturning_utilization <= 1.0
        )


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class CantileverWallDesigner:
    """Compose geometry + loads + DA factors and run all checks."""

    def __init__(
        self,
        geometry: CantileverWallGeometry,
        loading: RetainingWallLoading,
        concrete: Concrete,
        design_approach: DesignApproach = DesignApproach.DA2,
        bearing_formula: BearingCapacityFormula = BearingCapacityFormula.CHEN_EC7,
        include_passive_in_front: bool = False,
    ):
        self.geo = geometry
        self.load = loading
        self.concrete = concrete
        self.da = design_approach
        self.bearing_formula = bearing_formula
        self.include_passive = include_passive_in_front

    # ---------------------------------------------------------- self-weights
    def _self_weight_components(self) -> List[Tuple[str, float, float]]:
        """List of (label, weight_kN_per_m, lever_arm_about_toe_m) for stabilising loads."""
        g = self.geo
        gc = self.concrete.unit_weight
        gamma_soil = self.load.backfill.unit_weight

        items: List[Tuple[str, float, float]] = []
        # 1. Base slab — rectangular, centroid at B/2
        W_base = g.B * g.base_thickness * gc
        items.append(("base", W_base, g.B / 2.0))
        # 2. Stem (rectangular for now — taper handled approximately)
        avg_stem = 0.5 * (g.stem_top + g.stem_bottom)
        W_stem = avg_stem * g.H * gc
        x_stem = g.toe + g.stem_bottom / 2.0  # centroid of stem base
        items.append(("stem", W_stem, x_stem))
        # 3. Backfill over the heel
        W_fill = g.heel * g.H * gamma_soil
        x_fill = g.toe + g.stem_bottom + g.heel / 2.0
        items.append(("backfill_heel", W_fill, x_fill))
        # 4. Surcharge above the heel (variable load)
        if self.load.surcharge_q > 0:
            W_surcharge = g.heel * self.load.surcharge_q
            items.append(("surcharge_heel", W_surcharge, x_fill))
        # 5. Soil over the toe (if any embedment)
        if g.embedment_front > 0:
            W_toe_soil = g.toe * g.embedment_front * gamma_soil
            items.append(("soil_toe", W_toe_soil, g.toe / 2.0))
        return items

    # ----------------------------------------------------- earth-pressure
    def _virtual_back_height(self) -> float:
        """Height of the virtual vertical plane behind the wall (back of heel)."""
        return self.geo.H + self.geo.base_thickness

    def _active_thrust(self) -> Tuple[float, float, float]:
        """(P_h, P_v, lever_arm_about_toe_for_P_h).

        Routes to either:
        - **Rankine on the virtual back**: thrust acts parallel to the
          backfill slope (δ_virtual = α). For α = 0 the thrust is purely
          horizontal.
        - **Coulomb on the actual stem back**: thrust inclined at δ_w
          from the back-face normal. The vertical component is added to
          the stabilising weight.
        """
        import math
        H_v = self._virtual_back_height()
        phi = self.load.backfill.friction_angle
        gamma = self.load.backfill.unit_weight
        alpha = self.load.backfill_slope_deg

        if self.load.analysis_method == "rankine_virtual_back":
            # Rankine on the virtual back: K_a from the slope-corrected formula
            # and the thrust is parallel to the slope (δ_virtual = α).
            res = active_thrust(
                H=H_v, gamma=gamma, phi_deg=phi,
                c_prime=self.load.backfill.cohesion,
                surcharge_q=self.load.surcharge_q,
                use_coulomb=False,
                delta_deg=0.0, beta_deg=90.0, alpha_deg=alpha,
            )
            alpha_rad = math.radians(alpha)
            P_total = res.thrust_P
            # When sloping: project onto horizontal/vertical
            P_h = P_total * math.cos(alpha_rad)
            P_v = P_total * math.sin(alpha_rad)  # downward, helps stability
            return P_h, P_v, res.point_of_application_z

        # Coulomb on the actual stem back
        delta = phi * self.load.delta_over_phi
        res = active_thrust(
            H=H_v, gamma=gamma, phi_deg=phi,
            c_prime=self.load.backfill.cohesion,
            surcharge_q=self.load.surcharge_q,
            use_coulomb=True,
            delta_deg=delta, beta_deg=90.0, alpha_deg=alpha,
        )
        delta_rad = math.radians(delta)
        # res.thrust_P is the total magnitude when use_coulomb=True.
        # Components on horizontal and vertical:
        P_h = res.thrust_P * math.cos(delta_rad)
        P_v = res.thrust_P * math.sin(delta_rad)
        return P_h, P_v, res.point_of_application_z

    def _water_thrust(self) -> Tuple[float, float]:
        """(P_w, lever_arm_about_toe)."""
        H_w = self.load.water_height
        if H_w <= 0:
            return 0.0, 0.0
        P_w = 0.5 * self.load.gamma_w * H_w ** 2
        lever = H_w / 3.0
        return P_w, lever

    def _passive_thrust_front(self) -> Tuple[float, float]:
        """Passive resistance in front of the toe (optional)."""
        if not self.include_passive or self.geo.embedment_front <= 0:
            return 0.0, 0.0
        res = passive_thrust(
            H=self.geo.embedment_front,
            gamma=self.load.foundation_soil.unit_weight,
            phi_deg=self.load.foundation_soil.friction_angle,
            c_prime=self.load.foundation_soil.cohesion,
        )
        return res.thrust_P, res.point_of_application_z

    # -------------------------------------------------- factored ULS actions
    def _factored_actions(self) -> WallActionResult:
        pf = get_partial_factors(self.da, LimitState.GEO)
        gG_unfav = pf.actions.gamma_G_unfav
        gG_fav = pf.actions.gamma_G_fav
        gQ = pf.actions.gamma_Q_unfav

        # Self-weights — γG_fav for stabilising
        sw = self._self_weight_components()
        V_stb = 0.0
        M_stb = 0.0
        components: List[Tuple[str, float, float, float]] = []
        for name, W, lever in sw:
            # Surcharge over heel is variable, factor with γQ but stabilising
            factor = gQ if name == "surcharge_heel" else gG_fav
            W_d = factor * W
            V_stb += W_d
            M_stb += W_d * lever
            components.append((name, W_d, 0.0, lever))

        # Active thrust (destabilising) on the virtual back
        P_h, P_v, z_P = self._active_thrust()
        # γG_unfav on earth thrust (the soil weight is a permanent load)
        P_h_d = gG_unfav * P_h
        P_v_d = gG_unfav * P_v
        # P_v acts downward on the heel — adds to stabilising V, M_stb
        V_stb_extra = P_v_d
        M_stb += P_v_d * self.geo.x_back_of_heel
        components.append(("active_Pv", P_v_d, 0.0, self.geo.x_back_of_heel))
        # P_h lever is z above base bottom
        z_P_above_base = z_P  # already measured from base bottom (full virtual height)
        M_dst = P_h_d * z_P_above_base
        components.append(("active_Ph", 0.0, P_h_d, z_P_above_base))

        # Water thrust (γG_unfav)
        P_w, z_w = self._water_thrust()
        if P_w > 0:
            P_w_d = gG_unfav * P_w
            M_dst += P_w_d * z_w
            components.append(("water", 0.0, P_w_d, z_w))
        else:
            P_w_d = 0.0

        V_d = V_stb + V_stb_extra
        H_d = P_h_d + P_w_d

        # Distance from toe to resultant on base plane
        # Sum of moments about toe (V·x) — we want where the net resultant crosses
        x_R = (M_stb - M_dst) / V_d if V_d > 0 else 0.0
        e_x = self.geo.B / 2.0 - x_R

        return WallActionResult(
            V_d=V_d, H_d=H_d, M_dst=M_dst, M_stb=M_stb,
            x_R=x_R, e_x=e_x, qty_components=components,
        )

    # ------------------------------------------------ structural critical sections
    def _structural_forces(self, actions: WallActionResult) -> dict:
        """Bending moments and shears at the three critical sections."""
        g = self.geo
        phi = self.load.backfill.friction_angle
        gamma = self.load.backfill.unit_weight
        delta = phi * self.load.delta_over_phi if self.load.use_coulomb else 0.0
        pf = get_partial_factors(self.da, LimitState.STR)
        gG = pf.actions.gamma_G_unfav
        gQ = pf.actions.gamma_Q_unfav

        # --- STEM base: active pressure on the stem only (height H) -----
        import math
        H_stem = g.H
        res_stem = active_thrust(
            H=H_stem,
            gamma=gamma,
            phi_deg=phi,
            c_prime=self.load.backfill.cohesion,
            surcharge_q=self.load.surcharge_q,
            use_coulomb=self.load.use_coulomb,
            delta_deg=delta,
            beta_deg=90.0,
            alpha_deg=0.0,
        )
        P_h_stem = gG * res_stem.thrust_P
        # The lever arm for the stem moment is z_P about the base of the stem
        # (the section at the top of base slab). z_P is measured from toe of
        # the virtual back, i.e. from the base bottom — recompute relative to stem base.
        # For Rankine with surcharge, the moment about stem base:
        Ka = res_stem.coefficient_K
        M_earth = gG * 0.5 * Ka * gamma * H_stem ** 2 * (H_stem / 3.0)
        M_surch = gQ * Ka * self.load.surcharge_q * H_stem * (H_stem / 2.0)
        M_stem_base = M_earth + M_surch
        V_stem_base = (
            gG * 0.5 * Ka * gamma * H_stem ** 2
            + gQ * Ka * self.load.surcharge_q * H_stem
        )

        # --- HEEL: net upward soil reaction minus downward backfill+self-weight ---
        # Approximate the soil reaction at the heel end (q_min) and at the
        # stem face (q_at_stem) using linear distribution under V_d/B with e_x.
        V = actions.V_d
        B = g.B
        e = actions.e_x
        q_avg = V / B
        if abs(e) <= B / 6.0:
            q_max = q_avg * (1.0 + 6.0 * e / B)
            q_min = q_avg * (1.0 - 6.0 * e / B)
        else:
            # Triangular distribution: only a' = 3*(B/2 - |e|) is active
            a_prime = max(3.0 * (B / 2.0 - abs(e)), 1e-6)
            q_peak = 2.0 * V / a_prime
            # By sign of e: if e > 0 (towards heel), peak at heel
            if e > 0:
                q_max, q_min = q_peak, 0.0
            else:
                q_max, q_min = 0.0, q_peak  # peak at toe
        # By convention e > 0 means resultant towards heel (large M_stab)
        # Heel section is at x = toe + stem_bottom from the toe
        x_heel = g.toe + g.stem_bottom
        # Linear interpolation of q_soil at x_heel:
        if abs(e) <= B / 6.0:
            q_at_heel_face = q_avg * (1.0 + 6.0 * e * (x_heel - B / 2.0) / (B ** 2 / 6.0))
        else:
            q_at_heel_face = max(q_min, q_max) * 0.5
        # Downward loads over the heel: self-weight slab + backfill + surcharge
        gc = self.concrete.unit_weight
        w_slab = gc * g.base_thickness                   # kN/m of heel slab area (per m run × m)
        w_fill = gamma * g.H                             # kN/m
        w_surch = self.load.surcharge_q
        w_down = gG * w_slab + gG * w_fill + gQ * w_surch
        # Net upward per metre run of heel x B... approximate with trapezoidal q
        q_heel_avg = 0.5 * (q_at_heel_face + q_min if e > 0 else q_max)
        net_up = q_heel_avg - w_down
        # Heel moment about stem face (per m run)
        # Approximate by treating net as uniform over heel length
        M_heel = net_up * g.heel ** 2 / 2.0
        V_heel = net_up * g.heel

        # --- TOE: similar, but soil reaction acts up and dominates -----
        # Upward q at toe edge and at stem face
        if abs(e) <= B / 6.0:
            q_at_toe_face = q_avg * (1.0 + 6.0 * e * (g.toe - B / 2.0) / (B ** 2 / 6.0))
        else:
            q_at_toe_face = max(q_min, q_max) * 0.5
        w_down_toe = gG * gc * g.base_thickness + gG * gamma * g.embedment_front
        # Use the q value at the wall face (toe-end) — conservative
        net_up_toe = max(q_at_toe_face, q_max) - w_down_toe
        M_toe = net_up_toe * g.toe ** 2 / 2.0
        V_toe = net_up_toe * g.toe

        return {
            "M_stem_base": M_stem_base,
            "V_stem_base": V_stem_base,
            "M_heel": abs(M_heel),
            "V_heel": abs(V_heel),
            "M_toe": abs(M_toe),
            "V_toe": abs(V_toe),
        }

    # --------------------------------------------------------------- run
    def check(self) -> RetainingWallCheck:
        actions = self._factored_actions()
        pf = get_partial_factors(self.da, LimitState.GEO)

        # --- Bearing capacity (effective area method) -----------------
        # Treat the base as a long strip (L >> B), effective width B' = B - 2|e|
        B = self.geo.B
        e = abs(actions.e_x)
        B_eff = max(B - 2.0 * e, 1e-6)
        fake_fdn = RectangularFoundation(
            length=10000.0,            # 10 m strip surrogate
            width=B * 1000.0,
            thickness=self.geo.base_thickness * 1000.0,
            embedment_depth=self.geo.embedment_front * 1000.0 or 1.0,
        )
        if self.load.drained_design:
            bc = drained_bearing_capacity(
                foundation=fake_fdn,
                soil=self.load.foundation_soil,
                e_x=0.0,
                e_y=e,
                H_load=actions.H_d * 10.0,   # per 10 m strip
                V_load=actions.V_d * 10.0,
                gamma_Rv=pf.resistance.gamma_Rv,
                gamma_phi=pf.soil.gamma_phi,
                gamma_c=pf.soil.gamma_c,
                gamma_gamma=pf.soil.gamma_gamma,
                formula=self.bearing_formula,
            )
        else:
            bc = undrained_bearing_capacity(
                foundation=fake_fdn,
                soil=self.load.foundation_soil,
                e_x=0.0,
                e_y=e,
                H_load=actions.H_d * 10.0,
                gamma_Rv=pf.resistance.gamma_Rv,
                gamma_cu=pf.soil.gamma_cu,
            )
        q_Ed = actions.V_d / B_eff
        q_Rd = bc.q_ult / pf.resistance.gamma_Rv
        bearing_util = q_Ed / max(q_Rd, 1e-6)

        # --- Sliding -------------------------------------------------
        import math
        phi_b = math.radians(self.load.foundation_soil.friction_angle) / pf.soil.gamma_phi
        tan_phi_b_d = math.tan(phi_b)
        R_friction = actions.V_d * tan_phi_b_d
        R_cohesion = (
            self.load.foundation_soil.cohesion / pf.soil.gamma_c
        ) * B
        R_passive = 0.0
        if self.include_passive:
            P_p, _ = self._passive_thrust_front()
            R_passive = P_p / pf.resistance.gamma_R_e if hasattr(pf.resistance, "gamma_R_e") else P_p / 1.4
        H_Rd = (R_friction + R_cohesion) / pf.resistance.gamma_Rh + R_passive
        sliding_util = actions.H_d / max(H_Rd, 1e-6)

        # --- Overturning (EQU) ----------------------------------------
        pf_equ = get_partial_factors(self.da, LimitState.EQU)
        # Recompute with EQU factors quickly using the same components
        equ_M_dst = 0.0
        equ_M_stb = 0.0
        for name, F_v, F_h, lever in actions.qty_components:
            if F_h > 0:
                equ_M_dst += F_h * lever * (pf_equ.actions.gamma_Q_unfav if name == "water" else pf_equ.actions.gamma_G_unfav)
            else:
                equ_M_stb += F_v * lever * pf_equ.actions.gamma_G_fav
        overturn_util = equ_M_dst / max(equ_M_stb, 1e-6)

        # --- Structural critical sections -----------------------------
        struct = self._structural_forces(actions)

        return RetainingWallCheck(
            design_approach=self.da.value,
            actions=actions,
            bearing_q_Ed=q_Ed,
            bearing_q_Rd=q_Rd,
            bearing_utilization=bearing_util,
            sliding_H_Ed=actions.H_d,
            sliding_H_Rd=H_Rd,
            sliding_utilization=sliding_util,
            include_passive=self.include_passive,
            overturning_utilization=overturn_util,
            middle_third=abs(actions.e_x) <= self.geo.B / 6.0,
            M_stem_base=struct["M_stem_base"],
            V_stem_base=struct["V_stem_base"],
            M_heel=struct["M_heel"],
            V_heel=struct["V_heel"],
            M_toe=struct["M_toe"],
            V_toe=struct["V_toe"],
        )


__all__ = [
    "CantileverWallGeometry",
    "RetainingWallLoading",
    "WallActionResult",
    "RetainingWallCheck",
    "CantileverWallDesigner",
]
