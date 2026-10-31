"""Strengthening of existing foundations.

The module provides the most common verifications needed when a
foundation has to be reinforced or underpinned:

1. `angular_distortion_check` — compare the observed differential
   settlements between two points to the CTE-DB-SE-C / EC7 limits.
2. `enlarged_footing_pressure` — new bearing pressure when a footing is
   ring-jacketed (RC enlargement).
3. `mass_concrete_underpinning` — pit-by-pit underpinning: verify the
   pressure on the deepened plane and the staging.
4. `micropile_capacity` — design ULS capacity of a single micropile
   (skin friction + tip) using Bustamante-Doix style correlations.
5. `micropile_group_capacity` — design capacity of a group of
   micropiles installed through an existing footing, with EC7 R4 partial
   factors and pile-group efficiency.

Theory: docs/theory/08_strengthening.md.
"""

from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Damage / distortion limits
# ---------------------------------------------------------------------------

class StructureType(str, Enum):
    """CTE-DB-SE-C Table 2.2 structure categories for distortion limits."""

    ISOSTATIC = "isostatic"                   # 1/300
    RETAINING_WALL = "retaining_wall"         # 1/300
    FRAME_WITH_PARTITIONS = "frame_partitions"  # 1/500
    PRECAST_PANELS = "precast_panels"         # 1/700
    UNREINFORCED_MASONRY_SAGGING = "masonry_sagging"  # 1/1000
    UNREINFORCED_MASONRY_HOGGING = "masonry_hogging"  # 1/2000


_BETA_LIMITS = {
    StructureType.ISOSTATIC: 1.0 / 300.0,
    StructureType.RETAINING_WALL: 1.0 / 300.0,
    StructureType.FRAME_WITH_PARTITIONS: 1.0 / 500.0,
    StructureType.PRECAST_PANELS: 1.0 / 700.0,
    StructureType.UNREINFORCED_MASONRY_SAGGING: 1.0 / 1000.0,
    StructureType.UNREINFORCED_MASONRY_HOGGING: 1.0 / 2000.0,
}


class AngularDistortionResult(BaseModel):
    beta: float = Field(description="Computed angular distortion δs / L")
    beta_limit: float = Field(description="Code limit for the structure type")
    structure_type: StructureType
    utilization: float
    ok: bool


def angular_distortion_check(
    delta_s_AB_mm: float,
    L_AB_m: float,
    structure_type: StructureType,
) -> AngularDistortionResult:
    """Check `β_AB = δs_AB / L_AB ≤ β_limit` (CTE-DB-SE-C Table 2.2).

    Args:
        delta_s_AB_mm: differential settlement between A and B [mm].
        L_AB_m: horizontal distance between A and B [m].
        structure_type: structure category.
    """
    if L_AB_m <= 0:
        raise ValueError("L_AB must be > 0")
    beta = abs(delta_s_AB_mm) / 1000.0 / L_AB_m
    limit = _BETA_LIMITS[structure_type]
    return AngularDistortionResult(
        beta=beta,
        beta_limit=limit,
        structure_type=structure_type,
        utilization=beta / limit,
        ok=beta <= limit,
    )


# ---------------------------------------------------------------------------
# Footing enlargement
# ---------------------------------------------------------------------------

class EnlargedFootingResult(BaseModel):
    A_old: float
    A_new: float
    q_old: float = Field(description="Original bearing pressure [kPa]")
    q_new: float = Field(description="Bearing pressure after enlargement [kPa]")
    reduction_pct: float = Field(description="Pressure reduction [%]")
    interface_shear_required: float = Field(description="Required interface shear capacity [kPa]")


