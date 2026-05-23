"""Loads, actions and load combinations (EN 1990 + EN 1997-1)."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LoadType(str, Enum):
    """Load classification per EN 1990."""

    PERMANENT = "G"        # γ_G
    IMPOSED = "Q"          # γ_Q (variable)
    WIND = "W"             # variable, usually accompanying
    SNOW = "S"             # variable
    SEISMIC = "AEd"        # accidental seismic action
    ACCIDENTAL = "A"       # other accidental
    PRESTRESS = "P"        # prestress


class ActionCategory(str, Enum):
    """For ψ factors (EN 1990 Table A1.1)."""

    IMPOSED_RESIDENTIAL = "imposed_residential"
    IMPOSED_OFFICE = "imposed_office"
    IMPOSED_STORAGE = "imposed_storage"
    WIND = "wind"
    SNOW = "snow_below_1000m"
    SNOW_HIGH = "snow_above_1000m"
    TEMPERATURE = "temperature"
    DEFAULT = "default"


class PointLoad(BaseModel):
    """Point load applied at a column base.

    Sign conventions:
    - fz positive downwards (compression on the footing).
    - mx, my are bending moments about X, Y axes at column base level.
    - vx, vy are horizontal shear forces in X, Y directions.
    """

    name: str = "Column Load"
    fz: float = Field(0.0, description="Axial load (kN, +down)")
    mx: float = Field(0.0, description="Moment about X axis (kN·m)")
    my: float = Field(0.0, description="Moment about Y axis (kN·m)")
    vx: float = Field(0.0, description="Shear in X (kN)")
    vy: float = Field(0.0, description="Shear in Y (kN)")
    load_type: LoadType = LoadType.PERMANENT
    category: ActionCategory = ActionCategory.DEFAULT


class CombinationEntry(BaseModel):
    """A factored load entry within a combination: factor · load."""

    load: PointLoad
    factor: float = 1.0


class LoadCombination(BaseModel):
    """A linear combination of factored point loads."""

    name: str
    entries: List[CombinationEntry]

    # Aggregate per direction
    @property
    def total_fz(self) -> float:
        return sum(e.load.fz * e.factor for e in self.entries)

    @property
    def total_mx(self) -> float:
        return sum(e.load.mx * e.factor for e in self.entries)

    @property
    def total_my(self) -> float:
        return sum(e.load.my * e.factor for e in self.entries)

    @property
    def total_vx(self) -> float:
        return sum(e.load.vx * e.factor for e in self.entries)

    @property
    def total_vy(self) -> float:
        return sum(e.load.vy * e.factor for e in self.entries)

    @property
    def total_horizontal(self) -> float:
        return (self.total_vx ** 2 + self.total_vy ** 2) ** 0.5


# ---------------------------------------------------------------------------
# Standard combination builders (EN 1990 §6.4)
# ---------------------------------------------------------------------------

def uls_persistent_transient(
    permanent: List[PointLoad],
    leading_variable: Optional[PointLoad] = None,
    other_variables: Optional[List[PointLoad]] = None,
    gamma_G: float = 1.35,
    gamma_Q: float = 1.50,
    psi_0_other: float = 0.7,
    name: str = "ULS_persistent",
) -> LoadCombination:
    """Build the persistent/transient ULS combination per EN 1990 (6.10).

    Σ γ_G,j · G_k,j  +  γ_Q,1 · Q_k,1  +  Σ γ_Q,i · ψ_0,i · Q_k,i
    """
    entries: List[CombinationEntry] = []
    for g in permanent:
        entries.append(CombinationEntry(load=g, factor=gamma_G))
    if leading_variable is not None:
        entries.append(CombinationEntry(load=leading_variable, factor=gamma_Q))
    for q in other_variables or []:
        entries.append(CombinationEntry(load=q, factor=gamma_Q * psi_0_other))
    return LoadCombination(name=name, entries=entries)


def sls_characteristic(
    permanent: List[PointLoad],
    leading_variable: Optional[PointLoad] = None,
    other_variables: Optional[List[PointLoad]] = None,
    psi_0_other: float = 0.7,
    name: str = "SLS_characteristic",
) -> LoadCombination:
    """Characteristic SLS: Σ G + Q_1 + Σ ψ_0,i · Q_i."""
    entries: List[CombinationEntry] = [
        CombinationEntry(load=g, factor=1.0) for g in permanent
    ]
    if leading_variable is not None:
        entries.append(CombinationEntry(load=leading_variable, factor=1.0))
    for q in other_variables or []:
        entries.append(CombinationEntry(load=q, factor=psi_0_other))
    return LoadCombination(name=name, entries=entries)


def sls_quasi_permanent(
    permanent: List[PointLoad],
    variables: Optional[List[PointLoad]] = None,
    psi_2: float = 0.3,
    name: str = "SLS_quasi_permanent",
) -> LoadCombination:
    """Quasi-permanent SLS: Σ G + Σ ψ_2,i · Q_i."""
    entries: List[CombinationEntry] = [
        CombinationEntry(load=g, factor=1.0) for g in permanent
    ]
    for q in variables or []:
        entries.append(CombinationEntry(load=q, factor=psi_2))
    return LoadCombination(name=name, entries=entries)


def seismic_combination(
    permanent: List[PointLoad],
    seismic: PointLoad,
    variables: Optional[List[PointLoad]] = None,
    psi_2: float = 0.3,
    name: str = "Seismic",
) -> LoadCombination:
    """Seismic combination: Σ G + A_Ed + Σ ψ_2,i · Q_i (EN 1990 6.12)."""
    entries: List[CombinationEntry] = [
        CombinationEntry(load=g, factor=1.0) for g in permanent
    ]
    entries.append(CombinationEntry(load=seismic, factor=1.0))
    for q in variables or []:
        entries.append(CombinationEntry(load=q, factor=psi_2))
    return LoadCombination(name=name, entries=entries)
