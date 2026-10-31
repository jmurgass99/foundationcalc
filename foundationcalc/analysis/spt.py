"""Standard Penetration Test (SPT) parameter correlations.

The SPT N value is the number of blows of a 63.5 kg hammer falling 760 mm
to drive a standard 50 mm sampler 300 mm into the soil after a 150 mm
seating drive. Corrections applied:

1. Overburden correction → N_1 (Liao & Whitman 1986):
        N_1 = C_N · N         with C_N = √(p_a / σ'_v0),  0.5 < C_N < 2
2. Energy correction (60 % rod-energy ratio):
        N_60 = N · (ER / 60)
3. Combined: N_1(60) = C_N · N · (ER / 60)

Correlations implemented (re-derived from primary sources):
- **Peck-Hanson-Thornburn (1974)** N_60 → φ' (sand).
- **Hatanaka-Uchida (1996)** N_1(60) → φ' (modern, more accurate).
- **Stroud (1974)** N → c_u (clay).
- **Schmertmann (1970)** N → E (sand).
- **Bowles (1996)** N → unit weight (rough indicator).

Theory: docs/theory/10_in_situ_tests.md.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


P_A_kPa = 100.0   # atmospheric pressure


class SoilTypeSPT(str, Enum):
    SAND = "sand"
    SILT = "silt"
    CLAY = "clay"
    GRAVEL = "gravel"


class SPTReading(BaseModel):
    """One SPT depth point."""

    depth_m: float = Field(..., ge=0)
    N_raw: int = Field(..., ge=0)
    sigma_v0_eff_kPa: float = Field(..., ge=0)
    energy_ratio_ER: float = Field(60.0, gt=0, le=100, description="Hammer energy ratio (%)")
    soil_type: SoilTypeSPT = SoilTypeSPT.SAND


# ---------------------------------------------------------------------------
# Corrections
# ---------------------------------------------------------------------------

def overburden_correction_C_N(sigma_v0_eff_kPa: float, p_a_kPa: float = P_A_kPa) -> float:
    """Liao & Whitman (1986):  C_N = √(p_a / σ'_v0), clamped to [0.5, 2.0]."""
    if sigma_v0_eff_kPa <= 0:
        return 2.0
    Cn = math.sqrt(p_a_kPa / sigma_v0_eff_kPa)
    return min(max(Cn, 0.5), 2.0)


def energy_correction(N_raw: int, energy_ratio_ER: float) -> float:
    """Convert N at field ER to N_60."""
    return N_raw * (energy_ratio_ER / 60.0)


def normalised_SPT(reading: SPTReading, p_a_kPa: float = P_A_kPa) -> float:
    """Return N_1(60) — overburden + energy corrected."""
    N_60 = energy_correction(reading.N_raw, reading.energy_ratio_ER)
    Cn = overburden_correction_C_N(reading.sigma_v0_eff_kPa, p_a_kPa)
    return Cn * N_60


# ---------------------------------------------------------------------------
# φ' correlations for sand
# ---------------------------------------------------------------------------

def phi_peck_hanson_thornburn(N_60: float) -> float:
    """Peck-Hanson-Thornburn (1974) tabulated chart, polynomial fit.

    Valid range: 0 < N_60 ≲ 50.  Returns φ' (deg).
    """
    # Polynomial fit to the chart: phi = 27.1 + 0.30·N − 0.00054·N²
    return 27.1 + 0.30 * N_60 - 0.00054 * N_60 ** 2


def phi_hatanaka_uchida(N_1_60: float) -> float:
    """Hatanaka & Uchida (1996):  φ' = √(20·N_1(60)) + 20  (deg)."""
    return math.sqrt(20.0 * max(N_1_60, 0.0)) + 20.0


def phi_japan_road_association(N_1_60: float) -> float:
    """Japan Road Association (1990):  φ' = √(15·N_1(60)) + 15  (deg)."""
    return math.sqrt(15.0 * max(N_1_60, 0.0)) + 15.0


# ---------------------------------------------------------------------------
# c_u correlations for clay
# ---------------------------------------------------------------------------

def cu_stroud(N_60: float, plasticity_index: float = 30.0) -> float:
    """Stroud (1974):  c_u = f_1 · N_60     [kPa]

    f_1 depends on plasticity index PI:
      PI > 30 → f_1 ≈ 4.5
      PI = 20 → f_1 ≈ 5.0
      PI = 10 → f_1 ≈ 6.0
    """
    if plasticity_index >= 30:
        f1 = 4.5
    elif plasticity_index >= 20:
        f1 = 5.0
    else:
        f1 = 6.0
    return f1 * N_60


def cu_terzaghi_peck(N_60: float) -> float:
    """Terzaghi & Peck (1948) — quick estimate:  c_u ≈ 6.25 · N_60 [kPa]."""
    return 6.25 * N_60


# ---------------------------------------------------------------------------
# Young's modulus correlations
# ---------------------------------------------------------------------------

def E_schmertmann(N_60: float, soil_type: SoilTypeSPT = SoilTypeSPT.SAND) -> float:
    """Schmertmann (1970) — Young's modulus from N_60.

    | Soil type       | E [MPa]        |
    | sand (dry/wet)  | 0.766 · N_60   |
    | sand (sat)      | 0.5 · N_60     |
    | silty sand      | 0.6 · N_60     |
    | clayey sand     | 0.32 · N_60    |
    """
    if soil_type == SoilTypeSPT.SAND:
        return 0.766 * N_60
    if soil_type == SoilTypeSPT.SILT:
        return 0.6 * N_60
    if soil_type == SoilTypeSPT.CLAY:
        return 0.32 * N_60
    if soil_type == SoilTypeSPT.GRAVEL:
        return 1.20 * N_60
    return 0.766 * N_60


def E_bowles(N_60: float, soil_type: SoilTypeSPT = SoilTypeSPT.SAND) -> float:
    """Bowles (1996) — Young's modulus E (MPa):

      sand:   E = 0.5·(N_60 + 15)
      gravel: E = 0.6·(N_60 + 6)
      clay:   E = 0.4·N_60
    """
    if soil_type == SoilTypeSPT.GRAVEL:
        return 0.6 * (N_60 + 6)
    if soil_type == SoilTypeSPT.CLAY:
        return 0.4 * N_60
    return 0.5 * (N_60 + 15)


# ---------------------------------------------------------------------------
# Relative density (sand)
# ---------------------------------------------------------------------------

def relative_density_skempton(N_1_60: float) -> float:
    """Skempton (1986):  D_R² = N_1(60) / 60     ⇒  D_R (%) clamped 0-100."""
    Dr = math.sqrt(max(N_1_60 / 60.0, 0.0))
    return min(max(Dr * 100.0, 0.0), 100.0)


# ---------------------------------------------------------------------------
# Composite helper
# ---------------------------------------------------------------------------

class SPTDerived(BaseModel):
    depth_m: float
    N_raw: int
    N_60: float
    N_1_60: float
    phi_deg: Optional[float] = None
    c_u_kPa: Optional[float] = None
    E_MPa: Optional[float] = None
    relative_density_pct: Optional[float] = None
    soil_type: SoilTypeSPT


def derive_parameters(
    reading: SPTReading,
    plasticity_index: float = 30.0,
) -> SPTDerived:
    """Return all derived parameters for one SPT reading."""
    N_60 = energy_correction(reading.N_raw, reading.energy_ratio_ER)
    N_1_60 = normalised_SPT(reading)
    if reading.soil_type in (SoilTypeSPT.SAND, SoilTypeSPT.GRAVEL):
        phi = phi_hatanaka_uchida(N_1_60)
        cu = None
        Dr = relative_density_skempton(N_1_60)
    else:  # clay or silt
        phi = None
        cu = cu_stroud(N_60, plasticity_index)
        Dr = None
    E = E_schmertmann(N_60, reading.soil_type)
    return SPTDerived(
        depth_m=reading.depth_m, N_raw=reading.N_raw,
        N_60=N_60, N_1_60=N_1_60,
        phi_deg=phi, c_u_kPa=cu, E_MPa=E,
        relative_density_pct=Dr, soil_type=reading.soil_type,
    )


__all__ = [
    "SoilTypeSPT",
    "SPTReading",
    "SPTDerived",
    "overburden_correction_C_N",
    "energy_correction",
    "normalised_SPT",
    "phi_peck_hanson_thornburn",
    "phi_hatanaka_uchida",
    "phi_japan_road_association",
    "cu_stroud",
    "cu_terzaghi_peck",
    "E_schmertmann",
    "E_bowles",
    "relative_density_skempton",
    "derive_parameters",
]
