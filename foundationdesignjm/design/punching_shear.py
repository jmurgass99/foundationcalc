"""Punching shear verification per EN 1992-1-1 §6.4 (EC2).

Theory: docs/theory/03_shallow_foundations.md §3.4.1.
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field

from ..core.geometry import Column, RectangularFoundation


class PunchingShearResult(BaseModel):
    u1: float = Field(..., description="Critical perimeter at 2·d (m)")
    d_eff: float = Field(..., description="Effective depth (m)")
    F_sd: float = Field(..., description="Net punching force F_sd (kN)")
    F_sd_ef: float = Field(..., description="F_sd_ef = β · F_sd (kN)")
    tau_sd: float = Field(..., description="τ_sd (kPa = kN/m²)")
    tau_rd: float = Field(..., description="τ_Rd,c (kPa)")
    beta: float
    xi: float
    rho_l: float
    utilization: float
    applicable: bool = Field(
        True,
        description=(
            "True si el perímetro crítico a 2d cae DENTRO de la planta de la zapata. "
            "Si es False (zapata compacta), F_sd se anula geométricamente y la "
            "verificación a 2d NO es concluyente: EC2 §6.4.4(2) exige comprobar "
            "perímetros a distancia a < 2d. Un utilization=0 con applicable=False "
            "NO es un PASS."
        ),
    )

    @property
    def is_ok(self) -> bool:
        return self.utilization <= 1.0

    @property
    def verdict(self) -> str:
        """Veredicto honesto: nunca presenta como PASS un chequeo no aplicable."""
        if not self.applicable:
            return "NO_APLICABLE_2D"
        return "PASS" if self.is_ok else "FAIL"


def punching_shear_check(
    foundation: RectangularFoundation,
    column: Column,
    N_sd_kN: float,
    fck_MPa: float,
    rho_x: float,
    rho_y: float,
    d_eff_m: float,
    gamma_c: float = 1.5,
) -> PunchingShearResult:
    """EC2 punching shear at 2·d from the column face.

    Args:
        foundation: footing geometry.
        column: column geometry & position.
        N_sd_kN: design axial action at column base (kN).
        fck_MPa: characteristic cylinder strength (MPa).
        rho_x, rho_y: reinforcement ratios in two directions (e.g. 0.005).
        d_eff_m: effective depth of footing (m).
        gamma_c: concrete partial factor.
    """
    c1 = column.length / 1000.0
    c2 = column.width / 1000.0
    d = d_eff_m

    # Critical perimeter at distance 2·d from the column face
    u1 = 2.0 * c1 + 2.0 * c2 + 4.0 * math.pi * d

    # Effective area enclosed by u1 (rectangle + half-circles at the four corners)
    A_u1 = c1 * c2 + math.pi * (2.0 * d) ** 2 + 4.0 * d * c1 + 4.0 * d * c2

    # Net punching force — deduct the uplift inside u1
    A_footing = foundation.area
    if A_footing <= 0:
        raise ValueError("Footing area must be positive.")
    F_sd = N_sd_kN * (A_footing - A_u1) / A_footing
    F_sd = max(F_sd, 0.0)

    beta = column.punching_beta(foundation)
    F_sd_ef = beta * F_sd

    tau_sd = F_sd_ef / (u1 * d) if u1 * d > 0 else 0.0

    # EC2 τ_Rd,c
    xi = 1.0 + math.sqrt(200.0 / (d * 1000.0))
    xi = min(xi, 2.0)
    rho_l = min(math.sqrt(max(rho_x, 0.0) * max(rho_y, 0.0)), 0.02)
    tau_rd_MPa = (0.18 / gamma_c) * xi * (100.0 * rho_l * fck_MPa) ** (1.0 / 3.0)
    tau_rd_kPa = tau_rd_MPa * 1000.0  # MPa → kPa

    utilization = tau_sd / tau_rd_kPa if tau_rd_kPa > 0 else float("inf")

    # Zapata compacta: si el area encerrada por u1 alcanza o excede la planta,
    # la deduccion de reaccion anula F_sd y el chequeo a 2d pierde sentido
    # (EC2 6.4.4(2): comprobar perimetros a < 2d). Se marca NO aplicable.
    applicable = A_u1 < A_footing

    return PunchingShearResult(
        u1=u1,
        d_eff=d,
        F_sd=F_sd,
        F_sd_ef=F_sd_ef,
        tau_sd=tau_sd,
        tau_rd=tau_rd_kPa,
        beta=beta,
        xi=xi,
        rho_l=rho_l,
        utilization=utilization,
        applicable=applicable,
    )
