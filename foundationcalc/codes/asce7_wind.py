"""ASCE 7-22 wind loads — Directional Procedure (Chapter 27) simplified.

Computes velocity pressure qz, exposure coefficient Kz (Table 26.10-1),
topographic factor Kzt, directionality factor Kd, and the design pressure
p = qz · G · Cp − qi · GCpi for low-/mid-rise enclosed buildings.

Units: m, m/s, Pa (SI).

Theory: ASCE 7-22 Cap. 26-27; docs/theory/asce7_wind.md (planned).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Exposure(str, Enum):
    """ASCE 7 exposure categories (Table 26.7-1)."""

    B = "B"  # urban / suburban with closely-spaced obstructions
    C = "C"  # open terrain with scattered obstructions
    D = "D"  # flat unobstructed (coastal)


# zg (m) and α exponent — Table 26.10-1
_ZG_ALPHA = {
    Exposure.B: (366.0, 7.0),
    Exposure.C: (274.0, 9.5),
    Exposure.D: (213.0, 11.5),
}


def Kz(z: float, exposure: Exposure = Exposure.C) -> float:
    """Velocity pressure exposure coefficient (ASCE 7-22 Eq. 26.10-1).

    Kz = 2.01 · (z/zg)^(2/α) for z ≥ 4.6 m, else Kz at 4.6 m.
    """
    z = max(z, 4.6)
    zg, alpha = _ZG_ALPHA[exposure]
    return 2.01 * (z / zg) ** (2.0 / alpha)


class WindPressureResult(BaseModel):
    """Design wind pressures from the Directional Procedure (MWFRS)."""

    qz: float = Field(..., description="Velocity pressure (Pa)")
    p_wall_wind: float = Field(..., description="Windward wall pressure (Pa)")
    p_wall_lee: float = Field(..., description="Leeward wall pressure (Pa)")
    p_roof: float = Field(..., description="Roof pressure (Pa)")
    Kz: float
    Kd: float
    Kzt: float
    Ke: float
    G: float
    Cp_ww: float
    Cp_lw: float
    Cp_roof: float
    GCpi: float


def design_wind_pressure(
    *,
    V: float,
    z: float,
    exposure: Exposure = Exposure.C,
    Kzt: float = 1.0,
    Kd: float = 0.85,
    Ke: float = 1.0,
    G: float = 0.85,
    Cp_ww: float = 0.8,
    Cp_lw: float = -0.5,
    Cp_roof: float = -0.7,
    GCpi: float = 0.18,
    rho_air: float = 1.225,
) -> WindPressureResult:
    """Design wind pressure (ASCE 7-22 §27.3.2).

    qz = 0.5 · ρ · V² · Kz · Kzt · Kd · Ke    (V in m/s, result in Pa).
    p  = qz · G · Cp − qi · GCpi              (enclosed building: qi = qh).

    Args:
        V: basic wind speed (m/s).
        z: height of the point evaluated (m).
        exposure: B / C / D.
        Kzt, Kd, Ke: topographic, directionality, ground-elevation factors.
        G: gust factor (0.85 rigid).
        Cp_ww, Cp_lw, Cp_roof: external pressure coefficients.
        GCpi: internal pressure coefficient (±0.18 enclosed, ±0.55 open).
        rho_air: air density (kg/m³).
    """
    kz = Kz(z, exposure)
    qz = 0.5 * rho_air * V * V * kz * Kzt * Kd * Ke
    p_ww = qz * G * Cp_ww - qz * GCpi
    p_lw = qz * G * Cp_lw - qz * GCpi
    p_r = qz * G * Cp_roof - qz * GCpi
    return WindPressureResult(
        qz=qz, p_wall_wind=p_ww, p_wall_lee=p_lw, p_roof=p_r,
        Kz=kz, Kd=Kd, Kzt=Kzt, Ke=Ke,
        G=G, Cp_ww=Cp_ww, Cp_lw=Cp_lw, Cp_roof=Cp_roof, GCpi=GCpi,
    )


__all__ = ["Exposure", "Kz", "WindPressureResult", "design_wind_pressure"]
