"""Pile and pile-group / pile-cap geometry models.

Theory: docs/theory/05_pile_foundations.md.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class PileType(str, Enum):
    DRIVEN_PRECAST = "driven_precast"
    DRIVEN_IN_SITU = "driven_in_situ"
    BORED = "bored"
    CFA = "cfa"
    MICROPILE = "micropile"
    STEEL = "steel"


class PileSupport(str, Enum):
    END_BEARING = "end_bearing"
    FRICTION = "friction"
    COMBINED = "combined"
    BATTER = "batter"


class Pile(BaseModel):
    """Single pile."""

    diameter: float = Field(..., gt=0, description="Pile diameter (mm)")
    length: float = Field(..., gt=0, description="Pile length below cap (mm)")
    pile_type: PileType = PileType.BORED
    support: PileSupport = PileSupport.COMBINED
    inclination_deg: float = Field(0.0, ge=0, le=30)

    @property
    def diameter_m(self) -> float:
        return self.diameter / 1000.0

    @property
    def length_m(self) -> float:
        return self.length / 1000.0

    @property
    def area(self) -> float:
        """Cross-section area in m²."""
        return 3.141592653589793 * (self.diameter_m / 2.0) ** 2

    @property
    def shaft_perimeter(self) -> float:
        return 3.141592653589793 * self.diameter_m

    @property
    def diameter_class(self) -> str:
        d = self.diameter_m
        if d < 0.25:
            return "micropile"
        if d < 0.80:
            return "medium"
        return "large"


class PileInPlan(BaseModel):
    """Pile with its planar position relative to a pile-cap reference (mm)."""

    pile: Pile
    x: float = Field(..., description="X coordinate (mm) from cap centroid")
    y: float = Field(..., description="Y coordinate (mm) from cap centroid")
    name: str = "P"


class PileCap(BaseModel):
    """Rigid pile cap supporting one or more piles."""

    length: float = Field(..., gt=0, description="Cap length along X (mm)")
    width: float = Field(..., gt=0, description="Cap width along Y (mm)")
    thickness: float = Field(800.0, gt=0, description="Cap depth (mm)")
    piles: List[PileInPlan]

    @property
    def n_piles(self) -> int:
        return len(self.piles)

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
    def area(self) -> float:
        return self.length_m * self.width_m

    def pile_positions_m(self) -> List[Tuple[float, float]]:
        return [(p.x / 1000.0, p.y / 1000.0) for p in self.piles]

    def minimum_thickness_recommended(self) -> float:
        """h_min ≥ max(40 cm, Ø_pile) per EHE."""
        if not self.piles:
            return 400.0
        max_d = max(p.pile.diameter for p in self.piles)
        return max(400.0, max_d)
