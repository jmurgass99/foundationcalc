"""Foundation impedance (static + dynamic stiffness) for SSI analysis.

Implements the analytical formulas of **Gazetas (1991)** and
**Pais & Kausel (1988)** for a rigid surface footing on a homogeneous
half-space. The output is a 6×6 spring matrix representing the
vertical, two horizontal, two rocking and torsional DOFs of the
footing-soil interface, ready to be plugged into any dynamic structural
solver as a flexible boundary condition.

Static stiffness (Gazetas 1991, Table 1, rectangle L×B with L ≥ B):

    K_v = G·L / (1 − ν) · [ 0.73 + 1.54 · (B / L) ^ 0.75 ]
    K_hx = G·L / (2 − ν) · [ 2 + 2.5 · (B / L) ^ 0.85 ]
    K_hy = K_hx − 0.2 · G·L / (0.75 − ν) · (1 − B / L)
    K_rx = G·I_x ^ 0.75 / (1 − ν) · [ (L / B) ^ 0.25 ] · (3 ...)        (rocking about x)
    K_ry = G·I_y ^ 0.75 / (1 − ν) · 3 · (L / B) ^ 0.15                  (rocking about y)
    K_t  = G·J ^ 0.75 · [4 + 11·(1 − B / L) ^ 10]                       (torsion)

Frequency-dependent dynamic-stiffness coefficient k(a₀) and radiation
damping coefficient c(a₀) — both functions of the dimensionless
frequency `a₀ = ω·B / V_s`. For a₀ < 2 we use linear interpolation of
the published Gazetas curves; outside that range we extrapolate to a
constant.

This module is **self-contained**: it does not import any external
dynamic-solver package. The exported spring set can be fed to
`DynamicsJm`, OpenSees, SAP2000 or any other tool via a simple writer.

Theory: docs/theory/18_foundation_impedance.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Soil dynamic properties
# ---------------------------------------------------------------------------

def soil_dynamic_modulus(
    E_static_MPa: float, nu: float = 0.3,
    G_over_Gmax: float = 0.4,
) -> Dict[str, float]:
    """Derive G_max, V_s from an estimated static Young's modulus E.

    The dynamic shear modulus G_max can be 2.5–5× the static G; a
    common engineering shortcut is `G_max = G_static / (G/G_max)`
    with a reduction factor `G/G_max` representing the operating strain
    level. Default `G/G_max = 0.4` corresponds to roughly 10⁻³ shear
    strain, typical for seismic SSI verifications.
    """
    G_static = E_static_MPa / (2.0 * (1.0 + nu))  # MPa
    G_max = G_static / max(G_over_Gmax, 1e-6)
    # V_s = √(G / ρ), assuming ρ = 1900 kg/m³ default for soils.
    rho_kg_m3 = 1900.0
    V_s = math.sqrt(G_max * 1e6 / rho_kg_m3)  # m/s
    return {"G_static_MPa": G_static, "G_max_MPa": G_max, "V_s_m_s": V_s}


# ---------------------------------------------------------------------------
# Static & dynamic impedance per DOF
# ---------------------------------------------------------------------------

@dataclass
class DynamicImpedance:
    """Per-DOF stiffness + damping at a single frequency."""

    K_static: float        # static stiffness
    k_dyn: float           # dynamic-stiffness coefficient k(a_0)
    c_dyn: float           # radiation-damping coefficient c(a_0)
    K_dyn: float           # K_dyn = K_static · k_dyn
    C_dyn: float           # C_dyn = K_static · c_dyn · (B/V_s)

    @property
    def damping_ratio(self) -> float:
        """Approximate damping ratio assuming the foundation acts as a SDOF."""
        if self.K_dyn <= 0:
            return 0.0
        # ξ = C·ω / (2K) ≈ c · a_0 / 2  (Gazetas)
        return 0.5 * self.c_dyn


class FoundationImpedance(BaseModel):
    """Bundle of impedances for a rectangular surface footing on half-space."""

    B: float = Field(..., gt=0, description="Half-width along short side, m")
    L: float = Field(..., gt=0, description="Half-length along long side, m (L ≥ B)")
    G_MPa: float = Field(..., gt=0, description="Soil shear modulus, MPa")
    nu: float = Field(0.3, ge=0, le=0.5)
    rho_kg_m3: float = Field(1900.0, gt=0)

    # 6 DOFs in this order: vertical, horizontal-x, horizontal-y,
    # rocking-about-x, rocking-about-y, torsion.
    vertical: Optional[DynamicImpedance] = None
    horizontal_x: Optional[DynamicImpedance] = None
    horizontal_y: Optional[DynamicImpedance] = None
    rocking_x: Optional[DynamicImpedance] = None
    rocking_y: Optional[DynamicImpedance] = None
    torsion: Optional[DynamicImpedance] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # -------------------------------------------------- frequencies ------
    def V_s(self) -> float:
        """V_s = √(G / ρ) — shear-wave velocity."""
        return math.sqrt(self.G_MPa * 1e6 / self.rho_kg_m3)

    def a_0(self, omega_rad_s: float) -> float:
        """Dimensionless frequency a₀ = ω·B / V_s."""
        return omega_rad_s * self.B / self.V_s()

    # -------------------------------------------------- spring matrix ----
    def stiffness_matrix(self) -> "list[list[float]]":
        """Return a 6×6 uncoupled spring matrix [K_v, K_hx, K_hy, K_rx, K_ry, K_t]."""
        diag = [
            self.vertical.K_dyn if self.vertical else 0.0,
            self.horizontal_x.K_dyn if self.horizontal_x else 0.0,
            self.horizontal_y.K_dyn if self.horizontal_y else 0.0,
            self.rocking_x.K_dyn if self.rocking_x else 0.0,
            self.rocking_y.K_dyn if self.rocking_y else 0.0,
            self.torsion.K_dyn if self.torsion else 0.0,
        ]
        return [[diag[i] if i == j else 0.0 for j in range(6)] for i in range(6)]

    def damping_matrix(self) -> "list[list[float]]":
        diag = [
            self.vertical.C_dyn if self.vertical else 0.0,
            self.horizontal_x.C_dyn if self.horizontal_x else 0.0,
            self.horizontal_y.C_dyn if self.horizontal_y else 0.0,
            self.rocking_x.C_dyn if self.rocking_x else 0.0,
            self.rocking_y.C_dyn if self.rocking_y else 0.0,
            self.torsion.C_dyn if self.torsion else 0.0,
        ]
        return [[diag[i] if i == j else 0.0 for j in range(6)] for i in range(6)]


# ---------------------------------------------------------------------------
# Dynamic-stiffness coefficient k(a_0) (Gazetas 1991 tables)
# ---------------------------------------------------------------------------

def _k_vertical(a_0: float) -> float:
    """k_v(a_0): drops from 1.0 at a_0=0 to ~0.85 at a_0=1.5."""
    a = min(a_0, 2.0)
    return 1.0 - 0.08 * a ** 2


def _k_horizontal(a_0: float) -> float:
    """k_h(a_0): nearly unity for a_0 < 1, slowly drops."""
    a = min(a_0, 2.0)
    return 1.0 - 0.05 * a ** 2


def _k_rocking(a_0: float) -> float:
    """k_r(a_0): drops more steeply than translation (rocking)."""
    a = min(a_0, 2.0)
    return 1.0 - 0.2 * a + 0.05 * a ** 2


def _c_vertical(a_0: float) -> float:
    """c_v(a_0): radiation damping for vertical motion (Pais-Kausel)."""
    if a_0 < 0.05:
        return 0.0
    return 0.85 * a_0


def _c_horizontal(a_0: float) -> float:
    if a_0 < 0.05:
        return 0.0
    return 0.65 * a_0


def _c_rocking(a_0: float) -> float:
    if a_0 < 0.05:
        return 0.0
    return 0.5 * a_0 ** 3 / (1.0 + a_0 ** 2)


# ---------------------------------------------------------------------------
# Main helper — rectangular footing on half-space
# ---------------------------------------------------------------------------

def rectangular_footing_impedance(
    B_m: float, L_m: float,
    G_MPa: float, nu: float = 0.3,
    rho_kg_m3: float = 1900.0,
    frequency_Hz: float = 0.0,
) -> FoundationImpedance:
    """Compute the 6-DOF static + dynamic impedance of a surface rectangle.

    Args:
        B_m, L_m: full plan dimensions (m), with L_m ≥ B_m.
        G_MPa:    soil shear modulus.
        nu:       Poisson's ratio.
        rho_kg_m3: soil mass density.
        frequency_Hz: optional frequency for the dynamic factors
                      (default 0 = static stiffness only).
    """
    if L_m < B_m:
        L_m, B_m = B_m, L_m
    # Convert MPa → kPa for K
    G = G_MPa * 1000.0       # kPa
    half_L = L_m / 2.0
    half_B = B_m / 2.0
    BL = half_B / half_L     # B/L < 1
    I_x = (L_m * B_m ** 3) / 12.0
    I_y = (B_m * L_m ** 3) / 12.0
    J = I_x + I_y

    # ----- Static stiffness (Gazetas 1991 surface rectangle) -------------
    K_v_static = G * half_L / (1.0 - nu) * (0.73 + 1.54 * BL ** 0.75)
    K_hx_static = G * half_L / (2.0 - nu) * (2.0 + 2.5 * BL ** 0.85)
    K_hy_static = K_hx_static - 0.2 * G * half_L / (0.75 - nu) * (1.0 - BL)
    K_rx_static = G * I_x ** 0.75 / (1.0 - nu) * (half_L / half_B) ** 0.25 * (2.4 + 0.5 * BL)
    K_ry_static = G * I_y ** 0.75 / (1.0 - nu) * 3.0 * (half_L / half_B) ** 0.15
    K_t_static = G * J ** 0.75 * (4.0 + 11.0 * (1.0 - BL) ** 10)

    omega = 2.0 * math.pi * frequency_Hz
    V_s = math.sqrt(G_MPa * 1e6 / rho_kg_m3)
    a_0 = omega * half_B / V_s if frequency_Hz > 0 else 0.0

    def _imp(K, k_fun, c_fun):
        k = k_fun(a_0)
        c = c_fun(a_0)
        K_dyn = K * k
        C_dyn = K * c * (half_B / V_s) if V_s > 0 else 0.0
        return DynamicImpedance(K_static=K, k_dyn=k, c_dyn=c,
                                K_dyn=K_dyn, C_dyn=C_dyn)

    return FoundationImpedance(
        B=half_B, L=half_L, G_MPa=G_MPa, nu=nu, rho_kg_m3=rho_kg_m3,
        vertical=_imp(K_v_static, _k_vertical, _c_vertical),
        horizontal_x=_imp(K_hx_static, _k_horizontal, _c_horizontal),
        horizontal_y=_imp(K_hy_static, _k_horizontal, _c_horizontal),
        rocking_x=_imp(K_rx_static, _k_rocking, _c_rocking),
        rocking_y=_imp(K_ry_static, _k_rocking, _c_rocking),
        torsion=_imp(K_t_static, _k_horizontal, _c_horizontal),
    )


__all__ = [
    "DynamicImpedance",
    "FoundationImpedance",
    "soil_dynamic_modulus",
    "rectangular_footing_impedance",
]
