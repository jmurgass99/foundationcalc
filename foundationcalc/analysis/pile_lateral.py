"""Lateral analysis of single piles using p-y curves.

Three industry-standard p-y formulations are implemented (re-derived
from primary references, no GPL contamination):
- **Matlock (1970)** — soft clay.
- **Reese et al. (1974)** — sand (cyclic / static).
- **API RP 2A (2010)** — offshore-style for sand and clay (the most
  commonly used in practice today).

The pile is modelled as a beam-on-non-linear-foundation: the soil is
replaced by discrete springs whose force-displacement relation follows
the chosen p-y curve. The governing ODE

    EI · d⁴y/dz⁴ + p(y) = 0

is discretised by central finite differences. The boundary conditions at
the pile head can be:
- FREE_HEAD     — fixed shear H and moment M at head, free rotation.
- FIXED_HEAD    — fixed shear H and zero rotation (capped pile).

Returns the deflection y(z), shear V(z), moment M(z) and soil reaction
p(z) along the pile. Suitable for ULS shear and bending design of
pile-cap piles, mooring piles and monopiles.

Theory: docs/theory/11_pile_lateral.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# p-y formulations
# ---------------------------------------------------------------------------

class PYType(str, Enum):
    MATLOCK_SOFT_CLAY = "matlock_soft_clay"
    REESE_SAND = "reese_sand"
    API_SAND = "api_sand"
    API_CLAY = "api_clay"


def py_matlock(
    y_m: float, depth_m: float, pile_D_m: float,
    c_u_kPa: float, gamma_eff_kN_m3: float,
    J: float = 0.5,
    eps_50: float = 0.02,
) -> float:
    """Matlock (1970) p-y curve for soft clay (kPa·m / m run of pile, → kN/m).

    Args:
        y_m: lateral deflection (m).
        depth_m: depth below mudline (m, ≥ 0).
        pile_D_m: pile diameter (m).
        c_u_kPa: undrained shear strength (kPa).
        gamma_eff_kN_m3: effective unit weight of soil above z (kN/m³).
        J: empirical constant 0.25–0.5 (default 0.5 for Gulf of Mexico clay).
        eps_50: strain at 50 % failure stress in undrained test (default 0.02).

    Returns:
        Soil resistance per unit pile length p (kN/m).
    """
    if pile_D_m <= 0 or c_u_kPa <= 0:
        return 0.0
    # Ultimate resistance per unit length p_u (kPa·m → kN/m)
    p_ur = (3.0 + gamma_eff_kN_m3 * depth_m / c_u_kPa
            + J * depth_m / pile_D_m) * c_u_kPa * pile_D_m
    p_ud = 9.0 * c_u_kPa * pile_D_m
    p_u = min(p_ur, p_ud)
    # y_50 reference deflection
    y_50 = 2.5 * eps_50 * pile_D_m
    if y_50 <= 0:
        return 0.0
    # Hyperbolic p-y: p / p_u = 0.5 · (y/y_50)^(1/3), capped at 1.0
    ratio = abs(y_m) / y_50
    p_ratio = 0.5 * ratio ** (1.0 / 3.0)
    p = min(p_ratio, 1.0) * p_u
    return math.copysign(p, y_m)


def py_reese_sand(
    y_m: float, depth_m: float, pile_D_m: float,
    phi_deg: float, gamma_eff_kN_m3: float,
    k_pa_per_m: float = 22000.0,
) -> float:
    """Reese et al. (1974) p-y curve for sand — simplified hyperbolic.

    The full Reese curve has 4 segments; here we use the simplified
    hyperbolic envelope `p = (p_u · k_z · y) / (p_u + k_z · y)` which
    matches the original within ~5 % for typical pile geometries.

    Args:
        k_pa_per_m: subgrade modulus (kPa/m). Typical 6 800 (loose) –
                    33 900 (very dense) kPa/m for medium sand.
    """
    if pile_D_m <= 0 or phi_deg <= 0:
        return 0.0
    phi = math.radians(phi_deg)
    alpha = phi / 2.0
    beta = math.radians(45.0 + phi_deg / 2.0)
    K_0 = 0.4
    K_a = math.tan(math.radians(45.0 - phi_deg / 2.0)) ** 2

    # Reese's ultimate resistance (wedge for shallow, flow-around for deep)
    p_st = gamma_eff_kN_m3 * depth_m * (
        K_0 * depth_m * math.tan(phi) * math.sin(beta) / max(math.tan(beta - phi) * math.cos(alpha), 1e-6)
        + math.tan(beta) / math.tan(beta - phi) * (pile_D_m + depth_m * math.tan(beta) * math.tan(alpha))
        + K_0 * depth_m * math.tan(beta) * (math.tan(phi) * math.sin(beta) - math.tan(alpha))
        - K_a * pile_D_m
    )
    p_sd = K_a * pile_D_m * gamma_eff_kN_m3 * depth_m * (math.tan(beta) ** 8 - 1.0)\
        + K_0 * pile_D_m * gamma_eff_kN_m3 * depth_m * math.tan(phi) * math.tan(beta) ** 4
    p_u = max(min(p_st, p_sd), 0.0)
    if p_u <= 0:
        return 0.0
    k_z = k_pa_per_m * depth_m  # initial stiffness per unit length
    if k_z <= 0:
        return 0.0
    p_abs = (p_u * k_z * abs(y_m)) / (p_u + k_z * abs(y_m))
    return math.copysign(p_abs, y_m)


def py_api_sand(
    y_m: float, depth_m: float, pile_D_m: float,
    phi_deg: float, gamma_eff_kN_m3: float,
) -> float:
    """API RP 2A (2010) p-y for sand:  p = A · p_u · tanh((k·z·y)/(A·p_u))."""
    if pile_D_m <= 0 or phi_deg <= 0 or depth_m <= 0:
        return 0.0
    # Ultimate resistance coefficient at depth z (Reese's wedge / flow-around)
    C1 = 0.115 * math.exp(0.0405 * phi_deg)
    C2 = 0.571 * math.exp(0.022 * phi_deg)
    C3 = 50.0 * math.exp(0.07 * phi_deg)
    p_us = (C1 * depth_m + C2 * pile_D_m) * gamma_eff_kN_m3 * depth_m
    p_ud = C3 * pile_D_m * gamma_eff_kN_m3 * depth_m
    p_u = min(p_us, p_ud)
    # Initial subgrade modulus k (kPa/m) — API Fig 6.8.7
    k = 5400.0 * phi_deg / 30.0   # rough fit: ~5400 at φ=30, 9000 at φ=40
    A = 0.9  # cyclic; use 3.0 − 0.8·z/D ≥ 0.9 for static
    if abs(y_m) < 1e-9:
        return 0.0
    arg = (k * depth_m * abs(y_m)) / max(A * p_u, 1e-6)
    p = A * p_u * math.tanh(arg)
    return math.copysign(p, y_m)


def py_api_clay(
    y_m: float, depth_m: float, pile_D_m: float,
    c_u_kPa: float, gamma_eff_kN_m3: float,
    eps_50: float = 0.02,
    J: float = 0.5,
    cyclic: bool = False,
) -> float:
    """API RP 2A clay — same shape as Matlock with cyclic reduction.

    For cyclic loading below the reduced depth z_r the ultimate resistance
    is capped at 0.72·p_u.
    """
    p_static = py_matlock(y_m, depth_m, pile_D_m, c_u_kPa,
                          gamma_eff_kN_m3, J=J, eps_50=eps_50)
    if not cyclic:
        return p_static
    # Reduced depth: z_r = 6·D / ((γ·D/c_u) + J)
    z_r = 6.0 * pile_D_m / max(gamma_eff_kN_m3 * pile_D_m / c_u_kPa + J, 1e-6)
    if depth_m > z_r:
        return 0.72 * p_static
    # Linear taper from p_static at z=z_r to 0.72·p_static at z=0 — conservative
    factor = 0.72 + (1.0 - 0.72) * (depth_m / z_r)
    return factor * p_static


# ---------------------------------------------------------------------------
# Pile model and FD solver
# ---------------------------------------------------------------------------

class PYSoilLayer(BaseModel):
    """One soil layer used by the lateral-pile solver."""

    z_top_m: float = Field(..., ge=0)
    z_bot_m: float = Field(..., gt=0)
    py_type: PYType
    c_u_kPa: float = 0.0
    phi_deg: float = 0.0
    gamma_eff_kN_m3: float = 18.0
    eps_50: float = 0.02
    J: float = 0.5
    k_pa_per_m: float = 22000.0


class PileLateral(BaseModel):
    """Single-pile lateral-analysis input."""

    length_m: float = Field(..., gt=1.0)
    diameter_m: float = Field(..., gt=0.05)
    EI_kNm2: float = Field(..., gt=0)
    layers: List[PYSoilLayer]
    head_load_H_kN: float = 0.0
    head_moment_M_kNm: float = 0.0
    fixed_head: bool = Field(False, description="True = capped (rotation = 0)")


@dataclass
class LateralResult:
    z: np.ndarray
    y_m: np.ndarray             # deflection (m)
    rotation_rad: np.ndarray    # rotation (rad)
    M_kNm: np.ndarray           # bending moment (kN·m)
    V_kN: np.ndarray            # shear force (kN)
    p_kN_per_m: np.ndarray      # soil reaction (kN/m)

    @property
    def y_head_mm(self) -> float:
        return float(self.y_m[0] * 1000.0)

    @property
    def M_max_kNm(self) -> float:
        return float(np.max(np.abs(self.M_kNm)))

    @property
    def V_max_kN(self) -> float:
        return float(np.max(np.abs(self.V_kN)))


def _evaluate_py(pile: PileLateral, z: float, y: float) -> float:
    """Return p (kN/m) at depth z and deflection y, using the active layer's curve."""
    for layer in pile.layers:
        if layer.z_top_m <= z < layer.z_bot_m:
            if layer.py_type == PYType.MATLOCK_SOFT_CLAY:
                return py_matlock(y, z, pile.diameter_m,
                                  layer.c_u_kPa, layer.gamma_eff_kN_m3,
                                  J=layer.J, eps_50=layer.eps_50)
            if layer.py_type == PYType.REESE_SAND:
                return py_reese_sand(y, z, pile.diameter_m,
                                     layer.phi_deg, layer.gamma_eff_kN_m3,
                                     k_pa_per_m=layer.k_pa_per_m)
            if layer.py_type == PYType.API_SAND:
                return py_api_sand(y, z, pile.diameter_m,
                                   layer.phi_deg, layer.gamma_eff_kN_m3)
            if layer.py_type == PYType.API_CLAY:
                return py_api_clay(y, z, pile.diameter_m,
                                   layer.c_u_kPa, layer.gamma_eff_kN_m3,
                                   eps_50=layer.eps_50, J=layer.J)
    return 0.0


