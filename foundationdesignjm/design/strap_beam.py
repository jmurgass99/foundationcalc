"""Strap (tie) beam design for shallow foundations and pile foundations.

Theory: docs/theory/03_shallow_foundations.md §3.7 + 07_seismic.md §7.4.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class StrapBeamSpec(BaseModel):
    """Geometric and design output for a strap (tie) beam."""

    width_mm: float = Field(..., description="b (mm) ≥ 300")
    depth_mm: float = Field(..., description="h (mm) ≥ L/12 ≥ 350")
    length_mm: float
    design_axial_kN: float
    design_shear_kN: float
    design_moment_kNm: float
    note: str = ""


class GroundType(str, Enum):
    """EC8 ground type, for tie-beam seismic actions."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


def strap_for_two_footings(
    N1_kN: float,
    N2_kN: float,
    length_mm: float,
    eccentricity_mm: float = 0.0,
    seismic_factor: float = 0.03,
    q_self_kNm: float = 10.0,
) -> StrapBeamSpec:
    """Strap beam linking two footings.

    Design forces:
        T = seismic_factor · (N1 + N2)          (default 0.03 for non-seismic Spain)
        M1d = ±(M_column + N_column · e)
        M2d = ±q·L²/12 (self weight)
    """
    T = seismic_factor * (N1_kN + N2_kN)
    L = length_mm / 1000.0
    M2 = q_self_kNm * L ** 2 / 12.0
    M1 = max(N1_kN, N2_kN) * (eccentricity_mm / 1000.0)
    M_total = M1 + M2
    V_total = M_total / L if L > 0 else 0.0

    width = max(300.0, 0.0)
    depth = max(length_mm / 12.0, 350.0)

    return StrapBeamSpec(
        width_mm=width,
        depth_mm=depth,
        length_mm=length_mm,
        design_axial_kN=T,
        design_shear_kN=V_total,
        design_moment_kNm=M_total,
        note="Seismic factor 0.03 for non-seismic. Use (a_c/g) in seismic zones.",
    )


def seismic_tie_force(N_Ed_kN: float, alpha_S: float, ground_type: GroundType) -> float:
    """EC8 §5.4.1.2 tie-beam axial-design force:

        ±0.3·α·S·N_Ed for ground B,
        ±0.4·α·S·N_Ed for ground C,
        ±0.6·α·S·N_Ed for ground D.
    """
    factor = {
        GroundType.A: 0.0,
        GroundType.B: 0.3,
        GroundType.C: 0.4,
        GroundType.D: 0.6,
        GroundType.E: 0.6,
    }[ground_type]
    return factor * alpha_S * N_Ed_kN


def tie_beam_minimum_dimensions(n_storeys_above_basement: int) -> tuple[float, float]:
    """EC8: width ≥ 250 mm; depth ≥ 400 mm (≤ 3 storeys) or 500 mm (4+ storeys)."""
    width = 250.0
    depth = 500.0 if n_storeys_above_basement >= 4 else 400.0
    return width, depth
