"""Punching shear verification for SHALLOW FOUNDATIONS / FOOTINGS per EN 1992-1-1 §6.4 (EC2).

Diferenciación Arquitectónica de Dominio:
  - Este módulo es el motor canónico autorizado para PUNZONAMIENTO EN CIMENTACIONES (deduciendo
    la reacción neta del terreno dentro del perímetro de control y aplicando la reducción de
    perímetro crítico para zapatas compactas a <= 2d según EC2 §6.4.4(2)).
  - Para PUNZONAMIENTO EN LOSAS PLANAS / FORJADOS SIN VIGAS (sin terreno de apoyo), el motor
    canónico correspondiente es `fastsap.codes.punching.check_punching`.

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
    u1: float = Field(..., description="Control perimeter at 2·d or critical distance a (m)")
    d_eff: float = Field(..., description="Effective depth (m)")
    F_sd: float = Field(..., description="Net punching force F_sd (kN)")
    F_sd_ef: float = Field(..., description="F_sd_ef = β · F_sd (kN)")
    tau_sd: float = Field(..., description="Acting shear stress τ_sd (kPa = kN/m²)")
    tau_rd: float = Field(..., description="Base shear resistance τ_Rd,c (kPa)")
    beta: float
    xi: float
    rho_l: float
    utilization: float
    applicable: bool = Field(
        True,
        description=(
            "True si la verificación de punzonamiento es concluyente. "
            "Para zapatas estándar o compactas (EC2 §6.4.4(2)), se resuelve "
            "evaluando el perímetro crítico dentro del rango a <= 2d."
        ),
    )
    a_crit_m: float = Field(
        0.0,
        description="Distancia crítica 'a' desde la cara del soporte al perímetro de control (m).",
    )
    u_crit_m: float = Field(
        0.0,
        description="Longitud del perímetro crítico evaluado (m).",
    )
    is_compact: bool = Field(
        False,
        description="True si el perímetro crítico se produce a distancia a < 2d según EC2 §6.4.4(2).",
    )
    tau_rd_scaled_kPa: float = Field(
        0.0,
        description="Resistencia a cortante escalada por (2d/a) según EC2 §6.4.4(2) (kPa).",
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

    # Critical perimeter at distance 2·d from the column face
    u1 = 2.0 * c1 + 2.0 * c2 + 4.0 * math.pi * d

    # Effective area enclosed by u1 (rectangle + half-circles at the four corners)
    A_u1 = c1 * c2 + math.pi * (2.0 * d) ** 2 + 4.0 * d * c1 + 4.0 * d * c2

    A_footing = foundation.area
    if A_footing <= 0:
        raise ValueError("Footing area must be positive.")

    beta = column.punching_beta(foundation)

    # EC2 τ_Rd,c base
    xi = min(1.0 + math.sqrt(200.0 / (d * 1000.0)), 2.0)
    rho_l = min(math.sqrt(max(rho_x, 0.0) * max(rho_y, 0.0)), 0.02)
    tau_rd_MPa = (0.18 / gamma_c) * xi * (100.0 * rho_l * fck_MPa) ** (1.0 / 3.0)
    tau_rd_kPa = tau_rd_MPa * 1000.0  # MPa → kPa

    if A_u1 < A_footing:
        # Zapata estándar: u1 a 2d queda contenida dentro de la zapata
        F_sd = N_sd_kN * (A_footing - A_u1) / A_footing
        F_sd = max(F_sd, 0.0)
        F_sd_ef = beta * F_sd
        # DEFECTO CORREGIDO: aqui habia `... if u1 * d > 0 else 0.0`. Con la
        # guarda fallando, la tension ACTUANTE colapsaba a 0.0, la utilizacion
        # salia 0 y el veredicto PASS: la geometria degenerada aprobaba el
        # punzonamiento por no haberlo comprobado. Es tambien la razon de que
        # el mutante `u1 * d > 0` -> `< 0` sobreviviera a toda la suite.
        if u1 * d <= 0:
            raise ValueError(
                f"perimetro de control degenerado: u1 = {u1:.6f} m, d = {d:.6f} m. "
                f"Sin area de control no hay tension de punzonamiento que calcular."
            )
        tau_sd = F_sd_ef / (u1 * d)
        utilization = tau_sd / tau_rd_kPa if tau_rd_kPa > 0 else float("inf")

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
            applicable=True,
            a_crit_m=2.0 * d,
            u_crit_m=u1,
            is_compact=False,
            tau_rd_scaled_kPa=tau_rd_kPa,
        )
    else:
        # Zapata compacta (EC2 §6.4.4(2)): el perímetro a 2d excede la planta.
        # Se evalúan perímetros interiores a < 2d con resistencia tau_Rd escalada por (2d/a).
        dist_edge_x = max((foundation.length / 1000.0 - c1) / 2.0, 0.01) if foundation.length > 10.0 else max((foundation.length - c1) / 2.0, 0.01)
        dist_edge_y = max((foundation.width / 1000.0 - c2) / 2.0, 0.01) if foundation.width > 10.0 else max((foundation.width - c2) / 2.0, 0.01)
        max_a = min(2.0 * d, max(dist_edge_x, dist_edge_y))

        a_candidates = np.linspace(0.1 * d, max_a, 40)
        max_util = 0.0
        best_tuple = None

        for a_val in a_candidates:
            u_a = 2.0 * (c1 + c2) + 2.0 * math.pi * a_val
            A_u_a = c1 * c2 + 2.0 * (c1 + c2) * a_val + math.pi * (a_val**2)
            if A_u_a >= A_footing:
                continue
            F_sd_a = N_sd_kN * (1.0 - A_u_a / A_footing)
            F_sd_ef_a = beta * F_sd_a
            tau_sd_a = F_sd_ef_a / (u_a * d)
            scale = (2.0 * d) / a_val
            tau_rd_a = tau_rd_kPa * scale
            util = tau_sd_a / tau_rd_a

            if util >= max_util or best_tuple is None:
                max_util = util
                best_tuple = (a_val, u_a, F_sd_a, F_sd_ef_a, tau_sd_a, tau_rd_a)

        if best_tuple is None:
            a_crit, u_crit, F_sd_crit, F_sd_ef_crit, tau_sd_crit, tau_rd_scaled = (0.5 * d, u1, 0.0, 0.0, 0.0, tau_rd_kPa * 4.0)
        else:
            a_crit, u_crit, F_sd_crit, F_sd_ef_crit, tau_sd_crit, tau_rd_scaled = best_tuple

        return PunchingShearResult(
            u1=u_crit,
            d_eff=d,
            F_sd=F_sd_crit,
            F_sd_ef=F_sd_ef_crit,
            tau_sd=tau_sd_crit,
            tau_rd=tau_rd_kPa,
            beta=beta,
            xi=xi,
            rho_l=rho_l,
            utilization=max_util,
            applicable=True,
            a_crit_m=float(a_crit),
            u_crit_m=float(u_crit),
            is_compact=True,
            tau_rd_scaled_kPa=float(tau_rd_scaled),
        )


# ===========================================================================
# ACI 318-19 Punching Shear with Unbalanced Moment Transfer (§8.4.4 & §22.6)
# ===========================================================================

class AciPunchingShearResult(BaseModel):
    """Result of ACI 318-19 two-way shear (punching) check with moment transfer."""

    b0_mm: float = Field(..., description="Critical perimeter b0 at d/2 from column face (mm)")
    Ac_mm2: float = Field(..., description="Critical section area Ac = b0 * d (mm²)")
    Vu_kN: float = Field(..., description="Factored vertical punching shear force (kN)")
    Mux_kNm: float = Field(0.0, description="Factored unbalanced moment about X-axis (kNm)")
    Muy_kNm: float = Field(0.0, description="Factored unbalanced moment about Y-axis (kNm)")
    gamma_vx: float = Field(..., description="Fraction of Mux transferred by eccentric shear (ACI §8.4.4.2.2)")
    gamma_vy: float = Field(..., description="Fraction of Muy transferred by eccentric shear (ACI §8.4.4.2.2)")
    Jcx_mm4: float = Field(..., description="Polar property Jc of critical perimeter for flexure about X (mm⁴)")
    Jcy_mm4: float = Field(..., description="Polar property Jc of critical perimeter for flexure about Y (mm⁴)")
    v_dir_MPa: float = Field(..., description="Direct shear stress Vu / Ac (MPa)")
    v_mom_x_MPa: float = Field(0.0, description="Eccentric shear stress due to Mux (MPa)")
    v_mom_y_MPa: float = Field(0.0, description="Eccentric shear stress due to Muy (MPa)")
    v_ug_max_MPa: float = Field(..., description="Maximum factored shear stress on critical perimeter (MPa)")
    v_ug_min_MPa: float = Field(..., description="Minimum factored shear stress on critical perimeter (MPa)")
    vc_MPa: float = Field(..., description="Nominal two-way shear strength (ACI 318-19 §22.6.5.2) (MPa)")
    phi_vc_MPa: float = Field(..., description="Design shear strength phi * vc with phi = 0.75 (MPa)")
    phi: float = Field(0.75, description="Strength reduction factor (ACI 318-19 Table 21.2.1)")
    utilization: float = Field(..., description="DCR = v_ug_max / phi_vc")
    column_type: str = Field("interior", description="Column position: 'interior', 'edge', 'corner'")
    lambda_s: float = Field(1.0, description="Size effect factor (ACI 318-19 §22.5.5.1.3)")

    @property
    def is_ok(self) -> bool:
        return self.utilization <= 1.0


def punching_shear_aci318_check(
    c1_mm: float,
    c2_mm: float,
    d_eff_mm: float,
    Vu_kN: float,
    fc_MPa: float,
    Mux_kNm: float = 0.0,
    Muy_kNm: float = 0.0,
    column_type: str = "interior",
    phi: float = 0.75,
    lambda_conc: float = 1.0,
) -> AciPunchingShearResult:
    """Punching shear check per ACI 318-19 §8.4.4.2 and §22.6.

    Calculates maximum two-way shear stress v_ug on the critical perimeter at
    d/2 from the column face, combining direct shear and eccentric shear from
    unbalanced moments:

        v_ug = Vu / Ac + gamma_vx * Mux * cy / Jcx + gamma_vy * Muy * cx / Jcy

    Args:
        c1_mm: Column dimension along X (mm).
        c2_mm: Column dimension along Y (mm).
        d_eff_mm: Effective depth of slab / footing (mm).
        Vu_kN: Factored vertical shear load (kN).
        fc_MPa: Concrete compressive cylinder strength f'c (MPa).
        Mux_kNm: Factored unbalanced moment about X-axis causing shear along Y (kNm).
        Muy_kNm: Factored unbalanced moment about Y-axis causing shear along X (kNm).
        column_type: 'interior', 'edge', or 'corner'.
        phi: Strength reduction factor (default 0.75 per Table 21.2.1).
        lambda_conc: Lightweight modification factor (1.0 for normal weight).
    """
    if c1_mm <= 0 or c2_mm <= 0 or d_eff_mm <= 0:
        raise ValueError("Column dimensions and effective depth must be positive.")
    if fc_MPa <= 0:
        raise ValueError("Concrete strength f'c must be positive.")

    col_type = column_type.lower().strip()
    if col_type not in ("interior", "edge", "corner"):
        raise ValueError(f"Unknown column_type '{column_type}'. Must be 'interior', 'edge', or 'corner'.")

    d = d_eff_mm
    Vu_N = Vu_kN * 1000.0
    Mux_Nmm = Mux_kNm * 1e6
    Muy_Nmm = Muy_kNm * 1e6

    # 1. Critical perimeter dimensions at d/2 from column faces
    if col_type == "interior":
        bx = c1_mm + d
        by = c2_mm + d
        b0 = 2.0 * (bx + by)
        Ac = b0 * d
        # Flexure about X (transfers shear in Y direction, b1=by, b2=bx)
        gamma_fx = 1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(by / bx))
        gamma_vx = 1.0 - gamma_fx
        cy = by / 2.0
        Jcx = (d * by**3) / 6.0 + (by * d**3) / 6.0 + (d * bx * by**2) / 2.0

        # Flexure about Y (transfers shear in X direction, b1=bx, b2=by)
        gamma_fy = 1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(bx / by))
        gamma_vy = 1.0 - gamma_fy
        cx = bx / 2.0
        Jcy = (d * bx**3) / 6.0 + (bx * d**3) / 6.0 + (d * by * bx**2) / 2.0

    elif col_type == "edge":
        # Free edge normal to X axis
        bx = c1_mm + d / 2.0  # two sides normal to edge
        by = c2_mm + d        # one side parallel to edge
        b0 = 2.0 * bx + by
        Ac = b0 * d

        # Flexure about Y (normal to edge, non-symmetric along X)
        gamma_fy = 1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(bx / by))
        gamma_vy = 1.0 - gamma_fy
        cx_AB = (bx**2) / b0
        cx = max(cx_AB, bx - cx_AB)
        Jcy = (
            2.0 * ((d * bx**3) / 12.0 + (bx * d) * (bx / 2.0 - cx_AB) ** 2)
            + (by * d) * (cx_AB**2)
            + (by * d**3) / 12.0
        )

        # Flexure about X (parallel to edge, symmetric along Y)
        gamma_fx = 1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(by / bx))
        gamma_vx = 1.0 - gamma_fx
        cy = by / 2.0
        Jcx = (d * by**3) / 12.0 + 2.0 * (bx * d) * (by / 2.0) ** 2 + (bx * d**3) / 6.0

    else:  # corner
        bx = c1_mm + d / 2.0
        by = c2_mm + d / 2.0
        b0 = bx + by
        Ac = b0 * d

        # Flexure about Y
        gamma_fy = 1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(bx / by))
        gamma_vy = 1.0 - gamma_fy
        cx_AB = (bx**2) / (2.0 * b0)
        cx = max(cx_AB, bx - cx_AB)
        Jcy = (
            (d * bx**3) / 12.0
            + (bx * d) * (bx / 2.0 - cx_AB) ** 2
            + (by * d) * (cx_AB**2)
            + (by * d**3) / 12.0
        )

        # Flexure about X
        gamma_fx = 1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(by / bx))
        gamma_vx = 1.0 - gamma_fx
        cy_AB = (by**2) / (2.0 * b0)
        cy = max(cy_AB, by - cy_AB)
        Jcx = (
            (d * by**3) / 12.0
            + (by * d) * (by / 2.0 - cy_AB) ** 2
            + (bx * d) * (cy_AB**2)
            + (bx * d**3) / 12.0
        )

    # 2. Shear stresses (MPa = N/mm²)
    v_dir = Vu_N / Ac if Ac > 0 else 0.0
    v_mom_x = (gamma_vx * abs(Mux_Nmm) * cy) / Jcx if Jcx > 0 else 0.0
    v_mom_y = (gamma_vy * abs(Muy_Nmm) * cx) / Jcy if Jcy > 0 else 0.0

    v_ug_max = v_dir + v_mom_x + v_mom_y
    v_ug_min = v_dir - v_mom_x - v_mom_y

    # 3. Two-way shear concrete strength per ACI 318-19 §22.6.5.2
    sqrt_fc = math.sqrt(fc_MPa)
    lambda_s = min(math.sqrt(2.0 / (1.0 + 0.004 * d)), 1.0)
    beta_c = max(c1_mm, c2_mm) / min(c1_mm, c2_mm)

    alpha_s = 40.0 if col_type == "interior" else (30.0 if col_type == "edge" else 20.0)

    vc_1 = 0.33 * lambda_s * lambda_conc * sqrt_fc
    vc_2 = 0.17 * (1.0 + 2.0 / beta_c) * lambda_s * lambda_conc * sqrt_fc
    vc_3 = 0.083 * (2.0 + (alpha_s * d) / b0) * lambda_s * lambda_conc * sqrt_fc
    vc = min(vc_1, vc_2, vc_3)
    phi_vc = phi * vc

    if phi_vc <= 0.0:
        util = float("inf")
    else:
        util = v_ug_max / phi_vc

    return AciPunchingShearResult(
        b0_mm=b0,
        Ac_mm2=Ac,
        Vu_kN=Vu_kN,
        Mux_kNm=Mux_kNm,
        Muy_kNm=Muy_kNm,
        gamma_vx=gamma_vx,
        gamma_vy=gamma_vy,
        Jcx_mm4=Jcx,
        Jcy_mm4=Jcy,
        v_dir_MPa=v_dir,
        v_mom_x_MPa=v_mom_x,
        v_mom_y_MPa=v_mom_y,
        v_ug_max_MPa=v_ug_max,
        v_ug_min_MPa=v_ug_min,
        vc_MPa=vc,
        phi_vc_MPa=phi_vc,
        phi=phi,
        utilization=util,
        column_type=col_type,
        lambda_s=lambda_s,
    )
