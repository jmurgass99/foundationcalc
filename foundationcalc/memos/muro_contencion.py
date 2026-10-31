"""Memoria handcalcs - Muro de contencion (Coulomb + Rankine)."""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin, tan


@dataclass(frozen=True)
class MuroContencionInput:
    H_m: float
    gamma_kN_m3: float = 18.0
    phi_deg: float = 30.0
    delta_deg: float = 20.0
    beta_deg: float = 0.0       # backfill slope
    theta_deg: float = 0.0      # wall inclination from vertical
    cohesion_kPa: float = 0.0
    q_surch_kPa: float = 0.0


@dataclass(frozen=True)
class MuroContencionResult:
    Ka_rankine: float
    Ka_coulomb: float
    Ea_rankine_kN_m: float
    Ea_coulomb_kN_m: float
    z_app_m: float
    markdown: str


def rankine_ka(phi_deg: float, beta_deg: float = 0.0) -> float:
    phi = radians(phi_deg)
    beta = radians(beta_deg)
    if abs(beta) < 1e-9:
        return (1 - sin(phi)) / (1 + sin(phi))
    cb = cos(beta)
    num = cb - (cb * cb - cos(phi) ** 2) ** 0.5
    den = cb + (cb * cb - cos(phi) ** 2) ** 0.5
    return cb * num / den


def coulomb_ka(phi_deg: float, delta_deg: float, beta_deg: float = 0.0,
               theta_deg: float = 0.0) -> float:
    phi = radians(phi_deg)
    delta = radians(delta_deg)
    beta = radians(beta_deg)
    theta = radians(theta_deg)
    num = (cos(phi - theta)) ** 2
    a = sin(phi + delta) * sin(phi - beta)
    b = cos(theta - beta) * cos(theta + delta)
    inner = 1 + (a / b) ** 0.5
    den = (cos(theta)) ** 2 * cos(theta + delta) * inner ** 2
    return num / den


def memoria_muro(inp: MuroContencionInput) -> MuroContencionResult:
    Kar = rankine_ka(inp.phi_deg, inp.beta_deg)
    Kac = coulomb_ka(inp.phi_deg, inp.delta_deg, inp.beta_deg, inp.theta_deg)
    Ea_r = 0.5 * Kar * inp.gamma_kN_m3 * inp.H_m ** 2 + Kar * inp.q_surch_kPa * inp.H_m
    Ea_c = 0.5 * Kac * inp.gamma_kN_m3 * inp.H_m ** 2 + Kac * inp.q_surch_kPa * inp.H_m
    z_app = inp.H_m / 3.0
    md = (
        f"# Muro de Contencion (H={inp.H_m:.2f} m)\n\n"
        f"## Coeficientes\n- Ka (Rankine) = {Kar:.4f}\n- Ka (Coulomb) = {Kac:.4f}\n\n"
        f"## Empujes (kN/m)\n- Rankine: Ea = 0.5*Ka*g*H^2 + Ka*q*H = {Ea_r:.2f}\n"
        f"- Coulomb: Ea = {Ea_c:.2f}\n\n"
        f"## Punto de aplicacion\n- z = H/3 = {z_app:.2f} m\n"
    )
    return MuroContencionResult(Kar, Kac, Ea_r, Ea_c, z_app, md)


__all__ = ["MuroContencionInput", "MuroContencionResult",
           "rankine_ka", "coulomb_ka", "memoria_muro"]
