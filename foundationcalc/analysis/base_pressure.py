"""Contact pressure under a rigid rectangular footing — Navier + e>L/6 case.

Sign conventions: see core/loading.py.

Theory: docs/theory/03_shallow_foundations.md §3.2–3.3.
"""

from __future__ import annotations

from enum import Enum
from typing import Tuple

from pydantic import BaseModel

from ..core.geometry import Column, RectangularFoundation
from ..core.loading import LoadCombination


class PressureRegime(str, Enum):
    """Eccentricity regime per §3.3."""

    CENTRED = "centred"           # both |e_x|/L + |e_y|/W within core
    UNIAXIAL_IN_CORE = "uniaxial_in_core"
    OUTSIDE_CORE = "outside_core"
    OVERTURNED = "overturned"     # |e| > a/2 — no static equilibrium possible


class CornerPressures(BaseModel):
    """Bearing-pressure result, all values in kPa."""

    q1: float  # (-X, -Y)
    q2: float  # (-X, +Y)
    q3: float  # (+X, -Y)
    q4: float  # (+X, +Y)
    q_max: float
    q_min: float
    q_avg: float
    e_x: float
    e_y: float
    regime: PressureRegime
    active_area_m2: float


class BasePressureAnalysis:
    """Compute corner pressures under a rigid rectangular footing.

    Self-weight of the footing and any overlying soil is added automatically when
    `include_self_weight=True`. Moments at the column are translated to the centroid
    of the footing taking into account the column eccentricity and any column-base
    shear acting through the footing thickness.
    """

    def __init__(self, foundation: RectangularFoundation, column: Column):
        self.foundation = foundation
        self.column = column

    def calculate_pressures(
        self,
        combination: LoadCombination,
        soil_depth_mm: float = 0.0,
        soil_unit_weight: float = 18.0,
        concrete_unit_weight: float = 25.0,
        include_self_weight: bool = True,
    ) -> CornerPressures:
        """Return CornerPressures (q1, q2, q3, q4 + envelopes)."""

        L = self.foundation.length_m
        W = self.foundation.width_m
        t = self.foundation.thickness_m
        area = self.foundation.area

        # 1. Vertical load N (column + self-weight + soil above footing)
        if include_self_weight:
            sw_concrete = area * t * concrete_unit_weight
            sw_soil = area * (soil_depth_mm / 1000.0) * soil_unit_weight
        else:
            sw_concrete = 0.0
            sw_soil = 0.0
        N = combination.total_fz + sw_concrete + sw_soil

        if N <= 0:
            return CornerPressures(
                q1=0.0, q2=0.0, q3=0.0, q4=0.0,
                q_max=0.0, q_min=0.0, q_avg=0.0,
                e_x=0.0, e_y=0.0,
                regime=PressureRegime.CENTRED,
                active_area_m2=0.0,
            )

        # 2. Moments at the footing centroid (translate from column position)
        dx = (self.column.pos_x / 1000.0) - L / 2.0
        dy = (self.column.pos_y / 1000.0) - W / 2.0
        Mx_total = combination.total_mx + combination.total_fz * dy + combination.total_vy * t
        My_total = combination.total_my + combination.total_fz * dx + combination.total_vx * t

        # 3. Eccentricities (signed)
        ex = My_total / N  # eccentricity in X direction (positive towards +X)
        ey = Mx_total / N  # eccentricity in Y direction

        # 4. Determine regime
        in_core_x = abs(ex) <= L / 6.0 + 1e-9
        in_core_y = abs(ey) <= W / 6.0 + 1e-9
        within_2d_core = (6.0 * abs(ex) / L + 6.0 * abs(ey) / W) <= 1.0 + 1e-9

        # Catastrophic overturning — resultant outside the footing
        if abs(ex) >= L / 2.0 or abs(ey) >= W / 2.0:
            return CornerPressures(
                q1=float("inf"), q2=float("inf"), q3=float("inf"), q4=float("inf"),
                q_max=float("inf"), q_min=0.0, q_avg=N / area,
                e_x=round(ex, 4), e_y=round(ey, 4),
                regime=PressureRegime.OVERTURNED,
                active_area_m2=0.0,
            )

        if in_core_x and in_core_y and within_2d_core:
            regime = PressureRegime.CENTRED
            q1, q2, q3, q4, q_max, q_min, q_avg, active_area = self._navier_pressures(
                N, ex, ey, L, W
            )
        elif abs(ex) > 1e-9 and abs(ey) < 1e-9:
            regime = PressureRegime.OUTSIDE_CORE if not in_core_x else PressureRegime.UNIAXIAL_IN_CORE
            q1, q2, q3, q4, q_max, q_min, q_avg, active_area = self._uniaxial_pressures(
                N, ex, L, W, axis="x"
            )
        elif abs(ex) < 1e-9 and abs(ey) > 1e-9:
            regime = PressureRegime.OUTSIDE_CORE if not in_core_y else PressureRegime.UNIAXIAL_IN_CORE
            q1, q2, q3, q4, q_max, q_min, q_avg, active_area = self._uniaxial_pressures(
                N, ey, W, L, axis="y"
            )
        else:
            # General biaxial outside core — iterative solution required.
            # We fall back to Navier (gives at least one negative tension that the
            # caller must interpret as a warning).
            regime = PressureRegime.OUTSIDE_CORE
            q1, q2, q3, q4, q_max, q_min, q_avg, active_area = self._navier_pressures(
                N, ex, ey, L, W
            )

        return CornerPressures(
            q1=round(q1, 3),
            q2=round(q2, 3),
            q3=round(q3, 3),
            q4=round(q4, 3),
            q_max=round(q_max, 3),
            q_min=round(q_min, 3),
            q_avg=round(q_avg, 3),
            e_x=round(ex, 4),
            e_y=round(ey, 4),
            regime=regime,
            active_area_m2=round(active_area, 4),
        )

    @staticmethod
    def _navier_pressures(
        N: float, ex: float, ey: float, L: float, W: float
    ) -> Tuple[float, float, float, float, float, float, float, float]:
        base = N / (L * W)
        fx = 6.0 * ex / L
        fy = 6.0 * ey / W
        q1 = base * (1.0 - fx - fy)
        q2 = base * (1.0 - fx + fy)
        q3 = base * (1.0 + fx - fy)
        q4 = base * (1.0 + fx + fy)
        corners = [q1, q2, q3, q4]
        return q1, q2, q3, q4, max(corners), min(corners), base, L * W

    @staticmethod
    def _uniaxial_pressures(
        N: float, e: float, a: float, b: float, axis: str
    ) -> Tuple[float, float, float, float, float, float, float, float]:
        """One-way eccentricity (only e in `axis`, the other is 0).

        For e ≥ a/2 the resultant falls outside the footing and no static
        equilibrium is possible — we mark q_max = inf so callers can flag
        the design as catastrophic.
        """
        sign = 1.0 if e >= 0 else -1.0
        e_abs = abs(e)
        if e_abs >= a / 2.0:
            # Overturned — no valid contact. Return inf so utilizations explode.
            return float("inf"), float("inf"), float("inf"), float("inf"), \
                   float("inf"), 0.0, N / (a * b), 0.0
        if e_abs <= a / 6.0 + 1e-9:
            # Full base in compression: q = N/(a·b) · (1 ± 6e/a)
            base = N / (a * b)
            f = 6.0 * e_abs / a
            q_high = base * (1.0 + f)
            q_low = base * (1.0 - f)
            active_area = a * b
        else:
            # Partial base in compression (active length a' = 3·(a/2 − e))
            a_prime = 3.0 * (a / 2.0 - e_abs)
            q_high = 2.0 * N / (a_prime * b)
            q_low = 0.0
            active_area = a_prime * b

        # Assign to corners depending on the axis
        if axis == "x":
            if sign >= 0:
                # eccentricity towards +X → q3, q4 are high
                q1 = q_low; q2 = q_low; q3 = q_high; q4 = q_high
            else:
                q1 = q_high; q2 = q_high; q3 = q_low; q4 = q_low
        else:  # y
            if sign >= 0:
                q1 = q_low; q2 = q_high; q3 = q_low; q4 = q_high
            else:
                q1 = q_high; q2 = q_low; q3 = q_high; q4 = q_low

        corners = [q1, q2, q3, q4]
        return q1, q2, q3, q4, max(corners), min(corners), N / (a * b), active_area
