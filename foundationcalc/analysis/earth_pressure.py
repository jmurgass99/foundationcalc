"""Lateral earth pressure coefficients: at-rest, Rankine, Coulomb.

All angles in degrees unless suffixed with `_rad`.
Theory: docs/theory/06_retaining_walls.md.
"""

from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel, Field


class PressureState(str, Enum):
    AT_REST = "at_rest"
    ACTIVE = "active"
    PASSIVE = "passive"


class EarthPressureResult(BaseModel):
    """Bundle of K, total horizontal thrust P, and lever arm to the wall toe."""

    state: PressureState
    coefficient_K: float
    thrust_P: float = Field(description="Total horizontal earth thrust (kN/m run)")
    overturning_moment: float = Field(description="Moment about wall toe (kN·m/m)")
    point_of_application_z: float = Field(description="Height above toe (m)")


# ---------------------------------------------------------------------------
# Coefficients
# ---------------------------------------------------------------------------

def K0(phi_deg: float, OCR: float = 1.0) -> float:
    """At-rest coefficient (Jaky / Mayne–Kulhawy)."""
    sin_phi = math.sin(math.radians(phi_deg))
    return (1.0 - sin_phi) * (OCR ** sin_phi)


def Ka_rankine(phi_deg: float) -> float:
    return math.tan(math.radians(45.0 - phi_deg / 2.0)) ** 2


def Kp_rankine(phi_deg: float) -> float:
    return math.tan(math.radians(45.0 + phi_deg / 2.0)) ** 2


def Ka_rankine_inclined(phi_deg: float, alpha_deg: float = 0.0) -> float:
    """Rankine active coefficient for a backfill inclined α (cohesionless).

        K_a = cos α · [cos α − √(cos²α − cos²φ)] / [cos α + √(cos²α − cos²φ)]

    The thrust acts parallel to the backfill surface; valid for |α| ≤ φ.
    For α = 0 it reduces to tan²(45° − φ/2).
    """
    if abs(alpha_deg) > phi_deg + 1e-9:
        raise ValueError(
            f"Rankine con talud: |α| = {abs(alpha_deg):g}° > φ = {phi_deg:g}°, "
            "el relleno no es estable y la fórmula no aplica."
        )
    ca = math.cos(math.radians(alpha_deg))
    root = math.sqrt(max(ca * ca - math.cos(math.radians(phi_deg)) ** 2, 0.0))
    return ca * (ca - root) / (ca + root)


def Ka_coulomb(
    phi_deg: float,
    delta_deg: float = 0.0,
    beta_deg: float = 90.0,
    alpha_deg: float = 0.0,
) -> float:
    """Coulomb's active earth-pressure coefficient.

    Args:
        phi_deg:   soil friction angle φ'.
        delta_deg: wall-soil friction angle δ' (positive when wall tends to slide up).
        beta_deg:  back-face inclination from horizontal (90° = vertical wall).
        alpha_deg: backfill slope angle from horizontal.
    """
    phi = math.radians(phi_deg)
    delta = math.radians(delta_deg)
    beta = math.radians(beta_deg)
    alpha = math.radians(alpha_deg)

    numerator = math.sin(beta + phi) ** 2
    sub = (
        math.sin(phi + delta) * math.sin(phi - alpha)
        / max(math.sin(beta - delta) * math.sin(alpha + beta), 1e-12)
    )
    sub = max(sub, 0.0)  # avoid sqrt of negative for steep alpha
    denominator = (
        math.sin(beta) ** 2
        * math.sin(beta - delta)
        * (1.0 + math.sqrt(sub)) ** 2
    )
    return numerator / max(denominator, 1e-12)


def Kp_coulomb(
    phi_deg: float,
    delta_deg: float = 0.0,
    beta_deg: float = 90.0,
    alpha_deg: float = 0.0,
) -> float:
    """Coulomb's passive earth-pressure coefficient."""
    phi = math.radians(phi_deg)
    delta = math.radians(delta_deg)
    beta = math.radians(beta_deg)
    alpha = math.radians(alpha_deg)

    numerator = math.sin(beta - phi) ** 2
    sub = (
        math.sin(phi + delta) * math.sin(phi + alpha)
        / max(math.sin(beta + delta) * math.sin(beta + alpha), 1e-12)
    )
    sub = max(sub, 0.0)
    denominator = (
        math.sin(beta) ** 2
        * math.sin(beta + delta)
        * (1.0 - math.sqrt(sub)) ** 2
    )
    return numerator / max(denominator, 1e-12)


