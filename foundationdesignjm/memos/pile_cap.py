"""
Memoria handcalcs — Pile Cap (cabezal de pilotes) por método Strut-and-Tie
+ verificación Broms para carga lateral.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from math import sqrt
from typing import Any


@dataclass(frozen=True)
class PileCapInput:
    P_kN: float                       # carga vertical total
    n_piles: int = 4
    pile_diameter_m: float = 0.6
    pile_spacing_m: float = 1.8       # centro-a-centro
    cap_thickness_m: float = 1.0
    fc_MPa: float = 25.0
    fy_MPa: float = 420.0


@dataclass(frozen=True)
class PileCapResult:
    P_per_pile_kN: float
    strut_force_kN: float
    rebar_area_mm2: float
    is_safe: bool
    markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "P_per_pile_kN": self.P_per_pile_kN,
            "strut_force_kN": self.strut_force_kN,
            "rebar_area_mm2": self.rebar_area_mm2,
            "is_safe": self.is_safe,
        }


def render_pile_cap_memo(inp: PileCapInput) -> PileCapResult:
    P_pile = inp.P_kN / inp.n_piles
    # Strut-and-Tie ACI 318-19 Apéndice A
    # Brazo del tie ≈ 0.85·d, d = cap_thickness - cover
    d = inp.cap_thickness_m - 0.08  # 80mm recubrimiento
    arm = max(0.85 * d, 0.1)
    # Tie force ≈ P_pile · spacing/2 / arm
    Tie_kN = P_pile * (inp.pile_spacing_m / 2) / arm
    Strut_kN = sqrt(P_pile ** 2 + Tie_kN ** 2)

    # Área de acero requerida (φ=0.75 para tie)
    As_req_mm2 = Tie_kN * 1000 / (0.75 * inp.fy_MPa)

    # Verificación bielas (compresión) — limit: 0.85·f'c·Ac
    Ac_strut_mm2 = (inp.pile_diameter_m * 1000) ** 2  # área proyectada del pilote
    Strut_capacity_kN = 0.85 * inp.fc_MPa * Ac_strut_mm2 / 1000
    is_safe = Strut_kN <= Strut_capacity_kN

    md = (
        "# Memoria — Pile Cap (Strut-and-Tie ACI 318-19 Anexo A)\n\n"
        f"**Carga total:** P = {inp.P_kN:.1f} kN\n"
        f"**Pilotes:** {inp.n_piles} φ{inp.pile_diameter_m*1000:.0f}mm "
        f"@ {inp.pile_spacing_m:.2f} m\n\n"
        f"## Paso 1 — Reparto\n"
        f"P_pilote = P / n = {P_pile:.1f} kN\n\n"
        f"## Paso 2 — Modelo Strut-and-Tie\n"
        f"Brazo z ≈ 0.85·d = {arm*1000:.0f} mm\n"
        f"Tie = P_pilote · s/2 / z = {Tie_kN:.1f} kN\n"
        f"Strut = √(P² + T²) = {Strut_kN:.1f} kN\n\n"
        f"## Paso 3 — Refuerzo\n"
        f"As_req = T / (φ·fy) = **{As_req_mm2:.0f} mm²**\n\n"
        f"## Paso 4 — Verificación de bielas\n"
        f"Strut ≤ 0.85·f'c·Ac = {Strut_capacity_kN:.0f} kN → "
        f"{'✅' if is_safe else '❌'}\n"
    )

    return PileCapResult(
        P_per_pile_kN=P_pile, strut_force_kN=Strut_kN,
        rebar_area_mm2=As_req_mm2, is_safe=is_safe, markdown=md,
    )



# ---------------------------------------------------------------------------
# FD-002: Broms / Meyerhof / Group-efficiency memo
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BromsMeyerhofInput:
    """Input for the Broms + Meyerhof + group-efficiency pile-cap memo."""

    # Group geometry
    n_piles: int = 4                    # number of piles
    n_rows: int = 2                     # rows in the group
    n_cols: int = 2                     # columns in the group
    pile_diameter_m: float = 0.6
    pile_length_m: float = 15.0
    pile_spacing_m: float = 1.8         # centre-to-centre

    # Loads
    P_total_kN: float = 4000.0          # total vertical load on group
    H_kN: float = 200.0                 # horizontal load on group

    # Pile capacity (single)
    Q_single_kN: float = 1200.0         # axial capacity of single pile

    # Soil parameters
    soil_type: str = "clay"              # "clay" or "sand"
    su_kPa: float = 60.0                # undrained shear strength (clay)
    phi_deg: float = 0.0                # friction angle (sand)
    gamma_soil_kN_m3: float = 18.0

    # Cap geometry for punching check
    cap_B_m: float = 4.0                # cap width
    cap_L_m: float = 4.0                # cap length
    cap_h_m: float = 1.0                # cap thickness
    column_dim_m: float = 0.50          # column dimension (square)
    fc_MPa: float = 25.0                # concrete strength


@dataclass(frozen=True)
class BromsMeyerhofResult:
    """Result of the Broms/Meyerhof pile-cap memo."""

    # Group capacity
    eta_group: float                     # group efficiency
    Q_group_kN: float                    # axial group capacity
    is_safe_axial: bool

    # Broms lateral
    H_ult_single_kN: float              # Broms lateral capacity per pile
    H_group_kN: float                   # group lateral capacity
    is_safe_lateral: bool

    # Meyerhof punching
    v_Ed_kPa: float                     # acting shear stress
    v_Rd_kPa: float                     # resisting shear stress
    is_safe_punching: bool

    markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "eta_group": self.eta_group,
            "Q_group_kN": self.Q_group_kN,
            "is_safe_axial": self.is_safe_axial,
            "H_ult_single_kN": self.H_ult_single_kN,
            "H_group_kN": self.H_group_kN,
            "is_safe_lateral": self.is_safe_lateral,
            "v_Ed_kPa": self.v_Ed_kPa,
            "v_Rd_kPa": self.v_Rd_kPa,
            "is_safe_punching": self.is_safe_punching,
        }


def _group_efficiency_converse_labarre(n_rows: int, n_cols: int,
                                        D_m: float, s_m: float) -> float:
    """Converse-Labarre group efficiency formula.

    eta = 1 - theta · [(n_cols-1)·n_rows + (n_rows-1)·n_cols]
              / (90 · n_rows · n_cols)
    where theta = arctan(D/s) in degrees.
    """
    import math as _m
    theta_deg = _m.degrees(_m.atan(D_m / s_m))
    num = theta_deg * ((n_cols - 1) * n_rows + (n_rows - 1) * n_cols)
    den = 90.0 * n_rows * n_cols
    eta = 1.0 - num / den
    return max(min(eta, 1.0), 0.3)


def _broms_clay(D_m: float, L_m: float, su_kPa: float) -> float:
    """Broms (1964) lateral capacity for a free-head pile in clay.

    H_ult = 9 · su · D · (L - 1.5·D) -- simplified short-pile formula.
    For long piles the capacity is governed by the yield moment, but we
    conservatively use the short-pile approach.
    """
    e = 0.0  # free head, zero eccentricity for simplified version
    H_ult = 9.0 * su_kPa * D_m * max(L_m - 1.5 * D_m, 0.1)
    return H_ult


def _broms_sand(D_m: float, L_m: float, phi_deg: float,
                gamma: float) -> float:
    """Broms (1964) lateral capacity for a free-head pile in sand.

    H_ult = 0.5 · gamma · D · L^2 · Kp
    """
    import math as _m
    phi_r = _m.radians(phi_deg)
    Kp = _m.tan(_m.pi / 4 + phi_r / 2) ** 2
    H_ult = 0.5 * gamma * D_m * L_m ** 2 * Kp
    return H_ult


def _meyerhof_punching(P_kN: float, col_dim_m: float,
                        cap_h_m: float, fc_MPa: float) -> tuple[float, float]:
    """Meyerhof-style two-way punching shear check on pile cap.

    Perimeter at d/2 from column face, resistance per ACI 318-19.
    Returns (v_Ed_kPa, v_Rd_kPa).
    """
    cover_m = 0.075
    d_m = cap_h_m - cover_m
    if d_m <= 0:
        return (float("inf"), 0.0)

    # Critical perimeter at d/2 from each column face
    b_0 = 4 * (col_dim_m + d_m)  # square column
    v_Ed = P_kN / (b_0 * d_m)    # kPa

    # ACI 318-19 Eq. 22.6.5.2(a): v_c = 0.33 * sqrt(f'c) MPa
    v_Rd = 0.33 * sqrt(fc_MPa) * 1000  # MPa -> kPa

    return (v_Ed, v_Rd)


def render_pile_cap_broms_meyerhof_memo(
    inp: BromsMeyerhofInput,
) -> BromsMeyerhofResult:
    """Render a step-by-step pile-cap memo covering:

    1. Axial group capacity with efficiency factor (Converse-Labarre).
    2. Broms lateral capacity (clay or sand).
    3. Meyerhof two-way punching shear on the cap.
    """
    # --- Step 1: Group axial capacity ---
    eta = _group_efficiency_converse_labarre(
        inp.n_rows, inp.n_cols, inp.pile_diameter_m, inp.pile_spacing_m,
    )
    Q_group = inp.n_piles * inp.Q_single_kN * eta
    is_safe_axial = Q_group >= inp.P_total_kN

    # --- Step 2: Broms lateral capacity ---
    if inp.soil_type == "clay":
        H_ult_single = _broms_clay(inp.pile_diameter_m, inp.pile_length_m,
                                    inp.su_kPa)
    else:
        H_ult_single = _broms_sand(inp.pile_diameter_m, inp.pile_length_m,
                                    inp.phi_deg, inp.gamma_soil_kN_m3)
    H_group = inp.n_piles * H_ult_single * eta
    is_safe_lateral = H_group >= inp.H_kN

    # --- Step 3: Meyerhof punching shear ---
    v_Ed, v_Rd = _meyerhof_punching(
        inp.P_total_kN, inp.column_dim_m, inp.cap_h_m, inp.fc_MPa,
    )
    is_safe_punching = v_Ed <= v_Rd

    # --- Markdown report ---
    ok = lambda b: "OK" if b else "NO CUMPLE"
    md = (
        "# Memoria -- Pile Cap (Broms / Meyerhof)\n\n"
        f"**Grupo:** {inp.n_piles} pilotes D={inp.pile_diameter_m*1000:.0f}mm, "
        f"L={inp.pile_length_m:.1f}m, s={inp.pile_spacing_m:.2f}m\n"
        f"**Cargas:** P={inp.P_total_kN:.1f}kN, H={inp.H_kN:.1f}kN\n\n"
        f"## Paso 1 -- Capacidad axial del grupo\n"
        f"eta (Converse-Labarre) = {eta:.3f}\n"
        f"Q_group = n * Q_single * eta = {inp.n_piles} * {inp.Q_single_kN:.0f} "
        f"* {eta:.3f} = **{Q_group:.1f} kN**\n"
        f"P_total = {inp.P_total_kN:.1f} kN -> {ok(is_safe_axial)}\n\n"
        f"## Paso 2 -- Capacidad lateral (Broms, {inp.soil_type})\n"
        f"H_ult,single = {H_ult_single:.1f} kN\n"
        f"H_group = n * H_ult * eta = {H_group:.1f} kN\n"
        f"H_Ed = {inp.H_kN:.1f} kN -> {ok(is_safe_lateral)}\n\n"
        f"## Paso 3 -- Punzonamiento del cabezal (Meyerhof / ACI 318)\n"
        f"d = h - rec = {inp.cap_h_m - 0.075:.3f} m\n"
        f"v_Ed = P / (b_0 * d) = {v_Ed:.1f} kPa\n"
        f"v_Rd = 0.33 * sqrt(f'c) = {v_Rd:.1f} kPa\n"
        f"-> {ok(is_safe_punching)}\n"
    )

    return BromsMeyerhofResult(
        eta_group=eta, Q_group_kN=Q_group, is_safe_axial=is_safe_axial,
        H_ult_single_kN=H_ult_single, H_group_kN=H_group,
        is_safe_lateral=is_safe_lateral,
        v_Ed_kPa=v_Ed, v_Rd_kPa=v_Rd, is_safe_punching=is_safe_punching,
        markdown=md,
    )


__all__ = [
    "PileCapInput", "PileCapResult", "render_pile_cap_memo",
    "BromsMeyerhofInput", "BromsMeyerhofResult",
    "render_pile_cap_broms_meyerhof_memo",
]
