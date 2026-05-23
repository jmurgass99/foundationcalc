"""Foundation geometry: spread, strip, combined, mat, and column.

All linear dimensions are stored in millimetres (mm); areas in m² unless noted.
Theory: docs/theory/01_introduction.md, 03_shallow_foundations.md
"""

from __future__ import annotations

from enum import Enum
from typing import List, Tuple

from pydantic import BaseModel, Field


class FootingType(str, Enum):
    SPREAD = "spread"        # square / rectangular pad
    STRIP = "strip"          # long strip / wall footing
    COMBINED = "combined"    # supports 2+ columns
    STRAP = "strap"          # eccentric + interior connected by strap beam
    MAT = "mat"              # raft
    PILE_CAP = "pile_cap"


class RectangularFoundation(BaseModel):
    """Rectangular pad / spread foundation."""

    length: float = Field(..., gt=0, description="Foundation length (mm), X-axis")
    width: float = Field(..., gt=0, description="Foundation width (mm), Y-axis")
    thickness: float = Field(300.0, gt=0, description="Foundation thickness h (mm)")
    embedment_depth: float = Field(
        0.0, ge=0,
        description="Depth from ground surface to footing base (mm)",
    )
    footing_type: FootingType = FootingType.SPREAD

    @property
    def length_m(self) -> float:
        return self.length / 1000.0

    @property
    def width_m(self) -> float:
        return self.width / 1000.0

    @property
    def thickness_m(self) -> float:
        return self.thickness / 1000.0

    @property
    def depth_m(self) -> float:
        return self.embedment_depth / 1000.0

    @property
    def area(self) -> float:
        """Plan area in m²."""
        return self.length_m * self.width_m

    @property
    def perimeter(self) -> float:
        """Plan perimeter in m."""
        return 2.0 * (self.length_m + self.width_m)

    def section_modulus(self) -> Tuple[float, float]:
        """(W_x, W_y) section moduli of the base in m³ (about centroidal axes).

        W_x ≡ I_x / (W/2) for bending about X (varies stress in Y direction).
        """
        L = self.length_m
        W = self.width_m
        Wx = L * W ** 2 / 6.0  # about X axis → stress in Y
        Wy = W * L ** 2 / 6.0  # about Y axis → stress in X
        return Wx, Wy

    def is_rigid(self, cantilever_v_m: float) -> bool:
        """A footing is rigid when v < 2·h (cantilever vs thickness).

        v is the cantilever length from column face to footing edge in m.
        """
        return cantilever_v_m < 2.0 * self.thickness_m

    def effective_dimensions(self, ex_m: float, ey_m: float) -> Tuple[float, float]:
        """EC7 effective area dimensions accounting for eccentricities (m)."""
        Bp = max(0.0, self.width_m - 2.0 * abs(ey_m))
        Lp = max(0.0, self.length_m - 2.0 * abs(ex_m))
        return Lp, Bp


class StripFoundation(RectangularFoundation):
    """Long strip / wall footing. Width per metre run is the design parameter."""

    footing_type: FootingType = FootingType.STRIP

    @property
    def aspect_ratio(self) -> float:
        return self.length_m / self.width_m


class CombinedFoundation(BaseModel):
    """Combined footing supporting 2+ column loads (rectangular or trapezoidal)."""

    length: float = Field(..., gt=0, description="Total length (mm)")
    width_left: float = Field(..., gt=0, description="Width at left end (mm)")
    width_right: float = Field(..., gt=0, description="Width at right end (mm)")
    thickness: float = Field(500.0, gt=0)
    embedment_depth: float = Field(0.0, ge=0)
    footing_type: FootingType = FootingType.COMBINED

    @property
    def area(self) -> float:
        return (self.width_left + self.width_right) / 2.0 * self.length / 1e6

    @property
    def is_trapezoidal(self) -> bool:
        return abs(self.width_left - self.width_right) > 1e-6

    @property
    def centroid_along_length(self) -> float:
        """X-coordinate of the trapezoid centroid (from the left edge, in mm)."""
        a = self.width_left
        b = self.width_right
        L = self.length
        if abs(a - b) < 1e-9:
            return L / 2.0
        return L * (2 * b + a) / (3 * (a + b))


class StrapFoundation(BaseModel):
    """Boundary-line eccentric footing connected to an interior footing by a strap beam."""

    boundary_footing: RectangularFoundation
    interior_footing: RectangularFoundation
    strap_length: float = Field(..., gt=0, description="Centre-to-centre distance (mm)")
    strap_width: float = Field(300.0, gt=0)
    strap_depth: float = Field(500.0, gt=0)
    footing_type: FootingType = FootingType.STRAP


class MatFoundation(RectangularFoundation):
    """Mat / raft foundation."""

    footing_type: FootingType = FootingType.MAT
    column_grid: List[Tuple[float, float]] = Field(
        default_factory=list,
        description="(x, y) positions of column loads, in mm relative to the bottom-left corner.",
    )


class Column(BaseModel):
    """Rectangular column at the top of a footing."""

    length: float = Field(..., gt=0, description="Column dimension along X (mm)")
    width: float = Field(..., gt=0, description="Column dimension along Y (mm)")
    pos_x: float = Field(..., description="Centre X-coordinate on the footing (mm, from bottom-left)")
    pos_y: float = Field(..., description="Centre Y-coordinate on the footing (mm, from bottom-left)")

    @property
    def area(self) -> float:
        return self.length * self.width / 1e6

    def is_central(self, foundation: RectangularFoundation, tolerance_mm: float = 1.0) -> bool:
        return (
            abs(self.pos_x - foundation.length / 2.0) < tolerance_mm
            and abs(self.pos_y - foundation.width / 2.0) < tolerance_mm
        )

    def is_edge(self, foundation: RectangularFoundation, tolerance_mm: float = 1.0) -> bool:
        """True if column sits on an edge (but not a corner)."""
        on_long_edge = (
            abs(self.pos_x - self.length / 2.0) < tolerance_mm
            or abs(self.pos_x - (foundation.length - self.length / 2.0)) < tolerance_mm
        )
        on_short_edge = (
            abs(self.pos_y - self.width / 2.0) < tolerance_mm
            or abs(self.pos_y - (foundation.width - self.width / 2.0)) < tolerance_mm
        )
        return (on_long_edge and not on_short_edge) or (on_short_edge and not on_long_edge)

    def is_corner(self, foundation: RectangularFoundation, tolerance_mm: float = 1.0) -> bool:
        """True if column sits on a corner of the footing."""
        on_long_edge = (
            abs(self.pos_x - self.length / 2.0) < tolerance_mm
            or abs(self.pos_x - (foundation.length - self.length / 2.0)) < tolerance_mm
        )
        on_short_edge = (
            abs(self.pos_y - self.width / 2.0) < tolerance_mm
            or abs(self.pos_y - (foundation.width - self.width / 2.0)) < tolerance_mm
        )
        return on_long_edge and on_short_edge

    def punching_beta(self, foundation: RectangularFoundation) -> float:
        """EC2 β factor for punching (1.15 / 1.40 / 1.50)."""
        if self.is_corner(foundation):
            return 1.50
        if self.is_edge(foundation):
            return 1.40
        return 1.15
