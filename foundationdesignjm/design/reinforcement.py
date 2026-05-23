"""Flexural reinforcement and strut-and-tie design for footings.

Theory: docs/theory/03_shallow_foundations.md §3.4 + 05_pile_foundations.md §5.6.
"""

from __future__ import annotations

import math
from typing import Dict

from pydantic import BaseModel, Field

from ..core.material import Concrete, ReinforcingSteel


class ReinforcementResult(BaseModel):
    As_required: float = Field(..., description="Required area (mm²)")
    As_min: float = Field(..., description="Minimum area per EC2 (mm²)")
    As_provided: float = Field(..., description="Actually required = max(req, min) (mm²)")
    method: str
    note: str = ""


def strut_and_tie_rigid_footing(
    N_d_kN: float,
    a_mm: float,
    v_mm: float,
    d_mm: float,
    steel: ReinforcingSteel,
) -> ReinforcementResult:
    """Rigid footing under axial + small moment (strut-and-tie, EHE 58.4.1).

        T_d = N_d · (v + 0.25·a) / (0.85·d)
    """
    if d_mm <= 0:
        raise ValueError("Effective depth must be positive.")
    T_d = N_d_kN * 1000.0 * (v_mm + 0.25 * a_mm) / (0.85 * d_mm)  # N
    fyd = steel.fyd_strut_and_tie  # N/mm²
    As = T_d / fyd  # mm²
    return ReinforcementResult(
        As_required=As,
        As_min=0.0,
        As_provided=As,
        method="strut_and_tie_2D",
        note="Limit f_yd ≤ 400 N/mm² applied per EHE/EC2 STM rule.",
    )


def flexural_reinforcement(
    M_Ed_kNm: float,
    b_mm: float,
    d_mm: float,
    concrete: Concrete,
    steel: ReinforcingSteel,
) -> ReinforcementResult:
    """Bending design of a singly-reinforced rectangular section (EC2).

    Uses the lever-arm equation z = d/2 · (1 + √(1 − 3.53·K)) with z ≤ 0.95·d,
    capped at K' = 0.167 (singly reinforced limit).

    Minimum reinforcement (EC2 §9.2.1.1):
        As_min = max(0.26 · (f_ctm / f_yk) · b · d, 0.0013 · b · d)
    """
    if d_mm <= 0 or b_mm <= 0:
        raise ValueError("b and d must be positive.")
    M_Nmm = M_Ed_kNm * 1e6
    fck = concrete.fck
    fctm = concrete.fctm
    fyk = steel.fyk
    fyd = steel.fyd

    K = M_Nmm / (b_mm * d_mm ** 2 * fck)
    K_lim = 0.167
    note = ""
    if K > K_lim:
        z = 0.82 * d_mm
        note = "K > 0.167 — section under-reinforced; compression reinforcement required (approximation used)."
    else:
        z = d_mm * 0.5 * (1.0 + math.sqrt(max(0.0, 1.0 - 3.53 * K)))
        z = min(z, 0.95 * d_mm)

    As_req = M_Nmm / (fyd * z)
    As_min = max(0.26 * (fctm / fyk) * b_mm * d_mm, 0.0013 * b_mm * d_mm)

    return ReinforcementResult(
        As_required=As_req,
        As_min=As_min,
        As_provided=max(As_req, As_min),
        method="ec2_singly_reinforced",
        note=note,
    )


def critical_section_offset(a_mm: float, masonry_wall: bool = False) -> float:
    """Offset of the critical bending section inside the column (EHE 58.4.2):

        s1 at 0.15·a (concrete column)
        s1 at 0.25·a (masonry wall)
    """
    return 0.25 * a_mm if masonry_wall else 0.15 * a_mm


def reinforcement_distribution_rectangular_footing(
    As_total: float,
    a_prime_m: float,
    b_prime_m: float,
    h_m: float,
    a_m: float,
) -> Dict[str, float]:
    """Reinforcement distribution in a flexible rectangular footing (EHE 58.4.2):

    - Long side a': uniformly across width b'.
    - Short side b': the central strip of width b_strip ≤ a + 2h takes
      2·b'/(a'+b') of A_s; the rest goes in the lateral strips.
    """
    if a_prime_m + b_prime_m == 0:
        raise ValueError("Footing dimensions must be positive.")
    b_strip = min(b_prime_m, a_m + 2.0 * h_m)
    fraction_central = 2.0 * b_prime_m / (a_prime_m + b_prime_m)
    As_central = As_total * fraction_central
    As_lateral = As_total - As_central
    return {
        "b_strip_m": b_strip,
        "fraction_central": fraction_central,
        "As_central": As_central,
        "As_lateral": As_lateral,
    }
