"""
Memoria handcalcs -- Zapata combinada (combined footing) con verificacion
completa: distribucion de presiones, capacidad portante EC7, diseno a
flexion y punzonamiento en cada columna.

Aproximacion clasica con tension trapezoidal/triangular en la base:
    q = N/A +/- M*y/I

Theory: docs/theory/03_shallow_foundations.md + EN 1997-1 (EC7) + EN 1992-1-1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

try:
    from handcalcs.decorator import handcalc
    _HAS_HANDCALCS = True
except ImportError:
    _HAS_HANDCALCS = False
    def handcalc(*args, **kwargs):
        def deco(f): return f
        return deco


@dataclass(frozen=True)
class CombinedFootingFullInput:
    """Input for the full combined footing memo."""

    # Column loads
    P1_kN: float                       # axial load column 1
    P2_kN: float                       # axial load column 2
    M1_kNm: float = 0.0               # moment at column 1
    M2_kNm: float = 0.0               # moment at column 2

    # Geometry
    distance_cols_m: float = 4.0       # centre-to-centre
    L_m: float = 6.0                   # total footing length
    B_m: float = 2.0                   # footing width
    h_m: float = 0.60                  # footing thickness

    # Column dimensions (square)
    col1_dim_m: float = 0.40
    col2_dim_m: float = 0.40

    # Soil
    q_adm_kPa: float = 200.0          # allowable bearing pressure
    gamma_soil_kN_m3: float = 18.0
    c_kPa: float = 10.0               # effective cohesion
    phi_deg: float = 30.0             # effective friction angle
    D_f_m: float = 1.5                 # embedment depth

    # Concrete / steel
    fc_MPa: float = 25.0
    fy_MPa: float = 420.0
    cover_mm: float = 50.0


@dataclass(frozen=True)
class CombinedFootingFullResult:
    """Result of the full combined footing memo."""

    # Pressure distribution
    sigma_max_kPa: float
    sigma_min_kPa: float
    e_m: float                         # eccentricity of resultant

    # EC7 bearing capacity
    R_d_kN: float                      # design bearing capacity
    is_safe_bearing: bool

    # Flexure
    M_face_col1_kNm: float            # bending moment at face of col 1
    M_face_col2_kNm: float            # bending moment at face of col 2
    M_midspan_kNm: float              # midspan bending moment
    As_req_mm2: float                  # required reinforcement area

    # Punching
    v_Ed_col1_kPa: float
    v_Rd_kPa: float
    v_Ed_col2_kPa: float
    is_safe_punching_col1: bool
    is_safe_punching_col2: bool

    is_safe_no_tension: bool           # sigma_min >= 0
    markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sigma_max_kPa": self.sigma_max_kPa,
            "sigma_min_kPa": self.sigma_min_kPa,
            "e_m": self.e_m,
            "R_d_kN": self.R_d_kN,
            "is_safe_bearing": self.is_safe_bearing,
            "M_face_col1_kNm": self.M_face_col1_kNm,
            "M_face_col2_kNm": self.M_face_col2_kNm,
            "As_req_mm2": self.As_req_mm2,
            "v_Ed_col1_kPa": self.v_Ed_col1_kPa,
            "v_Ed_col2_kPa": self.v_Ed_col2_kPa,
            "is_safe_punching_col1": self.is_safe_punching_col1,
            "is_safe_punching_col2": self.is_safe_punching_col2,
        }


def _bearing_capacity_ec7(B: float, L: float, D_f: float,
                           gamma: float, c: float, phi_deg: float,
                           gamma_R: float = 1.4) -> float:
    """Brinch-Hansen bearing capacity per EC7 6.5 -- returns R_d (kN)."""
    phi_r = math.radians(max(phi_deg, 0.1))
    N_q = math.exp(math.pi * math.tan(phi_r)) * \
          math.tan(math.pi / 4 + phi_r / 2) ** 2
    N_c = (N_q - 1) / math.tan(phi_r)
    N_gamma = 2 * (N_q - 1) * math.tan(phi_r)

    # Shape factors
    s_q = 1 + (B / L) * math.sin(phi_r)
    s_c = 1 + (B / L) * (N_q / N_c) if N_c > 0 else 1.0
    s_gamma = 1 - 0.4 * (B / L)

    # Depth factors
    d_q = 1 + 2 * math.tan(phi_r) * (1 - math.sin(phi_r)) ** 2 * (D_f / B)
    d_c = d_q - (1 - d_q) / (N_c * math.tan(phi_r)) if N_c > 0 else 1.0
    d_gamma = 1.0

    q_0 = gamma * D_f
    sigma_ult = (c * N_c * s_c * d_c
                 + q_0 * N_q * s_q * d_q
                 + 0.5 * gamma * B * N_gamma * s_gamma * d_gamma)
    R_ult = sigma_ult * B * L
    R_d = R_ult / gamma_R
    return R_d


def render_combined_footing_memo(
    inp: CombinedFootingFullInput,
) -> CombinedFootingFullResult:
    """Render a complete combined footing memo with:

    1. Pressure distribution: q = N/A +/- M*y/I (trapezoidal/triangular).
    2. Bearing capacity check per EC7 (Brinch-Hansen).
    3. Flexural design: moment at face of each column, As required.
    4. Punching shear at each column (ACI 318 / EC2 simplified).
    """
    P_total = inp.P1_kN + inp.P2_kN
    M_total = inp.M1_kNm + inp.M2_kNm

    # --- Step 1: Pressure distribution ---
    # Overhang from left edge to column 1 (assume columns centred in footing)
    overhang_left = (inp.L_m - inp.distance_cols_m) / 2.0
    # Resultant position from column 1
    x_R_from_col1 = (inp.P2_kN * inp.distance_cols_m + M_total) / max(P_total, 1e-9)
    # Resultant position from left edge of footing
    x_R = overhang_left + x_R_from_col1
    # Centre of footing
    x_centro = inp.L_m / 2.0
    # Eccentricity (positive = resultant left of centre)
    e = x_centro - x_R

    A = inp.L_m * inp.B_m
    I = inp.B_m * inp.L_m ** 3 / 12.0
    y_max = inp.L_m / 2.0

    sigma_max = P_total / A + abs(P_total * e) * y_max / I
    sigma_min = P_total / A - abs(P_total * e) * y_max / I

    # --- Step 2: Bearing capacity EC7 ---
    # Effective width for eccentric loading (Meyerhof correction)
    B_eff = inp.B_m
    L_eff = inp.L_m - 2 * abs(e)
    if L_eff < B_eff:
        B_eff, L_eff = L_eff, B_eff

    R_d = _bearing_capacity_ec7(
        B=max(B_eff, 0.1), L=max(L_eff, 0.1),
        D_f=inp.D_f_m, gamma=inp.gamma_soil_kN_m3,
        c=inp.c_kPa, phi_deg=inp.phi_deg,
    )
    is_safe_bearing = R_d >= P_total

    # --- Step 3: Flexure at column faces ---
    # Distributed soil pressure (uniform approximation for flexure)
    w_soil = P_total / inp.L_m  # kN/m (per unit width * B)
    q_per_m = w_soil / inp.B_m   # kPa base

    # Column 1 face: cantilever from left edge to column 1 face
    # Assume col 1 at some overhang from left edge
    overhang_1 = (inp.L_m - inp.distance_cols_m) / 2.0
    l_cant_1 = max(overhang_1 - inp.col1_dim_m / 2.0, 0.0)
    M_face_col1 = w_soil * l_cant_1 ** 2 / 2.0

    # Column 2 face: cantilever from right edge
    overhang_2 = (inp.L_m - inp.distance_cols_m) / 2.0
    l_cant_2 = max(overhang_2 - inp.col2_dim_m / 2.0, 0.0)
    M_face_col2 = w_soil * l_cant_2 ** 2 / 2.0

    # Midspan moment (between columns, approximation as simply-supported
    # beam with cantilevers carrying the overhang)
    span = inp.distance_cols_m - inp.col1_dim_m / 2.0 - inp.col2_dim_m / 2.0
    R_left = P_total / 2.0 - (M_face_col1 - M_face_col2) / max(span, 0.1)
    M_midspan = R_left * span / 2.0 - w_soil * (span / 2.0) ** 2 / 2.0
    M_midspan = abs(M_midspan)

    # Required reinforcement (bottom, for max moment)
    M_design = max(M_face_col1, M_face_col2, M_midspan)
    d_eff_mm = inp.h_m * 1000 - inp.cover_mm - 10  # half bar diameter
    if d_eff_mm <= 0:
        d_eff_mm = 1.0
    # mu = M / (b * d^2 * fcd)
    fcd = inp.fc_MPa / 1.5
    b_mm = inp.B_m * 1000
    mu = (M_design * 1e6) / (b_mm * d_eff_mm ** 2 * fcd)
    mu = min(mu, 0.30)  # practical limit
    omega = 1 - math.sqrt(1 - 2 * mu)
    As_req = omega * b_mm * d_eff_mm * fcd / inp.fy_MPa
    # Minimum reinforcement EC2: 0.26 * fctm/fyk * b * d
    fctm = 0.3 * inp.fc_MPa ** (2 / 3)
    As_min = 0.26 * fctm / inp.fy_MPa * b_mm * d_eff_mm
    As_req = max(As_req, As_min)

    # --- Step 4: Punching shear at each column ---
    d_m = d_eff_mm / 1000.0

    def _punching(P_col: float, col_dim: float) -> tuple[float, float]:
        b_0 = 4 * (col_dim + d_m)
        v_Ed = P_col / (b_0 * d_m)
        v_Rd = 0.33 * math.sqrt(inp.fc_MPa) * 1000  # MPa->kPa
        return v_Ed, v_Rd

    v_Ed_1, v_Rd = _punching(inp.P1_kN, inp.col1_dim_m)
    v_Ed_2, _ = _punching(inp.P2_kN, inp.col2_dim_m)

    # --- Markdown report ---
    ok = lambda b: "OK" if b else "NO CUMPLE"
    md = (
        "# Memoria -- Zapata Combinada (EC7 + EC2)\n\n"
        f"**Cargas:** P1={inp.P1_kN:.1f}kN, P2={inp.P2_kN:.1f}kN, "
        f"M1={inp.M1_kNm:.1f}kNm, M2={inp.M2_kNm:.1f}kNm\n"
        f"**Dimensiones:** L={inp.L_m:.2f}m, B={inp.B_m:.2f}m, "
        f"h={inp.h_m:.2f}m\n\n"
        f"## Paso 1 -- Distribucion de presiones\n"
        f"P_total = P1+P2 = {P_total:.1f} kN\n"
        f"e = L/2 - x_R = {e:.3f} m\n"
        f"sigma_max = N/A + |N*e|*y/I = **{sigma_max:.1f} kPa**\n"
        f"sigma_min = N/A - |N*e|*y/I = **{sigma_min:.1f} kPa**\n"
        f"sigma_min >= 0 (sin traccion) -> {ok(sigma_min >= 0)}\n\n"
        f"## Paso 2 -- Capacidad portante EC7\n"
        f"B_eff={B_eff:.2f}m, L_eff={L_eff:.2f}m\n"
        f"R_d = {R_d:.1f} kN >= P = {P_total:.1f} kN -> {ok(is_safe_bearing)}\n\n"
        f"## Paso 3 -- Diseno a flexion\n"
        f"M_face_col1 = {M_face_col1:.1f} kNm\n"
        f"M_face_col2 = {M_face_col2:.1f} kNm\n"
        f"M_midspan = {M_midspan:.1f} kNm\n"
        f"As_req = **{As_req:.0f} mm2**\n\n"
        f"## Paso 4 -- Punzonamiento\n"
        f"Col 1: v_Ed={v_Ed_1:.1f}kPa <= v_Rd={v_Rd:.1f}kPa -> "
        f"{ok(v_Ed_1 <= v_Rd)}\n"
        f"Col 2: v_Ed={v_Ed_2:.1f}kPa <= v_Rd={v_Rd:.1f}kPa -> "
        f"{ok(v_Ed_2 <= v_Rd)}\n"
    )

    return CombinedFootingFullResult(
        sigma_max_kPa=sigma_max, sigma_min_kPa=sigma_min, e_m=e,
        R_d_kN=R_d, is_safe_bearing=is_safe_bearing,
        M_face_col1_kNm=M_face_col1, M_face_col2_kNm=M_face_col2,
        M_midspan_kNm=M_midspan, As_req_mm2=As_req,
        v_Ed_col1_kPa=v_Ed_1, v_Rd_kPa=v_Rd, v_Ed_col2_kPa=v_Ed_2,
        is_safe_punching_col1=v_Ed_1 <= v_Rd,
        is_safe_punching_col2=v_Ed_2 <= v_Rd,
        is_safe_no_tension=sigma_min >= 0,
        markdown=md,
    )


__all__ = [
    "CombinedFootingFullInput",
    "CombinedFootingFullResult",
    "render_combined_footing_memo",
]
