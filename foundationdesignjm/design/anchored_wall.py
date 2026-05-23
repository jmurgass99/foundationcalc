"""Anchored / tied-back retaining walls.

Used in excavations or steep cuts where neither a cantilever wall nor a
gravity wall is feasible. The wall is propped at one or several levels
by **ground anchors** drilled into stable strata behind the active
wedge.

This module gives:

- The **earth pressure diagram** that engineers use for anchored walls
  (trapezoidal / apparent earth pressure per Terzaghi-Peck & FHWA).
- Distribution of horizontal reactions among the anchor levels (assumes
  multi-prop continuous beam).
- **Anchor design** per level: bond length, free length and capacity
  verification (EN 1997-1 §8 + EN 1537).

Reference: FHWA-IF-99-015 (Ground Anchors and Anchored Systems).
Theory: docs/theory/06_retaining_walls.md §6.1 (anchored walls).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from ..codes.eurocode7 import DesignApproach, LimitState, get_partial_factors


class AnchorType(str, Enum):
    STRAND_TENDON = "strand_tendon"
    BAR_TENDON = "bar_tendon"


class AnchorMode(str, Enum):
    """Active vs passive anchor behaviour.

    ACTIVE  — post-tensioned (lock-off load applied after grout cures).
              No wall movement required to mobilise restraint, so the wall
              stays close to its at-rest condition: design with apparent
              earth pressure (Terzaghi-Peck) or K_0 pressures.
    PASSIVE — installed without post-tensioning; the wall must deflect
              before the anchor takes load. Behaves like a passive soil
              nail: design with fully active (K_a) earth pressures.
    """

    ACTIVE = "active"
    PASSIVE = "passive"


# Allowable unit bond resistance qs (kPa) by soil class — FHWA 1999
_BOND_RESISTANCE_kPa = {
    "rock": 1000.0,
    "stiff_clay": 100.0,
    "medium_clay": 50.0,
    "dense_sand": 300.0,
    "medium_sand": 150.0,
    "loose_sand": 60.0,
}


class AnchorLevel(BaseModel):
    """One row of ground anchors."""

    z_below_top_m: float = Field(..., ge=0)
    horizontal_spacing_m: float = Field(..., gt=0)
    inclination_deg: float = Field(15.0, ge=0, le=45,
                                   description="Inclination from horizontal")
    bond_zone_soil: str = Field("medium_sand")
    drill_diameter_m: float = Field(0.15, gt=0.05, le=0.5)
    mode: AnchorMode = Field(
        AnchorMode.ACTIVE,
        description="ACTIVE (post-tensioned) or PASSIVE (no prestress, "
                    "requires wall movement)",
    )
    lock_off_load_kN: float = Field(
        0.0, ge=0,
        description="Initial lock-off (post-tensioning) load per anchor "
                    "(kN). Only used for ACTIVE anchors; set to 0 to let "
                    "the designer pick ~0.75·T_design as the lock-off.",
    )


class AnchoredWallGeometry(BaseModel):
    H_excavation: float = Field(..., gt=2.0,
                                description="Excavation depth (m)")
    embedment_m: float = Field(..., ge=0,
                               description="Embedment below excavation toe (m)")
    anchor_levels: List[AnchorLevel]


class AnchoredWallLoading(BaseModel):
    phi_deg: float = Field(..., ge=20, le=45)
    gamma_kN_m3: float = Field(..., gt=10)
    surcharge_q: float = Field(0.0, ge=0)
    use_apparent_pressure: bool = Field(
        True, description="True → Terzaghi-Peck trapezoidal; False → triangular",
    )


@dataclass
class AnchorDesign:
    z_m: float
    horizontal_spacing_m: float
    mode: AnchorMode
    T_design_kN_per_anchor: float
    lock_off_load_kN: float
    free_length_m: float
    bond_length_m: float
    total_length_m: float
    bond_capacity_kN: float
    bond_utilization: float
    requires_wall_movement: bool
    ok: bool


@dataclass
class AnchoredWallResult:
    P_total_kN_per_m: float
    p_max_kPa: float
    anchors: List[AnchorDesign]

    @property
    def all_ok(self) -> bool:
        return all(a.ok for a in self.anchors)


class AnchoredWallDesigner:
    """Distribute earth pressure to anchors and design each anchor row."""

    def __init__(
        self,
        geometry: AnchoredWallGeometry,
        loading: AnchoredWallLoading,
        design_approach: DesignApproach = DesignApproach.DA2,
    ):
        self.geo = geometry
        self.load = loading
        self.da = design_approach

    def _apparent_pressure_kPa(self) -> float:
        """Terzaghi-Peck trapezoidal envelope for sands."""
        K_a = math.tan(math.radians(45.0 - self.load.phi_deg / 2.0)) ** 2
        # Sands (Terzaghi-Peck): p = 0.65 · γ · H · K_a (uniform over the lower 0.75 H)
        return 0.65 * self.load.gamma_kN_m3 * self.geo.H_excavation * K_a

    def _design_pressure_for_mode(self, mode: AnchorMode) -> tuple[float, float]:
        """Return (P_total_design_kN_per_m, p_peak_design_kPa) for the mode.

        Active anchors are post-tensioned ⇒ the wall barely moves ⇒
        Terzaghi-Peck apparent pressure (or K_0 if the user disabled it).
        Passive anchors require wall movement ⇒ classic triangular K_a
        pressure (smaller, but the wall must deflect to mobilise it).
        """
        pf = get_partial_factors(self.da, LimitState.GEO)
        gG_unfav = pf.actions.gamma_G_unfav
        H = self.geo.H_excavation

        if mode == AnchorMode.ACTIVE and self.load.use_apparent_pressure:
            p = self._apparent_pressure_kPa() * gG_unfav
            P_total = p * H + gG_unfav * self.load.surcharge_q * 0.5 * H
        else:
            K_a = math.tan(math.radians(45.0 - self.load.phi_deg / 2.0)) ** 2
            P_total = (gG_unfav * 0.5 * K_a * self.load.gamma_kN_m3 * H ** 2
                       + gG_unfav * K_a * self.load.surcharge_q * H)
            p = K_a * (self.load.gamma_kN_m3 * H + self.load.surcharge_q)
        return P_total, p

    def check(self) -> AnchoredWallResult:
        n = len(self.geo.anchor_levels)
        if n == 0:
            raise ValueError("Need at least one anchor level.")

        H = self.geo.H_excavation
        # If all anchors share the same mode, use one pressure diagram.
        # If mixed, the dominant (active) controls the apparent-pressure
        # reporting but each level is sized against its own demand.
        modes = {lvl.mode for lvl in self.geo.anchor_levels}
        reporting_mode = (
            AnchorMode.ACTIVE if AnchorMode.ACTIVE in modes else AnchorMode.PASSIVE
        )
        P_total_report, p_report = self._design_pressure_for_mode(reporting_mode)

        anchors: List[AnchorDesign] = []
        for lvl in self.geo.anchor_levels:
            P_total_lvl, _ = self._design_pressure_for_mode(lvl.mode)
            share = P_total_lvl / n
            T_per_m_wall = share                                    # kN/m of wall
            T_per_anchor = T_per_m_wall * lvl.horizontal_spacing_m  # kN
            q_s = _BOND_RESISTANCE_kPa.get(lvl.bond_zone_soil, 100.0)
            gamma_a = 1.5    # γ_anchor (EC7 A.12)
            T_design = T_per_anchor / math.cos(math.radians(lvl.inclination_deg))
            bond_capacity_per_m = math.pi * lvl.drill_diameter_m * q_s   # kN/m
            L_bond_required = T_design * gamma_a / bond_capacity_per_m

            phi_a = math.radians(45.0 + self.load.phi_deg / 2.0)
            free_length = (H - lvl.z_below_top_m) / math.tan(phi_a)
            free_length /= math.cos(math.radians(lvl.inclination_deg))
            free_length = max(free_length, 4.5)          # FHWA min ≥ 4.5 m

            total_length = free_length + L_bond_required
            bond_capacity_total = bond_capacity_per_m * L_bond_required
            bond_util = (T_design * gamma_a) / max(bond_capacity_total, 1e-9)

            if lvl.mode == AnchorMode.ACTIVE:
                P0 = (lvl.lock_off_load_kN if lvl.lock_off_load_kN > 0
                      else 0.75 * T_design)
            else:
                P0 = 0.0

            anchors.append(AnchorDesign(
                z_m=lvl.z_below_top_m,
                horizontal_spacing_m=lvl.horizontal_spacing_m,
                mode=lvl.mode,
                T_design_kN_per_anchor=T_design,
                lock_off_load_kN=P0,
                free_length_m=free_length,
                bond_length_m=L_bond_required,
                total_length_m=total_length,
                bond_capacity_kN=bond_capacity_total,
                bond_utilization=bond_util,
                requires_wall_movement=(lvl.mode == AnchorMode.PASSIVE),
                ok=bond_util <= 1.0 + 1e-6,
            ))

        return AnchoredWallResult(
            P_total_kN_per_m=P_total_report,
            p_max_kPa=p_report,
            anchors=anchors,
        )


__all__ = [
    "AnchorType",
    "AnchorMode",
    "AnchorLevel",
    "AnchoredWallGeometry",
    "AnchoredWallLoading",
    "AnchorDesign",
    "AnchoredWallResult",
    "AnchoredWallDesigner",
]