# ---------------------------------------------------------------------------
# Tension crack and thrusts
# ---------------------------------------------------------------------------

def tension_crack_depth(c_prime: float, gamma: float, K_a: float) -> float:
    """Depth z_c of the tension crack in the active state.

    z_c = 2·c' / (γ · √K_a)
    """
    if c_prime <= 0:
        return 0.0
    return 2.0 * c_prime / (gamma * math.sqrt(max(K_a, 1e-12)))


def active_thrust(
    H: float,
    gamma: float,
    phi_deg: float,
    c_prime: float = 0.0,
    surcharge_q: float = 0.0,
    use_coulomb: bool = False,
    delta_deg: float = 0.0,
    beta_deg: float = 90.0,
    alpha_deg: float = 0.0,
) -> EarthPressureResult:
    """Total horizontal active thrust P_a per metre run on a wall of height H.

    P_a = (1/2) · K_a · γ · H² + K_a · q · H − 2·c'·√K_a · H
    """
    Ka = (
        Ka_coulomb(phi_deg, delta_deg, beta_deg, alpha_deg)
        if use_coulomb
        else Ka_rankine(phi_deg)
    )

    P_earth = 0.5 * Ka * gamma * H ** 2
    P_surcharge = Ka * surcharge_q * H
    P_cohesion = -2.0 * c_prime * math.sqrt(max(Ka, 1e-12)) * H
    P = P_earth + P_surcharge + max(P_cohesion, -P_earth)

    # Lever arm to toe — earth triangular at H/3, surcharge rectangular at H/2
    M_earth = P_earth * H / 3.0
    M_surcharge = P_surcharge * H / 2.0
    M_total = M_earth + M_surcharge
    z = M_total / P if P > 0 else 0.0

    return EarthPressureResult(
        state=PressureState.ACTIVE,
        coefficient_K=Ka,
        thrust_P=P,
        overturning_moment=M_total,
        point_of_application_z=z,
    )


def passive_thrust(
    H: float,
    gamma: float,
    phi_deg: float,
    c_prime: float = 0.0,
    use_coulomb: bool = False,
    delta_deg: float = 0.0,
    beta_deg: float = 90.0,
    alpha_deg: float = 0.0,
) -> EarthPressureResult:
    """Total horizontal passive thrust P_p per metre run."""
    Kp = (
        Kp_coulomb(phi_deg, delta_deg, beta_deg, alpha_deg)
        if use_coulomb
        else Kp_rankine(phi_deg)
    )

    P_earth = 0.5 * Kp * gamma * H ** 2
    P_cohesion = 2.0 * c_prime * math.sqrt(Kp) * H
    P = P_earth + P_cohesion

    M_earth = P_earth * H / 3.0
    M_cohesion = P_cohesion * H / 2.0
    M_total = M_earth + M_cohesion
    z = M_total / P if P > 0 else 0.0

    return EarthPressureResult(
        state=PressureState.PASSIVE,
        coefficient_K=Kp,
        thrust_P=P,
        overturning_moment=M_total,
        point_of_application_z=z,
    )


def at_rest_thrust(
    H: float,
    gamma: float,
    phi_deg: float,
    OCR: float = 1.0,
    surcharge_q: float = 0.0,
) -> EarthPressureResult:
    """At-rest thrust on a non-yielding wall (e.g. basement wall)."""
    K0v = K0(phi_deg, OCR)
    P_earth = 0.5 * K0v * gamma * H ** 2
    P_surcharge = K0v * surcharge_q * H
    P = P_earth + P_surcharge

    M_earth = P_earth * H / 3.0
    M_surcharge = P_surcharge * H / 2.0
    M_total = M_earth + M_surcharge
    z = M_total / P if P > 0 else 0.0

    return EarthPressureResult(
        state=PressureState.AT_REST,
        coefficient_K=K0v,
        thrust_P=P,
        overturning_moment=M_total,
        point_of_application_z=z,
    )


def heel_min_width_for_rankine(h: float, phi_deg: float) -> float:
    """Minimum heel width so that a Rankine zone forms above it:

        b_min = h · tan(45° − φ'/2)
    """
    return h * math.tan(math.radians(45.0 - phi_deg / 2.0))
