"""Design of Mechanically Stabilized Earth (MSE) retaining walls.

An MSE wall is built by placing horizontal **reinforcement layers**
(steel strips, welded mesh or polymer geogrids) in compacted granular
fill behind a precast concrete or modular block facing. The reinforced
block acts as a coherent gravity mass.

Two distinct failure check groups:

A) **External stability** — treat the reinforced block as a single
   monolithic gravity wall and check:
   - Sliding along the base.
   - Overturning about the toe.
   - Bearing capacity.
   - Global slope stability (outside scope here, recommend Bishop /
     Spencer in a dedicated geotechnical tool).

B) **Internal stability** — each reinforcement layer must:
   - Have **tensile capacity** ≥ T_max,i (the horizontal force in the
     layer at its depth).
   - Have **enough length beyond the active wedge** so that the pull-out
     resistance ≥ T_max,i.

The active-zone boundary is the Rankine failure plane inclined at
`45° + φ'/2` from horizontal, starting at the toe.

Reference: AASHTO LRFD §11.10 + FHWA-NHI-10-024.
Theory: docs/theory/06_retaining_walls.md §6.1 (MSE walls).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from ..analysis.earth_pressure import Ka_rankine
from ..codes.eurocode7 import DesignApproach, LimitState, get_partial_factors


class MSEReinforcementType(str, Enum):
    STEEL_STRIP = "steel_strip"
    STEEL_GRID = "steel_grid"
    GEOGRID_HDPE = "geogrid_hdpe"
    GEOGRID_PET = "geogrid_pet"


# Allowable design strength (kN/m of reinforcement width) — illustrative
_T_ALLOW_kN_per_m = {
    MSEReinforcementType.STEEL_STRIP: 50.0,    # one 50 mm wide strip
    MSEReinforcementType.STEEL_GRID: 80.0,
    MSEReinforcementType.GEOGRID_HDPE: 35.0,
    MSEReinforcementType.GEOGRID_PET: 60.0,
}

# Interface friction coefficient F* between fill and reinforcement
_FRICTION_F_STAR = {
    MSEReinforcementType.STEEL_STRIP: 0.40,
    MSEReinforcementType.STEEL_GRID: 0.80,
    MSEReinforcementType.GEOGRID_HDPE: 0.67,
    MSEReinforcementType.GEOGRID_PET: 0.67,
}


class MSELayer(BaseModel):
    """One horizontal reinforcement layer."""

    z_below_top_m: float = Field(..., ge=0)
    length_m: float = Field(..., gt=0)
    reinforcement_type: MSEReinforcementType
    spacing_vertical_m: float = Field(..., gt=0,
        description="Vertical spacing tributary to this layer (m)")


class MSEWallGeometry(BaseModel):
    H: float = Field(..., gt=2.0, description="Wall height (m)")
    B_reinforced: float = Field(
        ..., gt=0.5, description="Width of the reinforced block at the base (m)",
    )
    facing_thickness: float = Field(0.15, gt=0)
    layers: List[MSELayer]


class MSELoading(BaseModel):
    phi_fill_deg: float = Field(..., ge=20, le=45)
    gamma_fill_kN_m3: float = Field(..., gt=10)
    surcharge_q: float = Field(0.0, ge=0)
    phi_foundation_deg: float = Field(..., ge=20, le=45)
    gamma_foundation_kN_m3: float = Field(..., gt=10)


@dataclass
class MSEExternalCheck:
    W_kN_per_m: float
    P_a_h_kN_per_m: float
    e_x_m: float
    sliding_utilization: float
    overturning_utilization: float
    bearing_utilization: float
    q_max_kPa: float
    all_ok: bool


@dataclass
class MSELayerCheck:
    z_m: float
    T_max_kN_per_m: float
    T_design_kN_per_m: float
    tensile_utilization: float
    pullout_length_required_m: float
    pullout_length_available_m: float
    pullout_utilization: float
    ok: bool


@dataclass
class MSEWallResult:
    external: MSEExternalCheck
    internal: List[MSELayerCheck]

    @property
    def all_ok(self) -> bool:
        return self.external.all_ok and all(l.ok for l in self.internal)


class MSEWallDesigner:
    """External + internal stability check for an MSE wall."""

    def __init__(
        self, geometry: MSEWallGeometry, loading: MSELoading,
        design_approach: DesignApproach = DesignApproach.DA2,
    ):
        self.geo = geometry
        self.load = loading
        self.da = design_approach

    def _external(self) -> MSEExternalCheck:
        pf = get_partial_factors(self.da, LimitState.GEO)
        gG_unfav = pf.actions.gamma_G_unfav
        gG_fav = pf.actions.gamma_G_fav

        H = self.geo.H
        B = self.geo.B_reinforced
        gamma = self.load.gamma_fill_kN_m3

        W_k = B * H * gamma                        # block weight per m run
        x_W = B / 2.0                              # centroid at midspan
        W_d_fav = gG_fav * W_k

        # Active thrust from the soil behind the reinforced block (no δ),
        # with the design friction angle of set M (tan φ_d = tan φ_k/γ_φ).
        # DEFECTO CORREGIDO (1.1.0): usaba φ_k en todos los enfoques y
        # mayoraba la sobrecarga (acción variable) con γ_G en vez de γ_Q.
        gQ = pf.actions.gamma_Q_unfav
        phi_fill_d_deg = math.degrees(math.atan(
            math.tan(math.radians(self.load.phi_fill_deg)) / pf.soil.gamma_phi))
        Ka = Ka_rankine(phi_fill_d_deg)
        P_soil_k = 0.5 * Ka * gamma * H ** 2
        P_surch_k = Ka * self.load.surcharge_q * H
        P_h_k = P_soil_k + P_surch_k
        P_h_d = gG_unfav * P_soil_k + gQ * P_surch_k
        z_arm = (
            gG_unfav * P_soil_k * (H / 3.0) + gQ * P_surch_k * (H / 2.0)
        ) / max(P_h_d, 1e-9)

        # Resultant on the base
        M_stb = W_d_fav * x_W
        M_dst = P_h_d * z_arm
        V_d = W_d_fav
        x_R = (M_stb - M_dst) / V_d if V_d > 0 else 0.0
        e_x = B / 2.0 - x_R
        # Bearing pressure (assume middle third)
        if abs(e_x) <= B / 6.0:
            q_max = V_d / B * (1.0 + 6.0 * abs(e_x) / B)
        else:
            a_p = max(3.0 * (B / 2.0 - abs(e_x)), 1e-6)
            q_max = 2.0 * V_d / a_p

        # Simple bearing capacity of foundation (drained, ϕ_g only)
        phi_g = math.radians(self.load.phi_foundation_deg)
        Nq = math.exp(math.pi * math.tan(phi_g)) * math.tan(math.pi / 4 + phi_g / 2) ** 2
        Ng = 2.0 * (Nq - 1.0) * math.tan(phi_g)
        B_eff = B - 2.0 * abs(e_x)
        q_ult = 0.5 * self.load.gamma_foundation_kN_m3 * B_eff * Ng
        q_Rd = q_ult / pf.resistance.gamma_Rv

        # Sliding — AASHTO/FHWA interface friction for MSE:
        # δ_interface = min(2/3 · φ_foundation_d, φ_fill_d)
        phi_g_d = math.atan(math.tan(phi_g) / pf.soil.gamma_phi)
        phi_fill_d_rad = math.atan(math.tan(math.radians(self.load.phi_fill_deg))
                                  / pf.soil.gamma_phi)
        delta_interface = min(2.0 / 3.0 * phi_g_d, phi_fill_d_rad)
        R_h = W_d_fav * math.tan(delta_interface)
        sliding_util = P_h_d / max(R_h / pf.resistance.gamma_Rh, 1e-6)
        overturning_util = M_dst / max(M_stb, 1e-6)
        bearing_util = q_max / max(q_Rd, 1e-6)

        return MSEExternalCheck(
            W_kN_per_m=W_k,
            P_a_h_kN_per_m=P_h_k,
            e_x_m=e_x,
            sliding_utilization=sliding_util,
            overturning_utilization=overturning_util,
            bearing_utilization=bearing_util,
            q_max_kPa=q_max,
            all_ok=(sliding_util <= 1.0 and overturning_util <= 1.0
                    and bearing_util <= 1.0),
        )

    def _internal(self) -> List[MSELayerCheck]:
        Ka = Ka_rankine(self.load.phi_fill_deg)
        phi_a = math.radians(45.0 + self.load.phi_fill_deg / 2.0)
        H = self.geo.H
        gamma = self.load.gamma_fill_kN_m3
        q = self.load.surcharge_q
        checks: List[MSELayerCheck] = []
        for layer in self.geo.layers:
            z = layer.z_below_top_m
            sigma_h = Ka * (gamma * z + q)        # kPa
            T_max = sigma_h * layer.spacing_vertical_m  # kN/m of wall length
            T_design = _T_ALLOW_kN_per_m[layer.reinforcement_type]
            tensile_util = T_max / max(T_design, 1e-9)

            # Pull-out resistance: layer extends to length_m from the wall face.
            # Active wedge crosses the layer at depth z at distance:
            # L_active = (H − z) / tan(45 + φ/2)
            L_active = (H - z) / math.tan(phi_a)
            L_anchor = max(layer.length_m - L_active, 0.0)
            F_star = _FRICTION_F_STAR[layer.reinforcement_type]
            # Pull-out (per metre of width, two-sided friction):
            sigma_v = gamma * z + q
            P_pullout = 2.0 * L_anchor * F_star * sigma_v   # kN/m
            # Required length in the anchor zone:
            L_req = T_max / max(2.0 * F_star * sigma_v, 1e-9)
            pullout_util = T_max / max(P_pullout, 1e-9)

            checks.append(MSELayerCheck(
                z_m=z, T_max_kN_per_m=T_max,
                T_design_kN_per_m=T_design,
                tensile_utilization=tensile_util,
                pullout_length_required_m=L_active + L_req,
                pullout_length_available_m=layer.length_m,
                pullout_utilization=pullout_util,
                ok=(tensile_util <= 1.0 and pullout_util <= 1.0),
            ))
        return checks

    def check(self) -> MSEWallResult:
        return MSEWallResult(
            external=self._external(),
            internal=self._internal(),
        )


__all__ = [
    "MSEReinforcementType",
    "MSELayer",
    "MSEWallGeometry",
    "MSELoading",
    "MSEExternalCheck",
    "MSELayerCheck",
    "MSEWallResult",
    "MSEWallDesigner",
]
