"""Boussinesq elastic stress increments under shallow foundations.

Implemented closed-form solutions (Boussinesq 1885, Newmark 1935 chart
formulas):

- `boussinesq_point_load_dsigma_z(P, x, y, z)`        — point load.
- `boussinesq_line_load_dsigma_z(q, x, z)`            — line load.
- `boussinesq_strip_load_dsigma_z(q, B, x, z)`        — flexible strip.
- `boussinesq_circular_load_centre(q, R, z)`          — flexible circle, centre.
- `boussinesq_rect_corner(q, B, L, z)`                — flexible rectangle,
                                                       below the corner (Newmark).
- `boussinesq_rect_centre(q, B, L, z)`                — flexible rectangle,
                                                       below the centre.
- `dsigma_z_at_depth_below_rect_footing(...)`         — convenience helper.

These integrals are used by `analysis.settlement` to compute the elastic
and consolidation settlement of footings on layered ground.

Theory: docs/theory/12_stress_distribution.md.
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Single-load Boussinesq
# ---------------------------------------------------------------------------

def boussinesq_point_load_dsigma_z(
    P_kN: float, x_m: float, y_m: float, z_m: float,
) -> float:
    """Vertical stress increment Δσ_z from a vertical point load P at the surface.

    Boussinesq (1885):
        Δσ_z = (3·P) / (2·π·z²) · (z²/r²)^(5/2)         with r² = x² + y² + z²
    """
    if z_m <= 0:
        raise ValueError("z must be > 0.")
    r2 = x_m ** 2 + y_m ** 2 + z_m ** 2
    return 3.0 * P_kN * z_m ** 3 / (2.0 * math.pi * r2 ** 2.5)


def boussinesq_line_load_dsigma_z(q_kN_per_m: float, x_m: float, z_m: float) -> float:
    """Δσ_z under a line load (q per unit length running in the y direction):

        Δσ_z = (2·q / π) · z³ / (x² + z²)²
    """
    if z_m <= 0:
        return 0.0
    return 2.0 * q_kN_per_m * z_m ** 3 / (math.pi * (x_m ** 2 + z_m ** 2) ** 2)


def boussinesq_strip_load_dsigma_z(
    q_kPa: float, B_m: float, x_m: float, z_m: float,
) -> float:
    """Δσ_z under a flexible strip of width B and uniform pressure q.

    `x` is measured from the centreline of the strip. Closed form
    (Holtz & Kovacs 2010, eq. 9.4):

        Δσ_z = (q / π) · [α + sin α · cos(α + 2 β)]

    where α = θ1 − θ2 is the angle subtended by the strip at the point and β
    is the angle from the vertical to the near edge, θ2 (θ1, θ2: angles from
    the vertical to the edges at x + a and x − a), so that α + 2β = θ1 + θ2.

    DEFECTO CORREGIDO (1.1.0): se tomaba β = (θ1 + θ2)/2, que da
    cos(2·θ1) en lugar de cos(θ1 + θ2). Bajo el eje de una zapata corrida de
    2 m a z = 2 m salía 0,448·q frente a 0,550·q (−18,5 %), y bajo el borde
    0,25·q frente a 0,409·q. Comprobado contra la integración numérica de
    cargas lineales (`tests/test_fix_110_*`).
    """
    if z_m <= 0:
        return 0.0
    a = B_m / 2.0
    # Angles at the point (x, z) looking up at the strip edges (−a, 0) and (a, 0)
    theta_1 = math.atan2(x_m + a, z_m)
    theta_2 = math.atan2(x_m - a, z_m)
    alpha = theta_1 - theta_2
    return q_kPa / math.pi * (alpha + math.sin(alpha) * math.cos(theta_1 + theta_2))


def boussinesq_circular_load_centre(q_kPa: float, R_m: float, z_m: float) -> float:
    """Δσ_z at depth z directly under the CENTRE of a flexible circle of radius R.

        Δσ_z = q · (1 − 1 / [1 + (R/z)²]^(3/2))
    """
    if z_m <= 0:
        return q_kPa
    return q_kPa * (1.0 - 1.0 / (1.0 + (R_m / z_m) ** 2) ** 1.5)


# ---------------------------------------------------------------------------
# Newmark / Steinbrenner — rectangle
# ---------------------------------------------------------------------------

def newmark_influence_factor(B_m: float, L_m: float, z_m: float) -> float:
    """Newmark (1935) influence factor I for the CORNER of a flexible rectangle.

    I depends on the dimensionless ratios m = B/z, n = L/z. The closed-form:

        I = 1 / (4 π) · [
              (2 m n √(m² + n² + 1)) / (m² + n² + m² n² + 1) · (m² + n² + 2) / (m² + n² + 1)
            + arctan( 2 m n √(m² + n² + 1) / (m² + n² − m² n² + 1) )
          ]

    The arctan must be > 0; when the denominator is negative we add π.
    """
    if z_m <= 0:
        return 0.25
    m = B_m / z_m
    n = L_m / z_m
    A = m ** 2 + n ** 2 + 1.0
    B2 = m * m * n * n
    num1 = 2.0 * m * n * math.sqrt(A)
    den1 = A + B2
    term1 = num1 / den1 * (A + 1.0) / A
    num2 = num1
    den2 = A - B2
    if den2 > 0:
        ang = math.atan(num2 / den2)
    else:
        ang = math.atan(num2 / den2) + math.pi
    return (term1 + ang) / (4.0 * math.pi)


def boussinesq_rect_corner(q_kPa: float, B_m: float, L_m: float, z_m: float) -> float:
    """Δσ_z below the corner of a flexible rectangle B × L at depth z."""
    return q_kPa * newmark_influence_factor(B_m, L_m, z_m)


def boussinesq_rect_centre(q_kPa: float, B_m: float, L_m: float, z_m: float) -> float:
    """Δσ_z below the centre of a flexible rectangle B × L (4 quadrants)."""
    return 4.0 * boussinesq_rect_corner(q_kPa, B_m / 2.0, L_m / 2.0, z_m)


def boussinesq_rect_point(
    q_kPa: float, B_m: float, L_m: float, z_m: float,
    x_m: float = 0.0, y_m: float = 0.0,
) -> float:
    """Δσ_z at depth z below an arbitrary point under a flexible rectangle.

    Uses superposition of the corner-influence rectangles. `(x, y)` is
    measured from the centre of the footing; the rectangle is B (x-dir)
    by L (y-dir). The point is assumed inside the footing — for points
    outside, the same superposition with negative areas applies.
    """
    half_B = B_m / 2.0
    half_L = L_m / 2.0
    # The four rectangles from the point to each corner
    b1 = half_B + x_m
    b2 = half_B - x_m
    l1 = half_L + y_m
    l2 = half_L - y_m
    rects = [(b1, l1), (b1, l2), (b2, l1), (b2, l2)]
    total = 0.0
    for B_i, L_i in rects:
        if B_i <= 0 or L_i <= 0:
            continue
        total += newmark_influence_factor(B_i, L_i, z_m)
    return q_kPa * total


# ---------------------------------------------------------------------------
# Convenience helper for footings
# ---------------------------------------------------------------------------

def dsigma_z_below_footing_centre(
    q_kPa: float, B_m: float, L_m: float, z_below_footing_m: float,
) -> float:
    """Wrapper: Δσ_z at depth z directly under the centre of a B × L footing."""
    return boussinesq_rect_centre(q_kPa, B_m, L_m, z_below_footing_m)


def dsigma_z_array_centre(
    q_kPa: float, B_m: float, L_m: float, z_values_m: list,
) -> list:
    """Vector version: Δσ_z at every z in `z_values_m`."""
    return [dsigma_z_below_footing_centre(q_kPa, B_m, L_m, z) for z in z_values_m]


__all__ = [
    "boussinesq_point_load_dsigma_z",
    "boussinesq_line_load_dsigma_z",
    "boussinesq_strip_load_dsigma_z",
    "boussinesq_circular_load_centre",
    "newmark_influence_factor",
    "boussinesq_rect_corner",
    "boussinesq_rect_centre",
    "boussinesq_rect_point",
    "dsigma_z_below_footing_centre",
    "dsigma_z_array_centre",
]
