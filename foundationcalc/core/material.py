"""Materials: concrete, reinforcing steel, soil (proxy)."""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field


class Concrete(BaseModel):
    """Structural concrete (EC2 EN 1992-1-1)."""

    name: str = "C25/30"
    fck: float = Field(25.0, gt=0, description="Characteristic cylinder strength (MPa)")
    unit_weight: float = Field(25.0, gt=0, description="γ_c (kN/m^3)")
    gamma_c: float = Field(1.5, gt=0, description="Concrete partial safety factor")
    alpha_cc: float = Field(1.0, gt=0, description="Long-term effects factor")

    @property
    def fcd(self) -> float:
        """Design compressive strength (MPa)."""
        return self.alpha_cc * self.fck / self.gamma_c

    @property
    def fctm(self) -> float:
        """Mean axial tensile strength fctm (MPa)."""
        if self.fck <= 50:
            return 0.30 * (self.fck ** (2.0 / 3.0))
        return 2.12 * math.log(1 + (self.fck + 8) / 10.0)

    @property
    def Ecm(self) -> float:
        """Secant modulus of elasticity Ecm (MPa)."""
        return 22000.0 * ((self.fck + 8) / 10.0) ** 0.3


class ReinforcingSteel(BaseModel):
    """Reinforcing steel (B500S, B400S, B500SD, etc.)."""

    name: str = "B500S"
    fyk: float = Field(500.0, gt=0, description="Characteristic yield strength (MPa)")
    gamma_s: float = Field(1.15, gt=0, description="Steel partial safety factor")
    Es: float = Field(200000.0, gt=0, description="Modulus of elasticity (MPa)")

    @property
    def fyd(self) -> float:
        return self.fyk / self.gamma_s

    @property
    def fyd_strut_and_tie(self) -> float:
        """Limit f_yd ≤ 400 N/mm² in strut-and-tie method (EHE / EC2)."""
        return min(self.fyd, 400.0)


# Backward compatibility — Soil class kept here but the rich one lives in core.soil
class Soil(BaseModel):
    """Lightweight soil model for the existing API. Prefer `core.soil.SoilProfile`."""

    bearing_capacity: float = Field(150.0, gt=0, description="Presumed bearing capacity (kN/m^2)")
    unit_weight: float = Field(18.0, gt=0, description="Unit weight (kN/m^3)")
    friction_angle: float = Field(30.0, ge=0, le=60)
    cohesion: float = Field(0.0, ge=0)
    undrained_shear_strength: Optional[float] = None
