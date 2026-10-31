"""Servicios de análisis sísmico geotécnico."""
from __future__ import annotations
from dataclasses import dataclass
import math

from ..exceptions import CodeError


@dataclass(frozen=True)
class MononobeOkabeInput:
    H: float              # altura muro (m)
    gamma: float          # γ suelo (kN/m³)
    phi: float            # ángulo fricción (°)
    delta: float = 0.0    # ángulo fricción muro-suelo (°)
    beta: float = 0.0     # inclinación talud detrás muro (°)
    alpha: float = 0.0    # inclinación pared muro (°)
    kh: float = 0.15      # coef. sísmico horizontal
    kv: float = 0.0       # coef. sísmico vertical


@dataclass(frozen=True)
class MononobeOkabeResult:
    K_AE: float           # coef. empuje activo dinámico
    P_AE: float           # empuje activo dinámico (kN/m)
    theta: float          # ángulo de inercia sísmica (°)
    notes: list[str]


def mononobe_okabe_thrust(inp: MononobeOkabeInput) -> MononobeOkabeResult:
    """Empuje sísmico activo según Mononobe-Okabe (EC8-5 Annex E)."""
    phi_r = math.radians(inp.phi)
    delta_r = math.radians(inp.delta)
    beta_r = math.radians(inp.beta)
    alpha_r = math.radians(inp.alpha)
    theta = math.atan(inp.kh / (1 - inp.kv))
    theta_deg = math.degrees(theta)

    # Verificación de aplicabilidad
    if phi_r - theta - beta_r <= 0:
        raise CodeError(
            f"Mononobe-Okabe no aplicable: φ-θ-β = "
            f"{inp.phi - theta_deg - inp.beta:.1f}° debe ser > 0"
        )

    numerator = math.cos(phi_r - theta - alpha_r) ** 2
    den_a = math.cos(theta) * math.cos(alpha_r) ** 2 * math.cos(alpha_r + delta_r + theta)
    sqrt_term = math.sqrt(
        max(0.0,
            (math.sin(phi_r + delta_r) * math.sin(phi_r - theta - beta_r))
            / (math.cos(alpha_r + delta_r + theta) * math.cos(beta_r - alpha_r))
        )
    )
    den_b = (1 + sqrt_term) ** 2
    K_AE = numerator / (den_a * den_b)
    P_AE = 0.5 * (1 - inp.kv) * inp.gamma * inp.H ** 2 * K_AE
    return MononobeOkabeResult(
        K_AE=K_AE, P_AE=P_AE, theta=theta_deg,
        notes=[
            f"K_AE = {K_AE:.4f}",
            f"P_AE = {P_AE:.1f} kN/m",
            f"θ = {theta_deg:.2f}° (ángulo de inercia)",
        ],
    )