def enlarged_footing_pressure(
    N_kN: float,
    A_old_m2: float,
    new_width_m: float,
    new_length_m: float,
) -> EnlargedFootingResult:
    """Bearing-pressure reduction when an existing footing is ring-jacketed.

    Assumes the load is uniformly redistributed onto the enlarged base.
    Returns the new pressure plus the interface shear that the old/new
    concrete connection must resist (load fraction × q_new).
    """
    if A_old_m2 <= 0 or new_width_m * new_length_m < A_old_m2:
        raise ValueError("A_old must be > 0 and A_new must be > A_old.")
    A_new = new_width_m * new_length_m
    q_old = N_kN / A_old_m2
    q_new = N_kN / A_new
    # Interface shear estimate: fraction of N transferred to the new ring
    # times q_new (acting as a vertical traction across the interface).
    frac_new = (A_new - A_old_m2) / A_new
    interface_shear = frac_new * q_new
    return EnlargedFootingResult(
        A_old=A_old_m2,
        A_new=A_new,
        q_old=q_old,
        q_new=q_new,
        reduction_pct=(q_old - q_new) / q_old * 100.0,
        interface_shear_required=interface_shear,
    )


# ---------------------------------------------------------------------------
# Mass-concrete underpinning (pit method)
# ---------------------------------------------------------------------------

class UnderpinningPit(BaseModel):
    width: float = Field(..., gt=0, le=1.5, description="Pit width along the wall (≤ 1.5 m), m")
    depth_below_old: float = Field(..., gt=0, description="Vertical extension below old founding plane, m")
    along_wall_length: float = Field(..., gt=0, description="Pit length along the wall, m")


class MassUnderpinningResult(BaseModel):
    N_per_pit: float = Field(description="Tributary load on one pit [kN]")
    q_deepened: float = Field(description="Bearing pressure on the deepened plane [kPa]")
    q_allow: float = Field(description="Allowable bearing pressure [kPa]")
    utilization: float
    n_pits: int
    stage_pattern: str
    ok: bool


def mass_concrete_underpinning(
    wall_load_kN_per_m: float,
    wall_length_m: float,
    pit: UnderpinningPit,
    q_allow_kPa: float,
    stages: int = 3,
) -> MassUnderpinningResult:
    """Verify the bearing pressure under each mass-concrete pit.

    Stages alternate so that no two adjacent pits are excavated at the
    same time (typically a 1/3 - 2/3 - 1/3 panel sequence with `stages`
    rotations).
    """
    if wall_load_kN_per_m <= 0 or wall_length_m <= 0:
        raise ValueError("Load and length must be > 0.")
    n_pits = max(int(math.ceil(wall_length_m / pit.along_wall_length)), 1)
    N_per_pit = wall_load_kN_per_m * pit.along_wall_length
    A_pit = pit.width * pit.along_wall_length
    q_deepened = N_per_pit / A_pit
    util = q_deepened / q_allow_kPa
    pattern = " -> ".join(
        ", ".join(str(i + j) for j in range(0, n_pits, stages))
        for i in range(stages)
    )
    return MassUnderpinningResult(
        N_per_pit=N_per_pit,
        q_deepened=q_deepened,
        q_allow=q_allow_kPa,
        utilization=util,
        n_pits=n_pits,
        stage_pattern=pattern,
        ok=util <= 1.0,
    )


# ---------------------------------------------------------------------------
# Micropile capacity (Bustamante-Doix style)
# ---------------------------------------------------------------------------

class MicropileSoilType(str, Enum):
    SAND_GRAVEL = "sand_gravel"
    SAND = "sand"
    CLAY = "clay"
    MARL_LIMESTONE = "marl_limestone"
    WEATHERED_ROCK = "weathered_rock"


# Bustamante-Doix unit skin friction values (q_s, in kPa) — type IRS injection.
# Conservative ranges; final values must come from local practice.
_QS_IRS = {
    MicropileSoilType.SAND_GRAVEL: (80.0, 200.0),
    MicropileSoilType.SAND: (60.0, 150.0),
    MicropileSoilType.CLAY: (40.0, 110.0),
    MicropileSoilType.MARL_LIMESTONE: (110.0, 300.0),
    MicropileSoilType.WEATHERED_ROCK: (250.0, 500.0),
}


