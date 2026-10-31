"""Eurocode 8 — Part 1: seismic design spectra and national zone data.

Implements:
- The horizontal **elastic response spectrum** S_e(T) per EN 1998-1 §3.2.2.2.
- The **design response spectrum** S_d(T) per §3.2.2.5 (divided by the
  behaviour factor q).
- The five **ground types** A–E with their S, T_B, T_C, T_D parameters
  for spectrum **Type 1** (M_s > 5.5) and **Type 2** (M_s ≤ 5.5).
- An extensible **seismic-zone database** with the reference peak ground
  acceleration a_gR per location for each supported national annex.

Currently bundled national annexes:
- **Spain** (NCSE-02 mapping + UNE-EN 1998-1 NA): basic zones with a_gR.
- Hooks for **Italy** (NTC) and **France** (PS92) — empty by default.

The mapping `country → city/zone → a_gR` is intentionally simple so that
new countries can be added by extending `SEISMIC_ZONES`.

Theory: docs/theory/17_eurocode8.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ground types and spectrum parameters
# ---------------------------------------------------------------------------

class GroundType(str, Enum):
    """EN 1998-1 Table 3.1 ground classification."""

    A = "A"   # Rock or rock-like (v_s,30 > 800 m/s)
    B = "B"   # Very dense sand/gravel (360 < v_s,30 ≤ 800)
    C = "C"   # Dense to medium-dense sand or stiff clay (180 ≤ v_s,30 ≤ 360)
    D = "D"   # Loose to medium granular or soft to firm cohesive (v_s,30 < 180)
    E = "E"   # Surface alluvium over a much stiffer base (5-20 m thick)


class SpectrumType(str, Enum):
    TYPE_1 = "1"   # M_s > 5.5 (typical Mediterranean far-field)
    TYPE_2 = "2"   # M_s ≤ 5.5 (near-field, smaller events)


@dataclass(frozen=True)
class SpectrumParams:
    S: float
    T_B: float
    T_C: float
    T_D: float


# EN 1998-1 Table 3.2 (Type 1) and Table 3.3 (Type 2)
_TYPE_1: Dict[GroundType, SpectrumParams] = {
    GroundType.A: SpectrumParams(S=1.00, T_B=0.15, T_C=0.40, T_D=2.0),
    GroundType.B: SpectrumParams(S=1.20, T_B=0.15, T_C=0.50, T_D=2.0),
    GroundType.C: SpectrumParams(S=1.15, T_B=0.20, T_C=0.60, T_D=2.0),
    GroundType.D: SpectrumParams(S=1.35, T_B=0.20, T_C=0.80, T_D=2.0),
    GroundType.E: SpectrumParams(S=1.40, T_B=0.15, T_C=0.50, T_D=2.0),
}
_TYPE_2: Dict[GroundType, SpectrumParams] = {
    GroundType.A: SpectrumParams(S=1.00, T_B=0.05, T_C=0.25, T_D=1.2),
    GroundType.B: SpectrumParams(S=1.35, T_B=0.05, T_C=0.25, T_D=1.2),
    GroundType.C: SpectrumParams(S=1.50, T_B=0.10, T_C=0.25, T_D=1.2),
    GroundType.D: SpectrumParams(S=1.80, T_B=0.10, T_C=0.30, T_D=1.2),
    GroundType.E: SpectrumParams(S=1.60, T_B=0.05, T_C=0.25, T_D=1.2),
}


def get_spectrum_parameters(
    ground: GroundType, spectrum: SpectrumType = SpectrumType.TYPE_1,
) -> SpectrumParams:
    return (_TYPE_1 if spectrum == SpectrumType.TYPE_1 else _TYPE_2)[ground]


# ---------------------------------------------------------------------------
# Seismic-zone database (national annexes)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SeismicZone:
    """One location entry in the seismic-zone database."""

    country: str
    region: str        # e.g. "Granada", "Catania"
    a_gR: float        # reference peak ground acceleration ratio (a_gR / g)
    spectrum_type: SpectrumType = SpectrumType.TYPE_1
    notes: str = ""


# Spain — NCSE-02 mapping (subset of municipalities, illustrative). Real
# implementation should plug a complete CSV; this gives common cases.
_SPAIN_ZONES: List[SeismicZone] = [
    SeismicZone("ES", "Barcelona",   0.04, SpectrumType.TYPE_2),
    SeismicZone("ES", "Madrid",      0.04, SpectrumType.TYPE_2),
    SeismicZone("ES", "Valencia",    0.06, SpectrumType.TYPE_2),
    SeismicZone("ES", "Sevilla",     0.07, SpectrumType.TYPE_1),
    SeismicZone("ES", "Cádiz",       0.11, SpectrumType.TYPE_1),
    SeismicZone("ES", "Granada",     0.23, SpectrumType.TYPE_1),
    SeismicZone("ES", "Almería",     0.14, SpectrumType.TYPE_1),
    SeismicZone("ES", "Málaga",      0.12, SpectrumType.TYPE_1),
    SeismicZone("ES", "Murcia",      0.15, SpectrumType.TYPE_1),
    SeismicZone("ES", "Alicante",    0.14, SpectrumType.TYPE_1),
    SeismicZone("ES", "Bilbao",      0.04, SpectrumType.TYPE_2),
    SeismicZone("ES", "Pamplona",    0.07, SpectrumType.TYPE_2),
    SeismicZone("ES", "Zaragoza",    0.04, SpectrumType.TYPE_2),
    SeismicZone("ES", "Lorca",       0.20, SpectrumType.TYPE_1),
    SeismicZone("ES", "Melilla",     0.16, SpectrumType.TYPE_1),
]

# Italy (NTC) and France (PS92) hooks — add real values as needed
_ITALY_ZONES: List[SeismicZone] = [
    SeismicZone("IT", "Roma",         0.13, SpectrumType.TYPE_1),
    SeismicZone("IT", "Napoli",       0.17, SpectrumType.TYPE_1),
    SeismicZone("IT", "Milano",       0.05, SpectrumType.TYPE_2),
    SeismicZone("IT", "L'Aquila",     0.30, SpectrumType.TYPE_1),
    SeismicZone("IT", "Catania",      0.25, SpectrumType.TYPE_1),
]
_FRANCE_ZONES: List[SeismicZone] = [
    SeismicZone("FR", "Paris",        0.04, SpectrumType.TYPE_2),
    SeismicZone("FR", "Marseille",    0.16, SpectrumType.TYPE_2),
    SeismicZone("FR", "Nice",         0.16, SpectrumType.TYPE_2),
    SeismicZone("FR", "Strasbourg",   0.11, SpectrumType.TYPE_2),
]

SEISMIC_ZONES: Dict[str, List[SeismicZone]] = {
    "ES": _SPAIN_ZONES,
    "IT": _ITALY_ZONES,
    "FR": _FRANCE_ZONES,
}


def lookup_seismic_zone(country: str, region: str) -> SeismicZone:
    """Return the SeismicZone entry for a given country / region.

    Args:
        country: ISO 2-letter code ("ES", "IT", "FR").
        region:  city or region name (case-insensitive).
    """
    table = SEISMIC_ZONES.get(country.upper(), [])
    region_lc = region.strip().lower()
    for z in table:
        if z.region.lower() == region_lc:
            return z
    raise KeyError(f"Region '{region}' not found in {country.upper()} seismic zones. "
                   f"Available: {[z.region for z in table]}")


def list_zones(country: str) -> List[str]:
    """Return the list of region names available for a country."""
    return [z.region for z in SEISMIC_ZONES.get(country.upper(), [])]


# ---------------------------------------------------------------------------
# Importance classes and behaviour factor
# ---------------------------------------------------------------------------

class ImportanceClass(str, Enum):
    """EN 1998-1 §4.2.5 importance class → γ_I."""

    I = "I"      # Buildings of minor importance (γ_I = 0.8)
    II = "II"    # Ordinary buildings (γ_I = 1.0)
    III = "III"  # Important buildings (schools, halls) (γ_I = 1.2)
    IV = "IV"    # Vital infrastructure (γ_I = 1.4)


_GAMMA_I = {
    ImportanceClass.I: 0.8,
    ImportanceClass.II: 1.0,
    ImportanceClass.III: 1.2,
    ImportanceClass.IV: 1.4,
}


def importance_factor(cls: ImportanceClass) -> float:
    return _GAMMA_I[cls]


# ---------------------------------------------------------------------------
# Response spectrum
# ---------------------------------------------------------------------------

def elastic_response_spectrum(
    T_s: float,
    a_g_g: float,
    params: SpectrumParams,
    damping_xi: float = 0.05,
) -> float:
    """Horizontal elastic response spectrum S_e(T) (EN 1998-1 §3.2.2.2).

    Returns the spectral acceleration ratio S_e(T) / g.

    Args:
        T_s: structural period (s).
        a_g_g: design ground acceleration ratio  a_g · γ_I / g.
        params: SpectrumParams for the (ground × spectrum-type) combo.
        damping_xi: viscous damping ratio (default 0.05).
    """
    if a_g_g <= 0:
        return 0.0
    eta = max(math.sqrt(10.0 / (5.0 + 100.0 * damping_xi)), 0.55)
    a_g_S = a_g_g * params.S
    T = max(T_s, 0.0)
    if T <= params.T_B:
        # Linear increase from a_g·S (T=0) to a_g·S·η·2.5 at T_B
        return a_g_S * (1.0 + (T / params.T_B) * (eta * 2.5 - 1.0))
    if T <= params.T_C:
        return a_g_S * eta * 2.5
    if T <= params.T_D:
        return a_g_S * eta * 2.5 * (params.T_C / T)
    # T > T_D — far-period (linear in T_D / T²)
    return a_g_S * eta * 2.5 * (params.T_C * params.T_D / T ** 2)


def design_response_spectrum(
    T_s: float,
    a_g_g: float,
    params: SpectrumParams,
    behaviour_factor_q: float = 1.0,
    beta: float = 0.20,
) -> float:
    """Design response spectrum S_d(T) (EN 1998-1 §3.2.2.5).

    Args:
        a_g_g: design ground acceleration ratio (already multiplied by γ_I).
        behaviour_factor_q: structural behaviour factor (≥ 1.0).
        beta: lower-bound factor for the design spectrum (typically 0.20).
    """
    a_g_S = a_g_g * params.S
    T = max(T_s, 0.0)
    q = max(behaviour_factor_q, 1.0)
    if T <= params.T_B:
        return a_g_S * (2.0 / 3.0 + T / params.T_B * (2.5 / q - 2.0 / 3.0))
    if T <= params.T_C:
        return a_g_S * 2.5 / q
    if T <= params.T_D:
        val = a_g_S * 2.5 / q * (params.T_C / T)
        return max(val, beta * a_g_g)
    val = a_g_S * 2.5 / q * (params.T_C * params.T_D / T ** 2)
    return max(val, beta * a_g_g)


@dataclass
class DesignSpectrum:
    """Bundle the design spectrum + metadata for one location/structure."""

    country: str
    region: str
    ground_type: GroundType
    importance_class: ImportanceClass
    behaviour_factor_q: float
    a_gR_g: float
    gamma_I: float
    spectrum_params: SpectrumParams
    spectrum_type: SpectrumType

    @property
    def a_g_g(self) -> float:
        """Design ground acceleration ratio a_g · γ_I (g)."""
        return self.a_gR_g * self.gamma_I

    def S_e(self, T: float, damping_xi: float = 0.05) -> float:
        return elastic_response_spectrum(T, self.a_g_g,
                                         self.spectrum_params, damping_xi)

    def S_d(self, T: float, beta: float = 0.20) -> float:
        return design_response_spectrum(T, self.a_g_g, self.spectrum_params,
                                        self.behaviour_factor_q, beta)


def build_design_spectrum(
    country: str, region: str,
    ground_type: GroundType,
    importance_class: ImportanceClass = ImportanceClass.II,
    behaviour_factor_q: float = 1.0,
) -> DesignSpectrum:
    """Compose a `DesignSpectrum` from country / region / ground / importance."""
    zone = lookup_seismic_zone(country, region)
    params = get_spectrum_parameters(ground_type, zone.spectrum_type)
    return DesignSpectrum(
        country=zone.country, region=zone.region,
        ground_type=ground_type,
        importance_class=importance_class,
        behaviour_factor_q=behaviour_factor_q,
        a_gR_g=zone.a_gR,
        gamma_I=importance_factor(importance_class),
        spectrum_params=params,
        spectrum_type=zone.spectrum_type,
    )


__all__ = [
    "GroundType",
    "SpectrumType",
    "SpectrumParams",
    "get_spectrum_parameters",
    "SeismicZone",
    "SEISMIC_ZONES",
    "lookup_seismic_zone",
    "list_zones",
    "ImportanceClass",
    "importance_factor",
    "elastic_response_spectrum",
    "design_response_spectrum",
    "DesignSpectrum",
    "build_design_spectrum",
]
