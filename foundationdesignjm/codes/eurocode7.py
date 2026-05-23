"""Eurocode 7 (EN 1997-1) — partial factors, design approaches and national annexes.

References:
- EN 1997-1:2004 Annex A (informative recommended values).
- UNE-EN 1990 / UNE-EN 1997-1 (Spain National Annex).

See docs/theory/02_eurocode7.md for the underlying tables and theory.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict

from pydantic import BaseModel, ConfigDict


class DesignApproach(str, Enum):
    """Eurocode 7 design approaches.

    DA-1 has two combinations checked separately.
    DA-2 applies partial factors on actions and resistances.
    DA-2* applies partial factors on the *effects* of actions and resistances
    (equivalent to traditional global safety factor: FS = γ_E · γ_R).
    DA-3 applies partial factors on actions and on soil parameters.
    """

    DA1_C1 = "DA1-C1"  # A1 + M1 + R1
    DA1_C2 = "DA1-C2"  # A2 + M2 + R1
    DA2 = "DA2"        # A1 + M1 + R2
    DA2_STAR = "DA2*"  # Effects-based DA2
    DA3 = "DA3"        # (A1 or A2) + M2 + R3


class LimitState(str, Enum):
    """Ultimate Limit States in EN 1997-1 §2.4.7."""

    EQU = "EQU"  # Loss of equilibrium of the structure or ground as a rigid body
    STR = "STR"  # Structural failure
    GEO = "GEO"  # Geotechnical failure
    UPL = "UPL"  # Uplift (buoyancy)
    HYD = "HYD"  # Hydraulic heave
    SLS = "SLS"  # Serviceability


class NationalAnnex(str, Enum):
    """National annexes profile selector."""

    EU_RECOMMENDED = "EU"
    SPAIN = "SPAIN"
    UK = "UK"
    GERMANY = "GERMANY"
    FRANCE = "FRANCE"
    ITALY = "ITALY"
    PORTUGAL = "PORTUGAL"


class PartialFactorSet(BaseModel):
    """Single set of partial factors (A1/A2/M1/M2/R1/R2/R3/R4)."""

    # Actions (set A)
    gamma_G_unfav: float = 1.0
    gamma_G_fav: float = 1.0
    gamma_Q_unfav: float = 0.0
    gamma_Q_fav: float = 0.0

    # Soil parameters (set M)
    gamma_phi: float = 1.0  # applied to tan(phi)
    gamma_c: float = 1.0    # effective cohesion
    gamma_cu: float = 1.0   # undrained shear strength
    gamma_qu: float = 1.0   # unconfined compressive strength
    gamma_gamma: float = 1.0  # weight density

    # Resistance factors (set R) for spread foundations
    gamma_Rv: float = 1.0  # bearing
    gamma_Rh: float = 1.0  # sliding
    gamma_Re: float = 1.0  # passive earth resistance

    # Pile factors (driven, bored, CFA — base/shaft/total/tension)
    gamma_pile_b_driven: float = 1.0
    gamma_pile_s_driven: float = 1.0
    gamma_pile_t_driven: float = 1.0
    gamma_pile_st_driven: float = 1.0
    gamma_pile_b_bored: float = 1.0
    gamma_pile_s_bored: float = 1.0
    gamma_pile_t_bored: float = 1.0
    gamma_pile_st_bored: float = 1.0

    name: str = ""


# ---------------------------------------------------------------------------
# EN 1997-1 Annex A — recommended (informative) values
# ---------------------------------------------------------------------------

# Set A1 (STR/GEO actions, persistent/transient)
A1 = PartialFactorSet(
    name="A1",
    gamma_G_unfav=1.35,
    gamma_G_fav=1.00,
    gamma_Q_unfav=1.50,
    gamma_Q_fav=0.0,
)
A2 = PartialFactorSet(
    name="A2",
    gamma_G_unfav=1.00,
    gamma_G_fav=1.00,
    gamma_Q_unfav=1.30,
    gamma_Q_fav=0.0,
)

# Sets M1 (no partial factors on soil) and M2 (apply partial factors on soil)
M1 = PartialFactorSet(
    name="M1",
    gamma_phi=1.0,
    gamma_c=1.0,
    gamma_cu=1.0,
    gamma_qu=1.0,
    gamma_gamma=1.0,
)
M2 = PartialFactorSet(
    name="M2",
    gamma_phi=1.25,
    gamma_c=1.25,
    gamma_cu=1.40,
    gamma_qu=1.40,
    gamma_gamma=1.0,
)

# Sets R1/R2/R3 for spread foundations
R1_SPREAD = PartialFactorSet(name="R1_spread", gamma_Rv=1.0, gamma_Rh=1.0, gamma_Re=1.0)
R2_SPREAD = PartialFactorSet(name="R2_spread", gamma_Rv=1.4, gamma_Rh=1.1, gamma_Re=1.4)
R3_SPREAD = PartialFactorSet(name="R3_spread", gamma_Rv=1.0, gamma_Rh=1.0, gamma_Re=1.0)

# EQU set (only for static-equilibrium ULS)
EQU_ACTIONS = PartialFactorSet(
    name="EQU_actions",
    gamma_G_unfav=1.10,
    gamma_G_fav=0.90,
    gamma_Q_unfav=1.50,
    gamma_Q_fav=0.0,
)
EQU_SOIL = PartialFactorSet(
    name="EQU_soil",
    gamma_phi=1.25,
    gamma_c=1.25,
    gamma_cu=1.40,
    gamma_qu=1.40,
    gamma_gamma=1.0,
)


# ---------------------------------------------------------------------------
# Combination factors ψ (EN 1990)
# ---------------------------------------------------------------------------

# Typical defaults — applications may override per action category.
PSI_FACTORS_DEFAULT: Dict[str, Dict[str, float]] = {
    "imposed_residential": {"psi_0": 0.7, "psi_1": 0.5, "psi_2": 0.3},
    "imposed_office": {"psi_0": 0.7, "psi_1": 0.5, "psi_2": 0.3},
    "imposed_storage": {"psi_0": 1.0, "psi_1": 0.9, "psi_2": 0.8},
    "wind": {"psi_0": 0.6, "psi_1": 0.2, "psi_2": 0.0},
    "snow_below_1000m": {"psi_0": 0.5, "psi_1": 0.2, "psi_2": 0.0},
    "snow_above_1000m": {"psi_0": 0.7, "psi_1": 0.5, "psi_2": 0.2},
    "temperature": {"psi_0": 0.6, "psi_1": 0.5, "psi_2": 0.0},
    "default": {"psi_0": 0.7, "psi_1": 0.5, "psi_2": 0.3},
}


class EC7PartialFactors(BaseModel):
    """Container of partial-factor sets selected by Design Approach and Limit State.

    `actions` returns the active A set, `soil` the M set, `resistance` the R set.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    design_approach: DesignApproach
    limit_state: LimitState
    actions: PartialFactorSet
    soil: PartialFactorSet
    resistance: PartialFactorSet
    annex: NationalAnnex = NationalAnnex.EU_RECOMMENDED