class MicropileGeometry(BaseModel):
    diameter_drilling: float = Field(..., gt=0.05, le=0.5, description="Drilling diameter d_d, m")
    diameter_grouted: float = Field(..., gt=0.05, le=0.6, description="Effective grouted diameter d_s, m")
    length_total: float = Field(..., gt=1.0, description="Total length, m")
    length_bond: float = Field(..., gt=1.0, description="Bond length in the bearing stratum, m")


class MicropileCapacityResult(BaseModel):
    R_skin_char: float = Field(description="Characteristic skin resistance [kN]")
    R_skin_design: float = Field(description="Design skin resistance [kN]")
    R_total_design: float = Field(description="Total design resistance R_d [kN]")
    q_s_used: float = Field(description="Unit skin friction used [kPa]")


def micropile_capacity(
    geometry: MicropileGeometry,
    soil_type: MicropileSoilType,
    q_s_kPa: float = None,
    correlation_factor_xi: float = 1.30,
    gamma_R_total: float = 1.50,
    alpha_inj: float = 1.20,
) -> MicropileCapacityResult:
    """Design ULS capacity of one micropile per Bustamante-Doix.

    Args:
        geometry: micropile dimensions.
        soil_type: bearing stratum class.
        q_s_kPa: explicit unit skin friction; if None, use the lower bound
                 of the Bustamante-Doix tables.
        correlation_factor_xi: ξ on shaft (EC7 Table A.9 / A.10).
        gamma_R_total: γ_t on total resistance (EC7 Table A.7, R4).
        alpha_inj: pressure-injection factor on the drilled diameter
                   (1.2–1.8 depending on the injection type IRS / IGU).
    """
    if q_s_kPa is None:
        q_s_kPa = _QS_IRS[soil_type][0]  # conservative lower bound
    # Effective shaft area = π · d_s · L_bond
    d_eff = max(geometry.diameter_grouted, alpha_inj * geometry.diameter_drilling)
    perimeter = math.pi * d_eff
    R_skin_char = perimeter * geometry.length_bond * q_s_kPa  # kN
    R_skin_design = R_skin_char / (correlation_factor_xi * gamma_R_total)
    # Conservative: ignore tip resistance for slender micropiles
    return MicropileCapacityResult(
        R_skin_char=R_skin_char,
        R_skin_design=R_skin_design,
        R_total_design=R_skin_design,
        q_s_used=q_s_kPa,
    )


# ---------------------------------------------------------------------------
# Micropile group through an existing footing
# ---------------------------------------------------------------------------

class MicropileGroupResult(BaseModel):
    n_piles: int
    R_per_pile: float
    R_group_design: float
    efficiency_E: float
    utilization: float
    ok: bool


def micropile_group_capacity(
    n_piles: int,
    R_per_pile_design_kN: float,
    spacing_to_diameter: float,
    N_design_kN: float,
) -> MicropileGroupResult:
    """Design capacity of a group of micropiles in compression.

    Group efficiency `E` follows Converse-Labarre when the spacing is
    less than 3 d. For s/d ≥ 3 the group is assumed fully efficient.
    """
    if n_piles < 2:
        raise ValueError("Group must have at least 2 piles.")
    if spacing_to_diameter >= 3.0:
        E = 1.0
    else:
        # Converse-Labarre simplified to E = (s/d) / 3, clamped
        E = max(0.5, spacing_to_diameter / 3.0)
    R_group = E * n_piles * R_per_pile_design_kN
    util = N_design_kN / max(R_group, 1e-6)
    return MicropileGroupResult(
        n_piles=n_piles,
        R_per_pile=R_per_pile_design_kN,
        R_group_design=R_group,
        efficiency_E=E,
        utilization=util,
        ok=util <= 1.0,
    )


__all__ = [
    "StructureType",
    "AngularDistortionResult",
    "angular_distortion_check",
    "EnlargedFootingResult",
    "enlarged_footing_pressure",
    "UnderpinningPit",
    "MassUnderpinningResult",
    "mass_concrete_underpinning",
    "MicropileSoilType",
    "MicropileGeometry",
    "MicropileCapacityResult",
    "micropile_capacity",
    "MicropileGroupResult",
    "micropile_group_capacity",
]
