"""Design of gravity retaining walls (mass concrete, masonry, gabion, crib).

A gravity wall resists the lateral earth thrust **purely by its own
weight**. Stability comes from:

- High self-weight (concrete, gabion baskets, crib + fill, masonry).
- Wide base (typically 0.5 H to 0.7 H).
- Battered front face and (sometimes) inclined back face.

Implemented checks (per EN 1997-1 §9 + Bowles 2001 §14):

1. **Active thrust** (Coulomb) on the back face with wall-soil friction
   `δ_w`; produces a resultant `P_a` inclined δ_w from horizontal.
   The vertical component `P_v = P_a · sin(α + δ_w)` adds to the
   stabilising weight; the horizontal component `P_h = P_a · cos(α + δ_w)`
   is the destabilising action.
2. **Self-weight** with the correct trapezoid centroid (assumes vertical
   back face by default — typical gravity-wall layout).
3. **Sliding** along the base using the wall-soil interface friction
   `δ_b` (NOT the soil internal angle).
4. **Overturning** about the toe — ratio M_dst/M_stb with the GEO
   factors of the design approach (not the EQU set of EN 1997-1 A.2).
5. **Middle-third** for the resultant on the base.
6. **Bearing capacity** of the foundation soil with **load-inclination
   factors** (Hansen / Vesic).
7. **No tension at any horizontal joint** (additional check for
   masonry / gabion / crib where joints have no tensile strength).

Geometry convention:
- x measured from the **toe** (front-bottom corner).
- y measured upward from the base.
- Default geometry has a **vertical back** at x = `bottom_width` and a
  **battered front** from (0, 0) at the toe to (`bottom_width − top_width`,
  H) at the top.

Theory: docs/theory/06_retaining_walls.md §6.1 + Bowles 2001 §14.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

from ..analysis.earth_pressure import Ka_coulomb
from ..codes.eurocode7 import DesignApproach, LimitState, get_partial_factors
from ..core.soil import SoilLayer


class GravityWallMaterial(str, Enum):
    MASS_CONCRETE = "mass_concrete"
    MASONRY = "masonry"
    GABION = "gabion"
    CRIB = "crib"


_UNIT_WEIGHT = {
    GravityWallMaterial.MASS_CONCRETE: 24.0,
    GravityWallMaterial.MASONRY: 22.0,
    GravityWallMaterial.GABION: 18.0,
    GravityWallMaterial.CRIB: 17.0,
}

# Typical wall-soil friction ratios on the back of the wall (δ_w / φ)
_DELTA_W_OVER_PHI = {
    GravityWallMaterial.MASS_CONCRETE: 2.0 / 3.0,   # smooth concrete back
    GravityWallMaterial.MASONRY:       2.0 / 3.0,
    GravityWallMaterial.GABION:        1.0,         # rough — full friction
    GravityWallMaterial.CRIB:          0.85,
}

# Base friction angle factor δ_b / φ_foundation
_DELTA_B_OVER_PHI = {
    GravityWallMaterial.MASS_CONCRETE: 2.0 / 3.0,   # precast
    GravityWallMaterial.MASONRY:       2.0 / 3.0,
    GravityWallMaterial.GABION:        1.0,         # full friction
    GravityWallMaterial.CRIB:          0.85,
}


class GravityWallGeometry(BaseModel):
    """Cross-section of a gravity wall (per metre run).

    Two parts:

    1. **Stem** — a trapezoid with `top_width` at the top, `stem_bottom`
       at its base, height `H`. Default layout: vertical back face on
       the right, battered front on the left.
    2. **Footing / base slab** (optional) — a horizontal rectangle below
       the stem, with optional `toe` extension in front and `heel`
       extension behind. When `toe = heel = 0` and `base_thickness = 0`,
       the wall is a pure trapezoid (no separate footing).

    Coordinates: x measured from the **toe of the footing** (front-bottom
    corner). With `toe > 0`, the stem starts at x = `toe` and ends at
    x = `toe + stem_bottom`. The total footing width is

        B = toe + stem_bottom + heel.
    """

    H: float = Field(..., gt=0.5, description="Stem height (m)")
    top_width: float = Field(..., gt=0.10,
                            description="Stem top width (m)")
    stem_bottom: float = Field(..., gt=0.20,
                              description="Stem width at the base (m)")
    toe: float = Field(0.0, ge=0,
                      description="Footing extension in front of the stem (m)")
    heel: float = Field(0.0, ge=0,
                       description="Footing extension behind the stem (m)")
    base_thickness: float = Field(
        0.0, ge=0,
        description="Footing slab thickness (m). 0 = no separate footing "
                    "(pure trapezoidal gravity wall).",
    )
    back_batter_deg: float = Field(
        0.0, ge=-30.0, le=30.0,
        description="Stem back-face inclination from vertical, deg",
    )

    # ------------------------------------------------------------------
    # Backwards compatibility: accept legacy `bottom_width` argument as
    # an alias for `stem_bottom` (toe and heel default to 0).
    # ------------------------------------------------------------------
    def __init__(self, **data):
        if "bottom_width" in data and "stem_bottom" not in data:
            data["stem_bottom"] = data.pop("bottom_width")
        super().__init__(**data)

    # ------------------------------------------------------------------
    @property
    def B(self) -> float:
        """Total footing width (toe + stem_bottom + heel)."""
        return self.toe + self.stem_bottom + self.heel

    @property
    def bottom_width(self) -> float:
        """Legacy alias for the total footing width."""
        return self.B

    @property
    def stem_area_m2(self) -> float:
        """Cross-section area of the trapezoidal stem only."""
        return 0.5 * (self.top_width + self.stem_bottom) * self.H

    @property
    def footing_area_m2(self) -> float:
        """Cross-section area of the footing slab (0 if no separate slab)."""
        return self.B * self.base_thickness

    @property
    def area_m2(self) -> float:
        """Total cross-section area (stem + footing)."""
        return self.stem_area_m2 + self.footing_area_m2

    @property
    def stem_centroid_x_from_toe_m(self) -> float:
        """x-centroid of the trapezoidal stem alone, measured from the toe
        of the footing.

        For a stem with vertical back and battered front, the local centroid
        (measured from the stem's own toe) is

            x_local = [s² − (s−a)²/3] / (a+s)

        where s = stem_bottom and a = top_width. We then shift by `toe`
        to refer to the footing toe.
        """
        a, s = self.top_width, self.stem_bottom
        x_local = (s ** 2 - (s - a) ** 2 / 3.0) / (a + s)
        return self.toe + x_local

    @property
    def footing_centroid_x_from_toe_m(self) -> float:
        """x-centroid of the footing slab (rectangle), from the toe."""
        return self.B / 2.0

    @property
    def back_face_x_at_y_zero_m(self) -> float:
        """x of the back face at the base of the stem (z = base_thickness)."""
        return self.toe + self.stem_bottom

    @property
    def stem_back_x_at_top_m(self) -> float:
        return self.toe + self.stem_bottom    # vertical back assumed


class GravityWallLoading(BaseModel):
    backfill: SoilLayer
    foundation_soil: SoilLayer
    surcharge_q: float = Field(0.0, ge=0)
    water_height: float = Field(0.0, ge=0)
    backfill_slope_deg: float = Field(
        0.0, ge=-30.0, le=30.0,
        description="Backfill surface slope α (deg above horizontal)",
    )


@dataclass
class GravityWallResult:
    # Self-weight contributions (per metre run)
    W_stem_kN_per_m: float
    W_footing_kN_per_m: float
    W_backfill_on_heel_kN_per_m: float
    W_kN_per_m: float            # = sum of the above (kept for back-compat)
    x_W_m: float                 # combined centroid of the stabilising weights
    # Active thrust (Coulomb)
    K_a: float
    P_a_total_kN_per_m: float
    P_h_kN_per_m: float
    P_v_kN_per_m: float
    z_P_h_m: float                    # lever arm above base
    P_w_kN_per_m: float               # hydrostatic
    # Reduced quantities (factored, design)
    V_d: float
    H_d: float
    M_dst: float
    M_stb: float
    e_x: float
    middle_third: bool
    q_max_kPa: float
    q_min_kPa: float
    # Verdicts
    bearing_utilization: float
    sliding_utilization: float
    overturning_utilization: float
    joint_tension: bool
    all_ok: bool


def _hansen_bearing(
    phi_deg: float, gamma: float, B_eff: float,
    V_d: float, H_d: float, c: float = 0.0,
) -> float:
    """Hansen / Vesic q_ult with inclination factors and effective width.

    Returns q_ult in kPa.
    """
    phi = math.radians(phi_deg)
    if phi < 1e-6:
        Nq = 1.0
        Nc = math.pi + 2.0
        Ng = 0.0
    else:
        Nq = math.exp(math.pi * math.tan(phi)) * math.tan(math.pi/4 + phi/2) ** 2
        Nc = (Nq - 1.0) / math.tan(phi)
        Ng = 2.0 * (Nq - 1.0) * math.tan(phi)
    # Vesic inclination factors for strip:
    if V_d > 0 and phi_deg > 0:
        i_q = max(0.0, 1.0 - H_d / V_d) ** 2
        i_g = max(0.0, 1.0 - H_d / V_d) ** 3
    else:
        i_q = i_g = 1.0
    if c > 0 and V_d > 0:
        i_c = (i_q * Nq - 1.0) / max(Nq - 1.0, 1e-9) if Nq > 1.0 else i_q
    else:
        i_c = i_q
    q_ult = c * Nc * i_c + 0.5 * gamma * B_eff * Ng * i_g
    return max(q_ult, 0.0)


class GravityWallDesigner:
    """End-to-end design check of a gravity wall (Coulomb thrust + Hansen BC)."""

    def __init__(
        self,
        geometry: GravityWallGeometry,
        loading: GravityWallLoading,
        material: GravityWallMaterial = GravityWallMaterial.MASS_CONCRETE,
        design_approach: DesignApproach = DesignApproach.DA2,
    ):
        self.geo = geometry
        self.load = loading
        self.material = material
        self.gamma_wall = _UNIT_WEIGHT[material]
        self.delta_w_ratio = _DELTA_W_OVER_PHI[material]
        self.delta_b_ratio = _DELTA_B_OVER_PHI[material]
        self.da = design_approach

    # ------------------------------------------------------------------
    def check(self) -> GravityWallResult:
        pf = get_partial_factors(self.da, LimitState.GEO)
        gG_unfav = pf.actions.gamma_G_unfav
        gG_fav = pf.actions.gamma_G_fav

        # ---- 1) Self-weight contributions ----
        # Stem
        W_stem = self.geo.stem_area_m2 * self.gamma_wall
        x_stem = self.geo.stem_centroid_x_from_toe_m
        # Footing slab (typically mass concrete regardless of stem material)
        gamma_footing = 24.0 if self.geo.base_thickness > 0 else 0.0
        W_footing = self.geo.footing_area_m2 * gamma_footing
        x_footing = self.geo.footing_centroid_x_from_toe_m
        # Backfill on the heel (acts as stabilising weight on top of the slab)
        gamma_fill = self.load.backfill.unit_weight
        W_fill = (self.geo.heel * self.geo.H * gamma_fill
                  if self.geo.heel > 0 else 0.0)
        x_fill = (self.geo.toe + self.geo.stem_bottom + self.geo.heel / 2.0
                  if self.geo.heel > 0 else 0.0)

        W_total = W_stem + W_footing + W_fill
        if W_total > 0:
            x_W = (W_stem * x_stem + W_footing * x_footing
                   + W_fill * x_fill) / W_total
        else:
            x_W = 0.0
        W_k = W_total  # backwards-compatible alias

        # ---- 2) Coulomb active thrust on the back face ----
        # Design strength of the backfill (set M of the design approach):
        # tan φ_d = tan φ_k / γ_φ (EN 1997-1 §2.4.6.2). DEFECTO CORREGIDO
        # (1.1.0): el empuje se calculaba con φ_k en todos los enfoques, de
        # modo que DA1-C2 y DA3 (M2, γ_φ = 1,25) no mayoraban el empuje.
        phi = math.degrees(math.atan(
            math.tan(math.radians(self.load.backfill.friction_angle)) / pf.soil.gamma_phi))
        gamma_f = self.load.backfill.unit_weight
        delta_w = phi * self.delta_w_ratio
        beta_back = 90.0 + self.geo.back_batter_deg   # 90 = vertical
        alpha = self.load.backfill_slope_deg
        # Total height over which the thrust acts (stem + footing if present).
        # The active thrust pushes on the vertical plane that goes from the
        # back-of-heel up to the top of the stem.
        H_back = self.geo.H + self.geo.base_thickness

        K_a = Ka_coulomb(phi_deg=phi, delta_deg=delta_w,
                        beta_deg=beta_back, alpha_deg=alpha)

        # Total Coulomb thrust on the back face (inclined δ_w to the normal
        # of the back face):
        P_a_soil = 0.5 * K_a * gamma_f * H_back ** 2
        P_a_surch = K_a * self.load.surcharge_q * H_back
        P_a_total = P_a_soil + P_a_surch
        # Lever arm of horizontal component above the base:
        z_a = (
            P_a_soil * (H_back / 3.0)
            + P_a_surch * (H_back / 2.0)
        ) / max(P_a_total, 1e-9)

        # Decompose into horizontal and vertical components.
        # For a back face inclined β from horizontal and wall-soil friction δ_w,
        # the resultant is at angle (β + δ_w − 90°) from horizontal:
        theta = math.radians(beta_back + delta_w - 90.0)
        P_h_k = P_a_total * math.cos(theta)
        P_v_k = P_a_total * math.sin(theta)   # downward, helps stability
        P_h_soil_k = P_a_soil * math.cos(theta)
        P_h_surch_k = P_a_surch * math.cos(theta)

        # ---- 3) Water thrust (hydrostatic, fully drained back not assumed) ----
        H_w = self.load.water_height
        P_w_k = 0.5 * 9.81 * H_w ** 2 if H_w > 0 else 0.0
        z_w = H_w / 3.0

        # ---- 4) Factored actions ----
        # The surcharge thrust is a VARIABLE action: γ_Q, not γ_G (EN 1990
        # Tabla A1.2; corregido en 1.1.0, antes iba con γ_G).
        gQ = pf.actions.gamma_Q_unfav
        W_d_fav = gG_fav * W_k
        P_v_d_fav = gG_fav * P_v_k                       # P_v is favourable
        P_h_d = gG_unfav * P_h_soil_k + gQ * P_h_surch_k
        P_w_d = gG_unfav * P_w_k

        # ---- 5) Lever arms (about toe) ----
        x_back = self.geo.back_face_x_at_y_zero_m
        M_stb = W_d_fav * x_W + P_v_d_fav * x_back
        M_dst = (gG_unfav * P_h_soil_k * (H_back / 3.0)
                 + gQ * P_h_surch_k * (H_back / 2.0) + P_w_d * z_w)

        V_d = W_d_fav + P_v_d_fav
        H_d = P_h_d + P_w_d

        # ---- 6) Eccentricity + contact pressures ----
        x_R = (M_stb - M_dst) / V_d if V_d > 0 else 0.0
        e_x = self.geo.B / 2.0 - x_R
        middle_third = abs(e_x) <= self.geo.B / 6.0
        if middle_third:
            q_max = V_d / self.geo.B * (1.0 + 6.0 * abs(e_x) / self.geo.B)
            q_min = V_d / self.geo.B * (1.0 - 6.0 * abs(e_x) / self.geo.B)
            B_eff = self.geo.B
        else:
            B_eff = max(3.0 * (self.geo.B / 2.0 - abs(e_x)), 1e-6)
            q_max = 2.0 * V_d / B_eff
            q_min = 0.0

        # ---- 7) Bearing capacity (Hansen, with i factors and B_eff) ----
        phi_g = self.load.foundation_soil.friction_angle
        gamma_g = self.load.foundation_soil.unit_weight
        # Design φ:
        phi_g_d = math.degrees(math.atan(math.tan(math.radians(phi_g)) / pf.soil.gamma_phi))
        q_ult = _hansen_bearing(phi_deg=phi_g_d, gamma=gamma_g, B_eff=B_eff,
                                V_d=V_d, H_d=H_d,
                                c=self.load.foundation_soil.cohesion / pf.soil.gamma_c)
        q_Rd = q_ult / pf.resistance.gamma_Rv
        bearing_util = q_max / max(q_Rd, 1e-6)

        # ---- 8) Sliding on the base interface ----
        delta_b_deg = phi_g_d * self.delta_b_ratio
        R_h_friction = V_d * math.tan(math.radians(delta_b_deg))
        R_h_cohesion = (self.load.foundation_soil.cohesion / pf.soil.gamma_c) * self.geo.B
        R_h = (R_h_friction + R_h_cohesion) / pf.resistance.gamma_Rh
        sliding_util = H_d / max(R_h, 1e-6)

        # ---- 9) Overturning (EQU) ----
        overturning_util = M_dst / max(M_stb, 1e-6)

        # ---- 10) Joint-tension flag ----
        joint_tension = not middle_third

        all_ok = (
            bearing_util <= 1.0
            and sliding_util <= 1.0
            and overturning_util <= 1.0
            and (not joint_tension or self.material == GravityWallMaterial.MASS_CONCRETE)
        )

        return GravityWallResult(
            W_stem_kN_per_m=W_stem,
            W_footing_kN_per_m=W_footing,
            W_backfill_on_heel_kN_per_m=W_fill,
            W_kN_per_m=W_k, x_W_m=x_W,
            K_a=K_a, P_a_total_kN_per_m=P_a_total,
            P_h_kN_per_m=P_h_k, P_v_kN_per_m=P_v_k, z_P_h_m=z_a,
            P_w_kN_per_m=P_w_k,
            V_d=V_d, H_d=H_d,
            M_dst=M_dst, M_stb=M_stb,
            e_x=e_x, middle_third=middle_third,
            q_max_kPa=q_max, q_min_kPa=q_min,
            bearing_utilization=bearing_util,
            sliding_utilization=sliding_util,
            overturning_utilization=overturning_util,
            joint_tension=joint_tension,
            all_ok=all_ok,
        )


__all__ = [
    "GravityWallMaterial",
    "GravityWallGeometry",
    "GravityWallLoading",
    "GravityWallResult",
    "GravityWallDesigner",
]