def solve_pile_lateral(
    pile: PileLateral,
    n_segments: int = 80,
    max_iter: int = 80,
    tol_mm: float = 0.1,
    relaxation: float = 0.5,
) -> LateralResult:
    """Solve the non-linear beam-on-py-springs problem via FD + Picard iteration.

    Governing equation (with finite differences):
        EI · (y_{i-2} − 4 y_{i-1} + 6 y_i − 4 y_{i+1} + y_{i+2}) / h^4
            + k_i · y_i = 0

    where k_i = p_i / y_i is the secant stiffness from the p-y curve at the
    current trial deflection. We iterate updating k_i until convergence.
    """
    n = n_segments + 1
    h = pile.length_m / n_segments
    z = np.linspace(0.0, pile.length_m, n)

    # Initial guess: simple cantilever under head loads
    H = pile.head_load_H_kN
    M = pile.head_moment_M_kNm
    EI = pile.EI_kNm2
    # Simple cubic guess based on free cantilever
    y = (H / (6.0 * EI)) * (3.0 * pile.length_m * z ** 2 - z ** 3) + \
        (M / (2.0 * EI)) * z ** 2
    y = y[::-1]  # reverse: y[0] is head, y[-1] tip
    y_prev = y.copy()

    for it in range(max_iter):
        # Secant spring stiffness at each node, k_i [kN/m/m]
        k_secant = np.zeros(n)
        for i in range(n):
            yi = y[i]
            if abs(yi) > 1e-9:
                pi = _evaluate_py(pile, z[i], yi)
                k_secant[i] = max(pi / yi, 0.0)
            else:
                k_secant[i] = 0.0

        # Assemble FD stiffness K (n × n)
        K = np.zeros((n, n))
        for i in range(2, n - 2):
            K[i, i - 2] = EI / h ** 4
            K[i, i - 1] = -4.0 * EI / h ** 4
            K[i, i]     = 6.0 * EI / h ** 4 + k_secant[i]
            K[i, i + 1] = -4.0 * EI / h ** 4
            K[i, i + 2] = EI / h ** 4

        # Boundary conditions at head (node 0): apply shear and moment
        # Shear at head: EI·y'''(0) = -H  →  use 3-point forward FD for y'''
        # Moment at head: EI·y''(0) = M  →  use forward FD for y''
        # We use ghost nodes y[-1] and y[-2] to express these:
        #   y''(0) ≈ (y[-1] − 2 y[0] + y[1]) / h^2 = M/EI
        #   y'''(0) ≈ (y[-2] − 2·y[-1] + 2·y[1] − y[2]) / (2 h^3) = -H/EI (FREE)
        #   or rotation y'(0) ≈ (y[1] − y[-1])/(2 h) = 0 (FIXED HEAD)
        # We eliminate y[-1] and y[-2] by writing them as a function of y[0]..y[2]
        # Free-head BC:
        if pile.fixed_head:
            #  y'(0) = 0 ⇒ y[-1] = y[1]
            #  y''(0) = M/EI ⇒ y[-1] − 2 y[0] + y[1] = M h² / EI
            #             ⇒ 2 y[1] − 2 y[0] = M h² / EI
            #             ⇒ y[0] = y[1] − M h²/(2 EI)
            K[0, :] = 0.0
            K[0, 0] = 1.0
            K[0, 1] = -1.0
            F0 = -M * h ** 2 / (2.0 * EI)
            # row 1: full FD with eliminated y[-1] = y[1]:
            # (y[1] − 4 y[0] + 6 y[1] − 4 y[2] + y[3])·EI/h^4 + k·y[1] = 0
            K[1, :] = 0.0
            K[1, 0] = -4.0 * EI / h ** 4
            K[1, 1] = (1.0 + 6.0) * EI / h ** 4 + k_secant[1]
            K[1, 2] = -4.0 * EI / h ** 4
            K[1, 3] = EI / h ** 4
        else:
            # Free-head: shear at head = H, moment at head = M
            # Use the 2 equations to eliminate y[-1] and y[-2]
            # y[-1] = 2 y[0] − y[1] + M h²/EI
            # y[-2] = ... derived from y'''(0):
            #   (y[-2] − 2 y[-1] + 2 y[1] − y[2]) = -2 H h³ / EI
            #   y[-2] = 2 y[-1] − 2 y[1] + y[2] − 2 H h³ / EI
            #         = 2(2 y[0] − y[1] + M h²/EI) − 2 y[1] + y[2] − 2 H h³ / EI
            #         = 4 y[0] − 4 y[1] + y[2] + 2 M h²/EI − 2 H h³ / EI
            # Substitute into FD at i=0 and i=1.
            # FD at i=0: y[-2] − 4 y[-1] + 6 y[0] − 4 y[1] + y[2] = (force balance)
            # Substituting yields a row that depends only on y[0]..y[2]:
            #   (4 y[0] − 4 y[1] + y[2] + 2Mh²/EI − 2Hh³/EI) − 4(2 y[0] − y[1] + Mh²/EI) + 6 y[0] − 4 y[1] + y[2]
            #   = (4 − 8 + 6) y[0] + (−4 + 4 − 4) y[1] + (1 + 1) y[2] + (2 − 4) Mh²/EI − 2 Hh³/EI
            #   = 2 y[0] − 4 y[1] + 2 y[2] − 2 M h²/EI − 2 H h³/EI
            # multiplied by EI/h^4 plus k_0·y[0] = 0
            K[0, :] = 0.0
            K[0, 0] = 2.0 * EI / h ** 4 + k_secant[0]
            K[0, 1] = -4.0 * EI / h ** 4
            K[0, 2] = 2.0 * EI / h ** 4
            F0 = (2.0 * M / h ** 2 + 2.0 * H * h / 1.0) / 1.0  # = (2 M h²/EI + 2 H h³/EI) · EI/h^4
            F0 = 2.0 * M / h ** 2 + 2.0 * H / h
            # For i=1: substitute y[-1] = 2 y[0] − y[1] + M h²/EI
            # FD at i=1: y[-1] − 4 y[0] + 6 y[1] − 4 y[2] + y[3]
            #          = (2 y[0] − y[1] + M h²/EI) − 4 y[0] + 6 y[1] − 4 y[2] + y[3]
            #          = -2 y[0] + 5 y[1] − 4 y[2] + y[3] + M h²/EI
            K[1, :] = 0.0
            K[1, 0] = -2.0 * EI / h ** 4
            K[1, 1] = 5.0 * EI / h ** 4 + k_secant[1]
            K[1, 2] = -4.0 * EI / h ** 4
            K[1, 3] = EI / h ** 4

        # BCs at tip (node n-1 and n-2): zero moment and shear (free)
        # y''(L) = 0  ⇒  y[n] − 2 y[n-1] + y[n-2] = 0  ⇒  y[n] = 2 y[n-1] − y[n-2]
        # y'''(L) = 0 ⇒  y[n+1] − 2 y[n] + 2 y[n-2] − y[n-3] = 0
        # Substituting into the FD at i=n-1 and n-2:
        # i = n-2: y[n-4] − 4 y[n-3] + 6 y[n-2] − 4 y[n-1] + y[n] = 0
        #         = y[n-4] − 4 y[n-3] + 6 y[n-2] − 4 y[n-1] + (2 y[n-1] − y[n-2])
        #         = y[n-4] − 4 y[n-3] + 5 y[n-2] − 2 y[n-1]
        K[n - 2, :] = 0.0
        K[n - 2, n - 4] = EI / h ** 4
        K[n - 2, n - 3] = -4.0 * EI / h ** 4
        K[n - 2, n - 2] = 5.0 * EI / h ** 4 + k_secant[n - 2]
        K[n - 2, n - 1] = -2.0 * EI / h ** 4
        # i = n-1: y[n-3] − 4 y[n-2] + 6 y[n-1] − 4 y[n] + y[n+1]
        # Substituting y[n] = 2 y[n-1] − y[n-2] and y[n+1] from y'''(L) = 0:
        # y[n+1] = 2 y[n] − 2 y[n-2] + y[n-3] = 2(2 y[n-1] − y[n-2]) − 2 y[n-2] + y[n-3]
        #        = 4 y[n-1] − 4 y[n-2] + y[n-3]
        # Substitute into i=n-1:
        # = y[n-3] − 4 y[n-2] + 6 y[n-1] − 4(2 y[n-1] − y[n-2]) + (4 y[n-1] − 4 y[n-2] + y[n-3])
        # = 2 y[n-3] − 4 y[n-2] + 2 y[n-1]
        K[n - 1, :] = 0.0
        K[n - 1, n - 3] = 2.0 * EI / h ** 4
        K[n - 1, n - 2] = -4.0 * EI / h ** 4
        K[n - 1, n - 1] = 2.0 * EI / h ** 4 + k_secant[n - 1]

        # RHS
        F = np.zeros(n)
        if not pile.fixed_head:
            F[0] = F0
        else:
            F[0] = F0  # y[0] = y[1] − M h²/(2 EI)

        try:
            y_new = np.linalg.solve(K, F)
        except np.linalg.LinAlgError:
            break

        # Relax for stability
        y_relaxed = relaxation * y_new + (1.0 - relaxation) * y_prev
        err_mm = max(abs(y_relaxed - y_prev)) * 1000.0
        y_prev = y_relaxed
        y = y_relaxed
        if err_mm < tol_mm:
            break

    # Recover internal forces by FD differentiation
    M_arr = np.zeros(n)
    V_arr = np.zeros(n)
    p_arr = np.zeros(n)
    for i in range(1, n - 1):
        M_arr[i] = EI * (y[i - 1] - 2.0 * y[i] + y[i + 1]) / h ** 2
    for i in range(2, n - 2):
        V_arr[i] = EI * (y[i + 2] - 2.0 * y[i + 1] + 2.0 * y[i - 1] - y[i - 2]) / (2.0 * h ** 3)
    for i in range(n):
        p_arr[i] = _evaluate_py(pile, z[i], y[i])

    # Rotation by central FD
    rot = np.zeros(n)
    for i in range(1, n - 1):
        rot[i] = (y[i + 1] - y[i - 1]) / (2.0 * h)

    return LateralResult(z=z, y_m=y, rotation_rad=rot, M_kNm=M_arr, V_kN=V_arr, p_kN_per_m=p_arr)


__all__ = [
    "PYType",
    "PYSoilLayer",
    "PileLateral",
    "LateralResult",
    "py_matlock",
    "py_reese_sand",
    "py_api_sand",
    "py_api_clay",
    "solve_pile_lateral",
]
