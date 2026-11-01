"""1-D consolidation analysis (Terzaghi).

Used to compute the time-dependent settlement of clay layers under a
footing-induced stress increment. Implements:

- **Terzaghi 1-D consolidation** — the degree of consolidation U(T_v)
  from the dimensionless time factor `T_v = c_v · t / H_dr²`.
- **Consolidation settlement** `s_c` from compression index `C_c` /
  recompression index `C_r` and initial void ratio.
- **Time-settlement curve** s(t).

The implementation follows Terzaghi (1925) and Holtz & Kovacs (2010).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence

import numpy as np
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# U(T_v) — degree of consolidation
# ---------------------------------------------------------------------------

def U_from_Tv(T_v: float, max_terms: int = 30) -> float:
    """Terzaghi 1-D degree of consolidation U as a function of the
    dimensionless time factor T_v.

    Exact series solution:
        U = 1 − Σ_{m=0}^∞ 2/M² · exp(−M² · T_v)
    with M = π(2m + 1)/2.
    """
    if T_v <= 0:
        return 0.0
    if T_v > 2.0:
        return 1.0
    s = 0.0
    for m in range(max_terms):
        M = math.pi * (2 * m + 1) / 2.0
        s += 2.0 / M ** 2 * math.exp(-M ** 2 * T_v)
    return min(max(1.0 - s, 0.0), 1.0)


def Tv_from_U(U: float) -> float:
    """Inverse: T_v from a target U (Casagrande approximation)."""
    U = min(max(U, 0.0), 0.999)
    if U < 0.6:
        return math.pi / 4.0 * U ** 2
    # Taylor: T_v = -0.933·log10(1 − U) − 0.085
    return -0.933 * math.log10(1.0 - U) - 0.085


# ---------------------------------------------------------------------------
# Consolidation settlement
# ---------------------------------------------------------------------------

class ClayLayer(BaseModel):
    """A clay layer for consolidation analysis."""

    thickness_m: float = Field(..., gt=0)
    e0: float = Field(..., gt=0, description="Initial void ratio")
    C_c: float = Field(..., gt=0, description="Compression index")
    C_r: float = Field(0.0, ge=0, description="Recompression index (default 0)")
    OCR: float = Field(1.0, ge=1.0, description="Overconsolidation ratio")
    sigma_p_kPa: float = Field(..., gt=0, description="Preconsolidation pressure (kPa)")
    c_v_m2_per_year: float = Field(..., gt=0, description="Coefficient of consolidation (m²/year)")
    two_way_drainage: bool = Field(True, description="True = drainage at top and bottom")

    @property
    def H_dr_m(self) -> float:
        """Maximum drainage path length."""
        return self.thickness_m / 2.0 if self.two_way_drainage else self.thickness_m


def settlement_consolidation(
    layer: ClayLayer,
    sigma_0_kPa: float,
    delta_sigma_kPa: float,
) -> float:
    """Final 1-D consolidation settlement of one clay layer.

    Three cases depending on whether the load passes the preconsolidation:
    1. Always normally consolidated (σ_0 ≥ σ'_p):
            s_c = H · C_c / (1 + e_0) · log10((σ_0 + Δσ) / σ_0)
    2. Stays overconsolidated (σ_0 + Δσ ≤ σ'_p):
            s_c = H · C_r / (1 + e_0) · log10((σ_0 + Δσ) / σ_0)
    3. Crosses the preconsolidation (σ_0 ≤ σ'_p ≤ σ_0 + Δσ):
            s_c = H · C_r / (1 + e_0) · log10(σ'_p / σ_0)
                + H · C_c / (1 + e_0) · log10((σ_0 + Δσ) / σ'_p)
    """
    if sigma_0_kPa <= 0 or delta_sigma_kPa <= 0:
        return 0.0
    H = layer.thickness_m
    e_factor = (1.0 + layer.e0)
    sigma_final = sigma_0_kPa + delta_sigma_kPa
    sigma_p = layer.sigma_p_kPa

    if sigma_0_kPa >= sigma_p:
        return H * layer.C_c / e_factor * math.log10(sigma_final / sigma_0_kPa)
    if sigma_final <= sigma_p:
        return H * layer.C_r / e_factor * math.log10(sigma_final / sigma_0_kPa)
    s_oc = H * layer.C_r / e_factor * math.log10(sigma_p / sigma_0_kPa)
    s_nc = H * layer.C_c / e_factor * math.log10(sigma_final / sigma_p)
    return s_oc + s_nc


def time_to_consolidation(
    layer: ClayLayer, U_target: float,
) -> float:
    """Years until the degree of consolidation reaches `U_target`."""
    Tv = Tv_from_U(U_target)
    return Tv * layer.H_dr_m ** 2 / layer.c_v_m2_per_year


# ---------------------------------------------------------------------------
# Time-settlement curve
# ---------------------------------------------------------------------------

@dataclass
class ConsolidationCurve:
    times_years: np.ndarray
    U: np.ndarray
    settlement_m: np.ndarray


def consolidation_curve(
    layer: ClayLayer,
    s_final_m: float,
    t_max_years: float,
    n_points: int = 50,
) -> ConsolidationCurve:
    """Return the time-settlement curve for one clay layer."""
    times = np.linspace(0.001, t_max_years, n_points)
    Hdr = layer.H_dr_m
    cv = layer.c_v_m2_per_year
    U_vals = np.array([U_from_Tv(cv * t / Hdr ** 2) for t in times])
    s_vals = U_vals * s_final_m
    return ConsolidationCurve(times_years=times, U=U_vals, settlement_m=s_vals)


# ---------------------------------------------------------------------------
# Elastic (immediate) settlement of a footing on cohesionless soil
# ---------------------------------------------------------------------------

def elastic_settlement_rectangle(
    q_kPa: float, B_m: float, L_m: float,
    E_kPa: float, nu: float = 0.3,
    shape_factor_I_s: float = None,
    location: str = "centre",
) -> float:
    """Elastic settlement of a flexible rectangle on a homogeneous half-space.

    s = q · B · (1 − ν²) / E · I_s,   B = short side, m = L/B ≥ 1.

    Default I_s (Steinbrenner/Schleicher, infinite depth; Bowles 1996):
        corner:  I_s = (1/π)·[m·ln((1 + √(1+m²))/m) + ln(m + √(1+m²))]
        centre:  I_s = 2 · corner value  (four B/2 × L/2 corners superposed)
    Square: 0.561 (corner) / 1.122 (centre); L/B = 2: 0.766 / 1.532.

    DEFECTO CORREGIDO (1.1.0): los dos términos tenían intercambiados el
    factor m y los argumentos de los logaritmos. En cuadrada coincidía con el
    centro (1,12), pero con L/B = 2 daba 2,14 en lugar de 1,53 (+40 %) y con
    L/B = 5, 7,49 en lugar de 2,10. Comprobado contra la integración
    numérica de la solución de Boussinesq (`tests/test_fix_110_*`).
    """
    if shape_factor_I_s is None:
        Bs = max(min(L_m, B_m), 1e-9)
        m = max(L_m, B_m) / Bs
        s1 = math.sqrt(1.0 + m * m)
        I_s_corner = (1.0 / math.pi) * (
            m * math.log((1.0 + s1) / m) + math.log(m + s1)
        )
        if location == "corner":
            I_s = I_s_corner
        elif location == "centre":
            I_s = 2.0 * I_s_corner
        else:
            raise ValueError("location debe ser 'centre' o 'corner'")
        B_m = Bs
    else:
        I_s = shape_factor_I_s
    return q_kPa * B_m * (1.0 - nu ** 2) / E_kPa * I_s


__all__ = [
    "U_from_Tv",
    "Tv_from_U",
    "ClayLayer",
    "settlement_consolidation",
    "time_to_consolidation",
    "ConsolidationCurve",
    "consolidation_curve",
    "elastic_settlement_rectangle",
]
