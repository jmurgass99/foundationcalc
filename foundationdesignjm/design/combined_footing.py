"""Combined footing design — 2 columns on a single rectangular or
trapezoidal RC footing.

Used when:
- Two columns are close enough that their isolated footings would overlap.
- A property-line column cannot have its footing extend beyond the line
  (eccentric column → use a trapezoidal footing or pair with strap beam).

The footing is sized so that the **resultant of the two column loads
passes through the centroid of the contact area** (no overall
eccentricity → uniform soil pressure).

Two shapes supported:
- **Rectangular** when both columns produce a resultant inside the
  property limits.
- **Trapezoidal** when one column is at the property line.

Theory: docs/theory/03_shallow_foundations.md §3.1 + Bowles 2001 §8.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

from pydantic import BaseModel, Field

from ..core.material import Concrete, ReinforcingSteel
from ..design.reinforcement import flexural_reinforcement


class CombinedFootingInputs(BaseModel):
    """Two columns on one footing."""

    P1_kN: float = Field(..., gt=0, description="Axial load on column 1 (kN)")
    P2_kN: float = Field(..., gt=0, description="Axial load on column 2 (kN)")
    col_spacing_m: float = Field(..., gt=0.5,
        description="Centre-to-centre spacing of the two columns (m)")
    column_1_to_property_line_m: float = Field(
        0.0, ge=0,
        description="Distance from column 1 to the property line (m); "
                    "0 means the column is right at the line",
    )
    column_size_m: float = Field(0.40, gt=0.10,
        description="Square column side (m)")
    q_allow_kPa: float = Field(200.0, gt=50,
        description="Allowable soil bearing pressure (kPa)")
    thickness_m: float = Field(0.60, gt=0.30,
        description="Footing thickness h (m)")


@dataclass
class CombinedFootingResult:
    shape: str           # "rectangular" or "trapezoidal"
    L_m: float           # total length
    B_m: float           # uniform width (rectangular)  OR  average width
    B1_m: float = 0.0    # short side (column 1 end)
    B2_m: float = 0.0    # long side (column 2 end)
    x_resultant_m: float = 0.0
    A_required_m2: float = 0.0
    A_provided_m2: float = 0.0
    M_pos_kNm: float = 0.0      # max positive (sagging, top fibre tension)
    M_neg_kNm: float = 0.0      # max negative (hogging, bottom fibre tension)
    V_max_kN: float = 0.0
    As_top_mm2: float = 0.0     # reinforcement near top (hogging)
    As_bot_mm2: float = 0.0     # reinforcement near bottom (sagging)
    note: str = ""


def design_combined_footing(
    inputs: CombinedFootingInputs,
    concrete: Concrete = Concrete(fck=30),
    steel: ReinforcingSteel = ReinforcingSteel(fyk=500),
) -> CombinedFootingResult:
    """Design a combined footing — rectangular if possible, trapezoidal if not."""
    P1 = inputs.P1_kN
    P2 = inputs.P2_kN
    s = inputs.col_spacing_m
    d = inputs.column_1_to_property_line_m
    R = P1 + P2

    # Position of resultant from column 1
    x_R = (P2 * s) / R     # measured from column 1, towards column 2
    x_R_from_property = d + x_R

    # Required base area (no eccentricity → uniform q_allow)
    A_req = R / inputs.q_allow_kPa
    cover = inputs.column_size_m / 2.0  # half column inside the footing edge

    # Try rectangular first: place the footing centred on the resultant.
    # Total length L such that centre lies at x_R_from_property → L = 2 · x_R_from_property
    L_rect = 2.0 * x_R_from_property + inputs.column_size_m
    B_rect = A_req / L_rect

    if d <= 0.05 * s and B_rect > 0:
        # Column 1 is at the property line → trapezoidal so that the footing
        # ends at the property line but the centroid still aligns with the
        # resultant.
        # For a trapezoid of length L with short side B1 (at column 1) and
        # long side B2 (at the far end):
        #   A = (B1 + B2)/2 · L = A_req
        #   centroid x_c = L/3 · (B1 + 2 B2)/(B1 + B2)  measured from B1 end
        # Set x_c = x_R + cover  →  solve for B1, B2 given L.
        L_trap = s + 2.0 * inputs.column_size_m
        x_c_target = x_R_from_property
        # We have one equation A = (B1+B2)/2 · L = A_req → B1 + B2 = 2 A_req/L
        sum_B = 2.0 * A_req / L_trap
        # And L/3 · (B1 + 2 B2)/(B1 + B2) = x_c
        # → (B1 + 2 B2) = 3 · x_c · (B1 + B2) / L
        denom = sum_B if sum_B > 0 else 1.0
        ratio_B2 = (3.0 * x_c_target / L_trap - 1.0)
        # B1 + 2 B2 = sum_B + B2 = sum_B · (3 x_c / L)
        sum_plus_B2 = sum_B * (3.0 * x_c_target / L_trap)
        B2 = sum_plus_B2 - sum_B
        B1 = sum_B - B2
        if B1 < 0 or B2 < 0 or B2 < B1:
            # Trapezoid not geometrically valid; fall back to rectangular
            shape = "rectangular"
            B_avg = B_rect
            B1 = B_rect
            B2 = B_rect
            L_final = L_rect
        else:
            shape = "trapezoidal"
            B_avg = sum_B / 2.0
            L_final = L_trap
    else:
        shape = "rectangular"
        B_avg = B_rect
        B1 = B_rect
        B2 = B_rect
        L_final = L_rect

    A_provided = 0.5 * (B1 + B2) * L_final
    q_avg = R / max(A_provided, 1e-6)

    # ------------- Bending diagram --------------
    # Treat the footing as a beam on the soil (upward) loaded by two point
    # loads (column reactions, downward). The "load" on the beam from the
    # soil per metre is:
    if shape == "rectangular":
        w_soil = q_avg * B_avg  # kN/m
    else:
        # Variable trapezoidal — average for envelope
        w_soil = q_avg * B_avg
    # Coordinates from column 1 face (= property line offset by `d`):
    x1 = d + inputs.column_size_m / 2.0  # column 1 centre
    x2 = x1 + s                           # column 2 centre

    # Soil reaction acts upward, column loads act downward. Computing
    # the moment from the left, with the upward distributed reaction
    # contributing positively, gives a sign convention where:
    #   m > 0  →  hogging in the footing  →  tension on the TOP fibre
    #   m < 0  →  sagging in the footing  →  tension on the BOTTOM fibre
    # The boundary value M_at(L_final) is zero by global equilibrium, so
    # cantilever moments are probed at the column centres (close to the
    # column-face peak), not at the slab edge.
    def M_at(x: float) -> float:
        m = w_soil * x * x / 2.0
        if x > x1:
            m -= P1 * (x - x1)
        if x > x2:
            m -= P2 * (x - x2)
        return m

    # Sample at column centres, midspan, and a fine search inside the span
    span_samples = [
        M_at(x1 + (x2 - x1) * k / 20.0) for k in range(1, 20)
    ]
    M_mid = max(span_samples)            # peak hogging between columns
    M_left_col = M_at(x1) if x1 > 0 else 0.0
    M_right_col = M_at(x2)
    # M_right_col is taken just before the column 2 contribution kicks in;
    # the matching value just AFTER column 2 (cantilever right of col 2)
    # is also evaluated to capture the right overhang peak:
    if L_final > x2:
        right_overhang_samples = [
            M_at(x2 + (L_final - x2) * k / 10.0)
            for k in range(1, 11)
        ]
        M_right_cant = min(right_overhang_samples)  # most negative if any
    else:
        M_right_cant = 0.0

    moments = [M_mid, M_left_col, M_right_col, M_right_cant]
    M_top = max(moments)   # most positive  → top steel (hogging)
    M_bot = min(moments)   # most negative  → bottom steel (sagging)

    # Legacy fields keep the older naming so existing callers don't break,
    # but the values now reflect physical sign: M_neg is the sagging
    # extreme (bottom-fibre tension), M_pos is the hogging extreme
    # (top-fibre tension).
    M_pos = M_top
    M_neg = M_bot

    # Shear: max at column faces
    V_max = max(P1, P2)

    # ------------- Reinforcement (per metre width) --------------
    d_eff_mm = inputs.thickness_m * 1000 - 70 - 10  # cover 70, half ϕ20
    flex_top = flexural_reinforcement(
        M_Ed_kNm=abs(M_top),
        b_mm=1000, d_mm=d_eff_mm,
        concrete=concrete, steel=steel,
    )
    flex_bot = flexural_reinforcement(
        M_Ed_kNm=abs(M_bot),
        b_mm=1000, d_mm=d_eff_mm,
        concrete=concrete, steel=steel,
    )
    # Multiply by average width
    As_top = flex_top.As_provided * B_avg
    As_bot = flex_bot.As_provided * B_avg

    return CombinedFootingResult(
        shape=shape,
        L_m=L_final,
        B_m=B_avg,
        B1_m=B1,
        B2_m=B2,
        x_resultant_m=x_R_from_property,
        A_required_m2=A_req,
        A_provided_m2=A_provided,
        M_pos_kNm=M_pos, M_neg_kNm=M_neg,
        V_max_kN=V_max,
        As_top_mm2=As_top, As_bot_mm2=As_bot,
        note=f"q_avg = {q_avg:.1f} kPa,  q_allow = {inputs.q_allow_kPa:.1f} kPa",
    )


__all__ = [
    "CombinedFootingInputs",
    "CombinedFootingResult",
    "design_combined_footing",
]