# ---------------------------------------------------------------------------
# Country profiles — override default resistance factors per National Annex
# ---------------------------------------------------------------------------

EC7_RECOMMENDED: Dict[str, PartialFactorSet] = {
    "A1": A1,
    "A2": A2,
    "M1": M1,
    "M2": M2,
    "R1": R1_SPREAD,
    "R2": R2_SPREAD,
    "R3": R3_SPREAD,
    "EQU_A": EQU_ACTIONS,
    "EQU_M": EQU_SOIL,
}

# Spain UNE-EN 1997-1 table A.5 — bearing γ_R,v = 2.15 (buildings).
R2_SPAIN_BUILDINGS = PartialFactorSet(
    name="R2_spain_buildings", gamma_Rv=2.15, gamma_Rh=1.10, gamma_Re=1.4,
)
R2_SPAIN_OTHER = PartialFactorSet(
    name="R2_spain_other_structures", gamma_Rv=1.85, gamma_Rh=1.10, gamma_Re=1.4,
)

SPAIN: Dict[str, PartialFactorSet] = {
    **EC7_RECOMMENDED,
    "R2": R2_SPAIN_BUILDINGS,
    "R2_other": R2_SPAIN_OTHER,
}

PROFILES: Dict[NationalAnnex, Dict[str, PartialFactorSet]] = {
    NationalAnnex.EU_RECOMMENDED: EC7_RECOMMENDED,
    NationalAnnex.SPAIN: SPAIN,
}


def get_partial_factors(
    design_approach: DesignApproach,
    limit_state: LimitState = LimitState.GEO,
    annex: NationalAnnex = NationalAnnex.EU_RECOMMENDED,
    structure_type: str = "building",
) -> EC7PartialFactors:
    """Return the active A/M/R sets for the given Design Approach + Limit State.

    Args:
        design_approach: DA-1 (C1 or C2), DA-2, DA-2* or DA-3.
        limit_state: STR, GEO, EQU, UPL, HYD or SLS.
        annex: National annex profile (defaults to EU recommended).
        structure_type: "building" (γ_R,v = 2.15 in Spain) or "other" (1.85).

    Raises:
        ValueError if combination is not supported.
    """
    profile = PROFILES.get(annex, EC7_RECOMMENDED)

    if limit_state == LimitState.EQU:
        return EC7PartialFactors(
            design_approach=design_approach,
            limit_state=limit_state,
            actions=profile["EQU_A"],
            soil=profile["EQU_M"],
            resistance=R1_SPREAD,
            annex=annex,
        )

    if limit_state == LimitState.SLS:
        unity = PartialFactorSet(name="SLS_unity")
        return EC7PartialFactors(
            design_approach=design_approach,
            limit_state=limit_state,
            actions=unity,
            soil=unity,
            resistance=unity,
            annex=annex,
        )

    if annex == NationalAnnex.SPAIN and structure_type == "other":
        r2 = profile["R2_other"]
    else:
        r2 = profile["R2"]

    if design_approach == DesignApproach.DA1_C1:
        return EC7PartialFactors(
            design_approach=design_approach,
            limit_state=limit_state,
            actions=profile["A1"],
            soil=profile["M1"],
            resistance=profile["R1"],
            annex=annex,
        )

    if design_approach == DesignApproach.DA1_C2:
        return EC7PartialFactors(
            design_approach=design_approach,
            limit_state=limit_state,
            actions=profile["A2"],
            soil=profile["M2"],
            resistance=profile["R1"],
            annex=annex,
        )

    if design_approach in (DesignApproach.DA2, DesignApproach.DA2_STAR):
        return EC7PartialFactors(
            design_approach=design_approach,
            limit_state=limit_state,
            actions=profile["A1"],
            soil=profile["M1"],
            resistance=r2,
            annex=annex,
        )

    if design_approach == DesignApproach.DA3:
        return EC7PartialFactors(
            design_approach=design_approach,
            limit_state=limit_state,
            actions=profile["A1"],
            soil=profile["M2"],
            resistance=profile["R3"],
            annex=annex,
        )

    raise ValueError(f"Unsupported design approach: {design_approach}")


def utilization_ratio(demand: float, capacity: float) -> float:
    """Λ = E_d / R_d, expressed as a fraction (0–1+). >1 means unsafe."""
    if capacity <= 0:
        raise ValueError("Capacity must be positive.")
    return demand / capacity
