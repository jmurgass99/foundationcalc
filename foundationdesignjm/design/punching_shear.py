"""Punching shear verification per EN 1992-1-1 §6.4 (EC2).

Theory: docs/theory/03_shallow_foundations.md §3.4.1.
Includes perimeter reduction for compact footings where a <= 2d per EC2 §6.4.4(2).
"""
from __future__ import annotations
import math
from typing import Optional
import numpy as np
from pydantic import BaseModel, Field
from ..core.geometry import Column, RectangularFoundation

class PunchingShearResult(BaseModel):
    u1: float = Field(..., description='Control perimeter at 2·d or critical distance a (m)')
    d_eff: float = Field(..., description='Effective depth (m)')
    F_sd: float = Field(..., description='Net punching force F_sd (kN)')
    F_sd_ef: float = Field(..., description='F_sd_ef = β · F_sd (kN)')
    tau_sd: float = Field(..., description='Acting shear stress τ_sd (kPa = kN/m²)')
    tau_rd: float = Field(..., description='Base shear resistance τ_Rd,c (kPa)')
    beta: float
    xi: float
    rho_l: float
    utilization: float
    applicable: bool = Field(True, description='True si la verificación de punzonamiento es concluyente. Para zapatas estándar o compactas (EC2 §6.4.4(2)), se resuelve evaluando el perímetro crítico dentro del rango a <= 2d.')
    a_crit_m: float = Field(0.0, description="Distancia crítica 'a' desde la cara del soporte al perímetro de control (m).")
    u_crit_m: float = Field(0.0, description='Longitud del perímetro crítico evaluado (m).')
    is_compact: bool = Field(False, description='True si el perímetro crítico se produce a distancia a < 2d según EC2 §6.4.4(2).')
    tau_rd_scaled_kPa: float = Field(0.0, description='Resistencia a cortante escalada por (2d/a) según EC2 §6.4.4(2) (kPa).')

    @property
    def is_ok(self) -> bool:
        return self.utilization <= 1.0

    @property
    def verdict(self) -> str:
        """Veredicto honesto: nunca presenta como PASS un chequeo no aplicable."""
        if not self.applicable:
            return 'NO_APLICABLE_2D'
        return 'PASS' if self.is_ok else 'FAIL'

def punching_shear_check(foundation: RectangularFoundation, column: Column, N_sd_kN: float, fck_MPa: float, rho_x: float, rho_y: float, d_eff_m: float, gamma_c: float=1.5) -> PunchingShearResult:
    """EC2 punching shear at 2·d or interior perimeter a < 2·d for compact footings.

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
    u1 = 2.0 * c1 + 3.0 * c2 + 4.0 * math.pi * d
    A_u1 = c1 * c2 + math.pi * (2.0 * d) ** 2 + 4.0 * d * c1 + 4.0 * d * c2
    A_footing = foundation.area
    if A_footing <= 0:
        raise ValueError('Footing area must be positive.')
    beta = column.punching_beta(foundation)
    xi = min(1.0 + math.sqrt(200.0 / (d * 1000.0)), 2.0)
    rho_l = min(math.sqrt(max(rho_x, 0.0) * max(rho_y, 0.0)), 0.02)
    tau_rd_MPa = 0.18 / gamma_c * xi * (100.0 * rho_l * fck_MPa) ** (1.0 / 3.0)
    tau_rd_kPa = tau_rd_MPa * 1000.0
    if A_u1 < A_footing:
        F_sd = N_sd_kN * (A_footing - A_u1) / A_footing
        F_sd = max(F_sd, 0.0)
        F_sd_ef = beta * F_sd
        tau_sd = F_sd_ef / (u1 * d) if u1 * d > 0 else 0.0
        utilization = tau_sd / tau_rd_kPa if tau_rd_kPa > 0 else float('inf')
        return PunchingShearResult(u1=u1, d_eff=d, F_sd=F_sd, F_sd_ef=F_sd_ef, tau_sd=tau_sd, tau_rd=tau_rd_kPa, beta=beta, xi=xi, rho_l=rho_l, utilization=utilization, applicable=True, a_crit_m=2.0 * d, u_crit_m=u1, is_compact=False, tau_rd_scaled_kPa=tau_rd_kPa)
    else:
        dist_edge_x = max((foundation.length / 1000.0 - c1) / 2.0, 0.01) if foundation.length > 10.0 else max((foundation.length - c1) / 2.0, 0.01)
        dist_edge_y = max((foundation.width / 1000.0 - c2) / 2.0, 0.01) if foundation.width > 10.0 else max((foundation.width - c2) / 2.0, 0.01)
        max_a = min(2.0 * d, max(dist_edge_x, dist_edge_y))
        a_candidates = np.linspace(0.1 * d, max_a, 40)
        max_util = 0.0
        best_tuple = None
        for a_val in a_candidates:
            u_a = 2.0 * (c1 + c2) + 2.0 * math.pi * a_val
            A_u_a = c1 * c2 + 2.0 * (c1 + c2) * a_val + math.pi * a_val ** 2
            if A_u_a >= A_footing:
                continue
            F_sd_a = N_sd_kN * (1.0 - A_u_a / A_footing)
            F_sd_ef_a = beta * F_sd_a
            tau_sd_a = F_sd_ef_a / (u_a * d)
            scale = 2.0 * d / a_val
            tau_rd_a = tau_rd_kPa * scale
            util = tau_sd_a / tau_rd_a
            if util >= max_util or best_tuple is None:
                max_util = util
                best_tuple = (a_val, u_a, F_sd_a, F_sd_ef_a, tau_sd_a, tau_rd_a)
        if best_tuple is None:
            a_crit, u_crit, F_sd_crit, F_sd_ef_crit, tau_sd_crit, tau_rd_scaled = (0.5 * d, u1, 0.0, 0.0, 0.0, tau_rd_kPa * 4.0)
        else:
            a_crit, u_crit, F_sd_crit, F_sd_ef_crit, tau_sd_crit, tau_rd_scaled = best_tuple
        return PunchingShearResult(u1=u_crit, d_eff=d, F_sd=F_sd_crit, F_sd_ef=F_sd_ef_crit, tau_sd=tau_sd_crit, tau_rd=tau_rd_kPa, beta=beta, xi=xi, rho_l=rho_l, utilization=max_util, applicable=True, a_crit_m=float(a_crit), u_crit_m=float(u_crit), is_compact=True, tau_rd_scaled_kPa=float(tau_rd_scaled))