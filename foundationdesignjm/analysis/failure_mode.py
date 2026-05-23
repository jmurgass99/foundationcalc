"""Failure-mode classification for shallow foundations (Vesic 1973).

Vesic introduced the rigidity index `I_r` to distinguish three failure
modes:

- **General shear failure** — dense cohesionless soil or stiff undrained
  clay. A well-defined slip surface reaches the ground surface.
  Use the standard N_q, N_γ unreduced. Mode for `I_r ≥ I_rc`.
- **Local shear failure** — medium dense to loose sand. Slip surface
  develops partially. Reduction factors ζ < 1 are applied.
- **Punching shear failure** — loose sand or soft clay. The footing
  punches downward without a defined slip surface; large settlements.
  Same reduction approach but more pronounced.

Rigidity index:
    I_r  = G / (c' + q' · tan φ')                with G = E / (2 (1 + ν))
    I_rc = 0.5 · exp[ 2.85 · cot(45° − φ'/2) ]
    I_rr = I_r / (1 + I_r · ε_v)                  if volumetric strain ε_v > 0

Reduction factors (Vesic 1973):
    ζ_q = ζ_γ = exp{ −4.4 tan φ + [3.07 sin φ · log10(2 I_r)] / (1 + sin φ) }
    ζ_c = ζ_q − (1 − ζ_q) / (N_q tan φ)            for φ > 0
    ζ_c = 0.32 + 0.12 · B/L + 0.6 · log10(I_r)     for φ = 0

Theory: docs/theory/13_failure_modes.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FailureMode(str, Enum):
    GENERAL_SHEAR = "general_shear"
    LOCAL_SHEAR = "local_shear"
    PUNCHING_SHEAR = "punching_shear"


@dataclass
class FailureModeResult:
    mode: FailureMode
    I_r: float
    I_rc: float
    zeta_q: float
    zeta_c: float
    zeta_gamma: float


def critical_rigidity_index(phi_deg: float) -> float:
    """I_rc — boundary between general and local/punching modes (Vesic 1973)."""
    phi_rad = math.radians(phi_deg)
    if phi_rad < 1e-9:
        return 13.0  # standard reference for undrained
    return 0.5 * math.exp(2.85 / math.tan(math.radians(45.0 - phi_deg / 2.0)))


def rigidity_index(
    E_kPa: float, nu: float,
    c_prime_kPa: float, phi_deg: float,
    q_prime_kPa: float,
) -> float:
    """I_r = G / (c' + q'·tan φ').

    Args:
        E_kPa: Young's modulus.
        nu: Poisson's ratio.
        c_prime_kPa: effective cohesion.
        phi_deg: friction angle.
        q_prime_kPa: effective overburden at founding depth.
    """
    G = E_kPa / (2.0 * (1.0 + nu))
    phi_rad = math.radians(phi_deg)
    denom = c_prime_kPa + q_prime_kPa * math.tan(phi_rad)
    if denom <= 1e-9:
        return float("inf")
    return G / denom


def vesic_reduction_factors(
    phi_deg: float, I_r: float, B_m: float, L_m: float, Nq: float,
) -> tuple[float, float, float]:
    """(ζ_c, ζ_q, ζ_γ) Vesic 1973 reduction for local / punching shear."""
    phi_rad = math.radians(phi_deg)
    if phi_rad < 1e-9:
        # Undrained
        zeta_c = 0.32 + 0.12 * (B_m / max(L_m, B_m)) + 0.6 * math.log10(max(I_r, 1.01))
        zeta_c = min(zeta_c, 1.0)
        return zeta_c, 1.0, 1.0
    # Drained
    arg = -4.4 * math.tan(phi_rad) + (
        3.07 * math.sin(phi_rad) * math.log10(2.0 * max(I_r, 1.01))
        / (1.0 + math.sin(phi_rad))
    )
    zeta_q = math.exp(arg)
    zeta_q = min(zeta_q, 1.0)
    zeta_gamma = zeta_q
    if Nq > 1.0:
        zeta_c = zeta_q - (1.0 - zeta_q) / (Nq * math.tan(phi_rad))
    else:
        zeta_c = zeta_q
    zeta_c = min(zeta_c, 1.0)
    return max(zeta_c, 0.0), max(zeta_q, 0.0), max(zeta_gamma, 0.0)


def classify_failure_mode(
    E_kPa: float, nu: float,
    c_prime_kPa: float, phi_deg: float,
    q_prime_kPa: float,
    B_m: float, L_m: float, Nq: float,
    relative_density_pct: Optional[float] = None,
) -> FailureModeResult:
    """Run full Vesic classification + return reduction factors.

    Use `relative_density_pct` to distinguish *local* (40-70 %) from
    *punching* (< 40 %) shear within the I_r < I_rc regime; if None,
    fall back to general/local based on I_r alone.
    """
    I_r = rigidity_index(E_kPa, nu, c_prime_kPa, phi_deg, q_prime_kPa)
    I_rc = critical_rigidity_index(phi_deg)

    if I_r >= I_rc:
        return FailureModeResult(
            mode=FailureMode.GENERAL_SHEAR, I_r=I_r, I_rc=I_rc,
            zeta_q=1.0, zeta_c=1.0, zeta_gamma=1.0,
        )

    zeta_c, zeta_q, zeta_gamma = vesic_reduction_factors(phi_deg, I_r, B_m, L_m, Nq)

    # Distinguish local vs punching on relative density (if provided)
    if relative_density_pct is not None and relative_density_pct < 35.0:
        mode = FailureMode.PUNCHING_SHEAR
    else:
        mode = FailureMode.LOCAL_SHEAR

    return FailureModeResult(
        mode=mode, I_r=I_r, I_rc=I_rc,
        zeta_q=zeta_q, zeta_c=zeta_c, zeta_gamma=zeta_gamma,
    )


__all__ = [
    "FailureMode",
    "FailureModeResult",
    "critical_rigidity_index",
    "rigidity_index",
    "vesic_reduction_factors",
    "classify_failure_mode",
]
