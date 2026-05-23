"""Pile-group analysis under combined V + H + M.

Distributes a column reaction (V vertical, H horizontal, M moment) onto
a group of piles under a **rigid pile-cap** assumption, and reports the
group capacity envelope considering:

- **Vertical distribution** (Engesser / rigid-cap formula):
        N_i = V/n  + M_x·y_i / I_x  + M_y·x_i / I_y
  where I_x = Σ y_i², I_y = Σ x_i² with the pile positions referred to
  the cap centroid.
- **Horizontal distribution** weighted by lateral stiffness (default
  uniform).
- **Group efficiency** for axial loading via Converse-Labarre (s/d):
        E = 1 - phi*(((n-1)*m + (m-1)*n) / (90 * m * n))
  where m × n is the pile arrangement and phi the arctan(d/s).
- **Group efficiency** for lateral loading (Mokwa & Duncan 2001):
        E_h ≈ 0.5 + 0.5·min(s/d / 6, 1.0)    (leading-row reduction)

The result lists the maximum and minimum N_i (compression / tension),
the per-pile H_i and the worst-pile utilisation when compared against
the user-supplied per-pile capacity envelope.

Theory: docs/theory/16_pile_groups.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Group efficiency
# ---------------------------------------------------------------------------

def converse_labarre_efficiency(
    n_rows: int, n_cols: int, spacing_m: float, diameter_m: float,
) -> float:
    """Converse-Labarre group efficiency for axial loading.

    E = 1 − φ · [(n−1)·m + (m−1)·n] / (90 · m · n)
    where φ = atan(d/s) in degrees, m = n_cols, n = n_rows.

    Returns 1.0 when s/d ≥ 4 (no group effect) and decreases with
    closer spacings.
    """
    if n_rows < 1 or n_cols < 1 or diameter_m <= 0:
        return 1.0
    s_over_d = spacing_m / diameter_m
    if s_over_d >= 4.0:
        return 1.0
    phi_deg = math.degrees(math.atan(diameter_m / spacing_m))
    m, n = n_cols, n_rows
    if m * n == 1:
        return 1.0
    E = 1.0 - phi_deg * ((n - 1) * m + (m - 1) * n) / (90.0 * m * n)
    return max(E, 0.5)


def mokwa_duncan_lateral_efficiency(spacing_m: float, diameter_m: float) -> float:
    """Lateral group efficiency from leading-row reduction (Mokwa & Duncan 2001).

    Approximation:  E_h ≈ 0.5 + 0.5·min(s/d / 6, 1.0).
    """
    if diameter_m <= 0:
        return 1.0
    s_d = spacing_m / diameter_m
    return 0.5 + 0.5 * min(s_d / 6.0, 1.0)


# ---------------------------------------------------------------------------
# Group geometry
# ---------------------------------------------------------------------------

class PileInGroup(BaseModel):
    """One pile in a rigid-cap group, defined by its centroidal (x, y)."""

    x_m: float = Field(..., description="x coordinate referred to cap centroid (m)")
    y_m: float = Field(..., description="y coordinate referred to cap centroid (m)")
    diameter_m: float = Field(..., gt=0.05)
    axial_capacity_kN: float = Field(0.0, ge=0,
        description="Per-pile design axial capacity (compression, kN). 0 = unknown.")
    tension_capacity_kN: float = Field(0.0, ge=0,
        description="Per-pile design uplift capacity (kN).")
    lateral_capacity_kN: float = Field(0.0, ge=0,
        description="Per-pile design lateral capacity (kN).")
    name: str = ""


class PileGroup(BaseModel):
    """Rectangular or arbitrary pile group under a rigid cap."""

    piles: List[PileInGroup]
    spacing_m: float = Field(..., gt=0,
        description="Centre-to-centre spacing (mean) for group efficiency.")
    arrangement_rows: int = Field(1, ge=1)
    arrangement_cols: int = Field(1, ge=1)

    @property
    def n(self) -> int:
        return len(self.piles)

    @property
    def I_x(self) -> float:
        """I_x = Σ y_i² (used for moment-induced axial)."""
        return sum(p.y_m ** 2 for p in self.piles)

    @property
    def I_y(self) -> float:
        """I_y = Σ x_i²"""
        return sum(p.x_m ** 2 for p in self.piles)

    def axial_efficiency(self) -> float:
        return converse_labarre_efficiency(
            self.arrangement_rows, self.arrangement_cols,
            self.spacing_m, self.piles[0].diameter_m if self.piles else 1.0,
        )

    def lateral_efficiency(self) -> float:
        return mokwa_duncan_lateral_efficiency(
            self.spacing_m,
            self.piles[0].diameter_m if self.piles else 1.0,
        )


# ---------------------------------------------------------------------------
# Helpers — common pile group layouts
# ---------------------------------------------------------------------------

def rectangular_group(
    n_rows: int, n_cols: int,
    spacing_m: float, diameter_m: float,
    axial_capacity_kN: float = 0.0,
    tension_capacity_kN: float = 0.0,
    lateral_capacity_kN: float = 0.0,
) -> PileGroup:
    """Build a m × n rectangular pile group centred on (0, 0)."""
    piles: List[PileInGroup] = []
    x_centre = (n_cols - 1) / 2.0
    y_centre = (n_rows - 1) / 2.0
    for i in range(n_rows):
        for j in range(n_cols):
            x = (j - x_centre) * spacing_m
            y = (i - y_centre) * spacing_m
            piles.append(PileInGroup(
                x_m=x, y_m=y, diameter_m=diameter_m,
                axial_capacity_kN=axial_capacity_kN,
                tension_capacity_kN=tension_capacity_kN,
                lateral_capacity_kN=lateral_capacity_kN,
                name=f"P{i + 1}{j + 1}",
            ))
    return PileGroup(
        piles=piles, spacing_m=spacing_m,
        arrangement_rows=n_rows, arrangement_cols=n_cols,
    )


# ---------------------------------------------------------------------------
# Force distribution
# ---------------------------------------------------------------------------

@dataclass
class PileForce:
    pile_name: str
    x_m: float
    y_m: float
    N_kN: float
    H_x_kN: float
    H_y_kN: float
    axial_utilization: float
    lateral_utilization: float
    in_compression: bool


@dataclass
class PileGroupResult:
    """Bundle of per-pile forces + group-level utilizations."""

    forces: List[PileForce]
    N_max_compression: float
    N_max_tension: float
    H_max_per_pile: float
    axial_efficiency: float
    lateral_efficiency: float
    group_axial_utilization: float    # worst pile compression check
    group_tension_utilization: float  # worst pile tension check
    group_lateral_utilization: float
    governing_pile: str
    all_ok: bool


def distribute_loads_rigid_cap(
    group: PileGroup,
    V_kN: float,            # +down
    H_x_kN: float = 0.0,    # global X shear
    H_y_kN: float = 0.0,    # global Y shear
    M_x_kNm: float = 0.0,   # moment about X (causes Δ N in y direction)
    M_y_kNm: float = 0.0,   # moment about Y (causes Δ N in x direction)
) -> PileGroupResult:
    """Distribute V, H_x, H_y, M_x, M_y over the group under a rigid cap.

    Axial per pile (Engesser):
        N_i = V/n  +  M_x · y_i / I_x  +  M_y · x_i / I_y

    Horizontal per pile (uniform among all piles, then × E_h):
        H_xi = (H_x / n) / E_h        ⇒ each pile must resist this much
        H_yi = (H_y / n) / E_h

    Note: the division by E_h means that for tight groups each pile
    has to resist MORE than the simple uniform share — i.e. the group
    is *less* efficient. The resultant horizontal per pile:
        H_i = √(H_xi² + H_yi²)
    """
    n = group.n
    if n == 0:
        raise ValueError("Group has no piles.")
    I_x = group.I_x
    I_y = group.I_y
    E_axial = group.axial_efficiency()
    E_lat = group.lateral_efficiency()
    forces: List[PileForce] = []
    N_max_c = -float("inf")
    N_min_c = float("inf")
    H_max = 0.0
    worst_pile = ""
    worst_util = 0.0
    worst_tension_util = 0.0

    for p in group.piles:
        # Axial
        N_i = V_kN / n
        if I_x > 1e-9:
            N_i += M_x_kNm * p.y_m / I_x
        if I_y > 1e-9:
            N_i += M_y_kNm * p.x_m / I_y

        # Lateral
        H_xi = (H_x_kN / n) / max(E_lat, 1e-6)
        H_yi = (H_y_kN / n) / max(E_lat, 1e-6)
        H_i = math.sqrt(H_xi ** 2 + H_yi ** 2)
        H_max = max(H_max, H_i)

        # Group efficiency for axial: cap_eff = capacity · E_axial
        cap_axial = max(p.axial_capacity_kN * E_axial, 1e-6)
        cap_tension = max(p.tension_capacity_kN, 1e-6)
        cap_lateral = max(p.lateral_capacity_kN, 1e-6)

        if N_i >= 0:
            ax_util = N_i / cap_axial
            tens_util = 0.0
        else:
            ax_util = 0.0
            tens_util = -N_i / cap_tension
        lat_util = H_i / cap_lateral if p.lateral_capacity_kN > 0 else 0.0

        forces.append(PileForce(
            pile_name=p.name or f"P{forces[-1].pile_name[1:] if forces else 1}",
            x_m=p.x_m, y_m=p.y_m, N_kN=N_i,
            H_x_kN=H_xi, H_y_kN=H_yi,
            axial_utilization=ax_util,
            lateral_utilization=lat_util,
            in_compression=N_i >= 0,
        ))
        if N_i > N_max_c:
            N_max_c = N_i
        if N_i < N_min_c:
            N_min_c = N_i
        combined = max(ax_util, tens_util, lat_util)
        if combined > worst_util:
            worst_util = combined
            worst_pile = p.name

    N_max_tension = -N_min_c if N_min_c < 0 else 0.0
    group_ax_util = max(f.axial_utilization for f in forces)
    group_tens_util = max(((-f.N_kN) / max(group.piles[0].tension_capacity_kN, 1e-6))
                          for f in forces if f.N_kN < 0) if any(f.N_kN < 0 for f in forces) else 0.0
    group_lat_util = max(f.lateral_utilization for f in forces)

    all_ok = (group_ax_util <= 1.0 and group_tens_util <= 1.0
              and group_lat_util <= 1.0)

    return PileGroupResult(
        forces=forces,
        N_max_compression=N_max_c,
        N_max_tension=N_max_tension,
        H_max_per_pile=H_max,
        axial_efficiency=E_axial,
        lateral_efficiency=E_lat,
        group_axial_utilization=group_ax_util,
        group_tension_utilization=group_tens_util,
        group_lateral_utilization=group_lat_util,
        governing_pile=worst_pile,
        all_ok=all_ok,
    )


__all__ = [
    "PileInGroup",
    "PileGroup",
    "PileForce",
    "PileGroupResult",
    "converse_labarre_efficiency",
    "mokwa_duncan_lateral_efficiency",
    "rectangular_group",
    "distribute_loads_rigid_cap",
]
