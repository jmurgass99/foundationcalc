"""Strut-and-tie design of pile caps (rigid caps with 2, 3, 4+ piles).

Theory: docs/theory/05_pile_foundations.md §5.6.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from pydantic import BaseModel, Field

from ..core.material import ReinforcingSteel


class PileCapTieResult(BaseModel):
    T_d: float = Field(..., description="Design tie force (N)")
    A_s: float = Field(..., description="Required steel area (mm²)")
    secondary_min: float = Field(..., description="Minimum secondary reinforcement (mm²)")
    note: str = ""


def cap_two_piles(
    N_d_kN: float,
    v_mm: float,
    a_mm: float,
    d_mm: float,
    steel: ReinforcingSteel,
) -> PileCapTieResult:
    """Cap on 2 piles — main tie:

        T_d = N_d · (v + 0.25·a) / (0.85·d)
    """
    if d_mm <= 0:
        raise ValueError("Effective depth must be positive.")
    T_d_N = N_d_kN * 1000.0 * (v_mm + 0.25 * a_mm) / (0.85 * d_mm)
    A_s = T_d_N / steel.fyd_strut_and_tie
    return PileCapTieResult(
        T_d=T_d_N,
        A_s=A_s,
        secondary_min=A_s / 10.0,
        note="Cap on 2 piles, strut-and-tie. Secondary ≥ T_d/10, min 4 ‰ in each direction.",
    )


def cap_three_piles(
    N_d_kN: float,
    l_mm: float,
    a_mm: float,
    d_mm: float,
    steel: ReinforcingSteel,
) -> PileCapTieResult:
    """Cap on 3 piles (equilateral, side l, column dim a):

        T_d = 0.68 · (N_d / d) · (0.58·l − 0.25·a)
    """
    if d_mm <= 0:
        raise ValueError("Effective depth must be positive.")
    T_d_N = 0.68 * (N_d_kN * 1000.0 / d_mm) * (0.58 * l_mm - 0.25 * a_mm)
    A_s = T_d_N / steel.fyd_strut_and_tie
    return PileCapTieResult(
        T_d=T_d_N,
        A_s=A_s,
        secondary_min=A_s / 4.0,
        note="Cap on 3 piles, STM. Reinforcement in three strips connecting pile axes (60°).",
    )


def cap_four_piles(
    N_d_kN: float,
    l1_mm: float,
    l2_mm: float,
    a1_mm: float,
    a2_mm: float,
    d_mm: float,
    steel: ReinforcingSteel,
) -> Tuple[PileCapTieResult, PileCapTieResult]:
    """Cap on 4 piles (rectangular, sides l1 × l2, column a1 × a2):

        T_1d = (N_d / (0.85·d)) · (0.50·l1 − 0.25·a1)
        T_2d = (N_d / (0.85·d)) · (0.50·l2 − 0.25·a2)
    """
    if d_mm <= 0:
        raise ValueError("Effective depth must be positive.")
    coef = N_d_kN * 1000.0 / (0.85 * d_mm)
    T1_N = coef * (0.50 * l1_mm - 0.25 * a1_mm)
    T2_N = coef * (0.50 * l2_mm - 0.25 * a2_mm)
    fyd = steel.fyd_strut_and_tie
    res1 = PileCapTieResult(
        T_d=T1_N, A_s=T1_N / fyd, secondary_min=(T1_N / fyd) / 4.0,
        note="Cap on 4 piles, direction 1, STM. Bars over piles.",
    )
    res2 = PileCapTieResult(
        T_d=T2_N, A_s=T2_N / fyd, secondary_min=(T2_N / fyd) / 4.0,
        note="Cap on 4 piles, direction 2, STM.",
    )
    return res1, res2


def pile_cap_secondary_vertical(N_d_kN: float, n_piles: int) -> float:
    """Vertical secondary reinforcement (multi-pile rigid caps, n ≥ 3):

        F_min = N_d / (1.5 · n)

    Returns the design force (N) — to be divided by f_yd by the caller.
    """
    if n_piles < 3:
        return 0.0
    return N_d_kN * 1000.0 / (1.5 * n_piles)


def distribute_forces_rigid_cap(
    Fv_kN: float,
    Mx_kNm: float,
    My_kNm: float,
    pile_positions: List[Tuple[float, float]],
) -> List[float]:
    """Force per pile under a rigid cap, vertical piles, equal section.

        F_iv = F_v/n + M_x · y_i / Σy² + M_y · x_i / Σx²

    pile_positions in metres relative to the cap centroid.
    """
    n = len(pile_positions)
    if n == 0:
        return []
    sum_y2 = sum(y ** 2 for _, y in pile_positions)
    sum_x2 = sum(x ** 2 for x, _ in pile_positions)
    forces = []
    for x, y in pile_positions:
        f = Fv_kN / n
        if sum_y2 > 1e-12:
            f += Mx_kNm * y / sum_y2
        if sum_x2 > 1e-12:
            f += My_kNm * x / sum_x2
        forces.append(f)
    return forces
