"""Soil and ground-water model.

Theory: docs/theory/01_introduction.md, 02_eurocode7.md
"""

from __future__ import annotations

import math
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class DrainageCondition(str, Enum):
    DRAINED = "drained"
    UNDRAINED = "undrained"


class SoilType(str, Enum):
    COHESIVE = "cohesive"
    COHESIONLESS = "cohesionless"
    MIXED = "mixed"


class SoilLayer(BaseModel):
    """A single soil layer with characteristic parameters."""

    name: str = "layer"
    thickness: float = Field(..., gt=0, description="Layer thickness in m")
    soil_type: SoilType = SoilType.COHESIONLESS

    # Strength parameters
    friction_angle: float = Field(30.0, ge=0, le=60, description="phi' in degrees")
    cohesion: float = Field(0.0, ge=0, description="c' in kPa (effective cohesion)")
    undrained_shear_strength: Optional[float] = Field(
        None, ge=0, description="c_u in kPa (undrained)"
    )

    # Weight & water
    unit_weight: float = Field(18.0, gt=0, description="γ in kN/m^3 (above water table)")
    saturated_unit_weight: Optional[float] = Field(
        None, gt=0, description="γ_sat in kN/m^3"
    )

    # Stiffness
    youngs_modulus: Optional[float] = Field(None, gt=0, description="E in MPa")
    poisson_ratio: Optional[float] = Field(0.3, ge=0, le=0.5)

    # Other
    OCR: float = Field(1.0, ge=1.0, description="Overconsolidation ratio")
    SPT_N: Optional[int] = Field(None, ge=0)
    cone_resistance_qc: Optional[float] = Field(None, gt=0, description="CPT q_c in MPa")

    @field_validator("undrained_shear_strength", mode="after")
    @classmethod
    def _coerce_cu(cls, v: Optional[float]) -> Optional[float]:
        return v

    def effective_unit_weight(self, below_water: bool = False, gamma_w: float = 9.81) -> float:
        """γ' = γ_sat − γ_w if below WT and γ_sat is known; otherwise γ."""
        if below_water and self.saturated_unit_weight is not None:
            return self.saturated_unit_weight - gamma_w
        return self.unit_weight

    def K0(self) -> float:
        """At-rest earth pressure coefficient (Jaky / Mayne–Kulhawy).

        K_0 = (1 − sin φ') · OCR^(sin φ')
        """
        sin_phi = math.sin(math.radians(self.friction_angle))
        return (1.0 - sin_phi) * (self.OCR ** sin_phi)

    def Ka_rankine(self) -> float:
        """Rankine active earth-pressure coefficient."""
        return math.tan(math.radians(45.0 - self.friction_angle / 2.0)) ** 2

    def Kp_rankine(self) -> float:
        """Rankine passive earth-pressure coefficient."""
        return math.tan(math.radians(45.0 + self.friction_angle / 2.0)) ** 2


class SoilProfile(BaseModel):
    """Layered soil profile with an optional ground-water table.

    Depth coordinate increases downward starting from ground surface (z = 0).
    """

    layers: List[SoilLayer]
    water_table_depth: Optional[float] = Field(
        None, description="Depth from surface to water table (m). None means no WT."
    )
    gamma_w: float = Field(9.81, gt=0, description="Water unit weight (kN/m^3)")

    @property
    def total_depth(self) -> float:
        return sum(layer.thickness for layer in self.layers)

    def layer_at(self, depth: float) -> SoilLayer:
        """Return the layer that contains `depth` (m). Last layer extends to infinity."""
        if depth < 0:
            raise ValueError("Depth must be non-negative")
        running = 0.0
        for layer in self.layers:
            running += layer.thickness
            if depth <= running + 1e-9:
                return layer
        return self.layers[-1]

    def total_stress_at(self, depth: float) -> float:
        """Total vertical stress σ_v at depth (kPa = kN/m^2).

        Splits each layer at the water-table depth so that the dry unit weight
        is used above and the saturated unit weight below.
        """
        if depth < 0:
            raise ValueError("Depth must be non-negative")
        sigma = 0.0
        z_top = 0.0
        wt = self.water_table_depth
        for layer in self.layers:
            z_bottom = min(z_top + layer.thickness, depth)
            if z_bottom <= z_top:
                break
            # Split at the water-table boundary if it falls inside this layer
            if wt is not None and z_top < wt < z_bottom:
                dz_above = wt - z_top
                dz_below = z_bottom - wt
                gamma_sat = layer.saturated_unit_weight or layer.unit_weight
                sigma += layer.unit_weight * dz_above + gamma_sat * dz_below
            else:
                below = wt is not None and z_top >= wt
                gamma = (
                    (layer.saturated_unit_weight or layer.unit_weight)
                    if below
                    else layer.unit_weight
                )
                sigma += gamma * (z_bottom - z_top)
            z_top = z_bottom
            if z_top >= depth:
                break
        return sigma

    def pore_pressure_at(self, depth: float) -> float:
        """Hydrostatic pore-water pressure at depth (kPa). Returns 0 above WT."""
        if self.water_table_depth is None or depth <= self.water_table_depth:
            return 0.0
        return self.gamma_w * (depth - self.water_table_depth)

    def effective_stress_at(self, depth: float) -> float:
        """σ'_v = σ_v − u."""
        return self.total_stress_at(depth) - self.pore_pressure_at(depth)


# Convenience factories ------------------------------------------------------

def homogeneous_sand(
    phi: float = 35.0,
    gamma: float = 18.0,
    depth: float = 20.0,
    name: str = "sand",
) -> SoilProfile:
    """Build a homogeneous sand profile (cohesionless, no water table)."""
    return SoilProfile(
        layers=[
            SoilLayer(
                name=name,
                thickness=depth,
                soil_type=SoilType.COHESIONLESS,
                friction_angle=phi,
                cohesion=0.0,
                unit_weight=gamma,
            )
        ]
    )


def homogeneous_clay(
    cu: float = 50.0,
    gamma: float = 19.0,
    depth: float = 20.0,
    name: str = "clay",
) -> SoilProfile:
    """Build a homogeneous undrained clay profile."""
    return SoilProfile(
        layers=[
            SoilLayer(
                name=name,
                thickness=depth,
                soil_type=SoilType.COHESIVE,
                friction_angle=0.0,
                cohesion=0.0,
                undrained_shear_strength=cu,
                unit_weight=gamma,
            )
        ]
    )
