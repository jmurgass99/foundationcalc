"""Strap (tie) beam design for shallow foundations and pile foundations.

Theory: docs/theory/03_shallow_foundations.md §3.7 + 07_seismic.md §7.4.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class StrapBeamSpec(BaseModel):
    """Geometric and design output for a strap (tie) beam."""

    width_mm: float = Field(..., description="b (mm) ≥ 300")
    depth_mm: float = Field(..., description="h (mm) ≥ L/12 ≥ 350")
    length_mm: float
    design_axial_kN: float
    design_shear_kN: float
    design_moment_kNm: float
    note: str = ""


class GroundType(str, Enum):
    """EC8 ground type, for tie-beam seismic actions."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


def strap_for_two_footings(
    N1_kN: float,
    N2_kN: float,
    length_mm: float,
    eccentricity_mm: float = 0.0,
    seismic_factor: float = 0.03,
    q_self_kNm: float = 10.0,
) -> StrapBeamSpec:
    """Strap beam linking two footings.

    Design forces:
        T = seismic_factor · (N1 + N2)          (default 0.03 for non-seismic Spain)
        M1d = ±(M_column + N_column · e)
        M2d = ±q·L²/12 (self weight)
    """
    T = seismic_factor * (N1_kN + N2_kN)
    L = length_mm / 1000.0
    M2 = q_self_kNm * L ** 2 / 12.0
    M1 = max(N1_kN, N2_kN) * (eccentricity_mm / 1000.0)
    M_total = M1 + M2
    V_total = M_total / L if L > 0 else 0.0

    width = max(300.0, 0.0)
    depth = max(length_mm / 12.0, 350.0)

    return StrapBeamSpec(
        width_mm=width,
        depth_mm=depth,
        length_mm=length_mm,
        design_axial_kN=T,
        design_shear_kN=V_total,
        design_moment_kNm=M_total,
        note="Seismic factor 0.03 for non-seismic. Use (a_c/g) in seismic zones.",
    )


def seismic_tie_force(N_Ed_kN: float, alpha_S: float, ground_type: GroundType) -> float:
    """EC8 §5.4.1.2 tie-beam axial-design force:

        ±0.3·α·S·N_Ed for ground B,
        ±0.4·α·S·N_Ed for ground C,
        ±0.6·α·S·N_Ed for ground D.
    """
    factor = {
        GroundType.A: 0.0,
        GroundType.B: 0.3,
        GroundType.C: 0.4,
        GroundType.D: 0.6,
        GroundType.E: 0.6,
    }[ground_type]
    return factor * alpha_S * N_Ed_kN


def tie_beam_minimum_dimensions(n_storeys_above_basement: int) -> tuple[float, float]:
    """EC8: width ≥ 250 mm; depth ≥ 400 mm (≤ 3 storeys) or 500 mm (4+ storeys)."""
    width = 250.0
    depth = 500.0 if n_storeys_above_basement >= 4 else 400.0
    return width, depth


class Nsr10TieBeamResult(BaseModel):
    """Resultado del diseño de viga de amarre según NSR-10 Artículo A.3.6.4.2."""
    code_article: str = "NSR-10 Artículo A.3.6.4.2"
    seismic_zone: str
    Aa: float
    Pu_col_max_kN: float
    axial_force_Tu_kN: float
    axial_force_Cu_kN: float
    width_mm: float
    depth_mm: float
    length_mm: float
    As_tension_mm2: float
    As_min_mm2: float
    As_provided_mm2: float
    n_bars: int
    bar_diameter_mm: float
    stirrup_spec: str
    note: str


def design_tie_beam_nsr10(
    Pu_col_max_kN: float,
    Aa: float,
    length_m: float,
    seismic_zone: str = "alta",
    fc_MPa: float = 21.0,
    fy_MPa: float = 420.0,
) -> Nsr10TieBeamResult:
    """Diseña viga de amarre según NSR-10 Artículo A.3.6.4.2.

    Fuerza axial normativa:
        T_u = C_u = 0.25 · Aa · Pu  (en zona de amenaza sísmica alta)
        T_u = C_u = 0.20 · Aa · Pu  (en zona de amenaza sísmica intermedia)
        T_u = C_u = 0.15 · Aa · Pu  (en zona de amenaza sísmica baja)
    """
    import math

    zone = seismic_zone.lower().strip()
    if zone in ("alta", "high"):
        factor = 0.25
    elif zone in ("intermedia", "medium", "moderate"):
        factor = 0.20
    else:
        factor = 0.15

    # Fuerza axial exacta según NSR-10 Art. A.3.6.4.2
    T_u_kN = round(factor * Aa * Pu_col_max_kN, 6)
    C_u_kN = T_u_kN


    # Dimensiones mínimas NSR-10 A.3.6.4.3 / C.21
    # Sección transversal mínima: lado >= 250 mm (o 200 mm según tipo estructural), área >= Pu / 200 (en MPa/kgf)
    width_mm = 250.0
    depth_mm = max(300.0, (length_m * 1000.0) / 15.0)

    # Armadura por tracción axial: Tu <= phi * As * fy (phi = 0.90)
    phi = 0.90
    As_tension = (T_u_kN * 1000.0) / (phi * fy_MPa)

    # Cuantía mínima NSR-10 C.21: 4 barras longitudinales, min rho = 0.005 o 4#4 (As = 4*129 = 516 mm²)
    Ag = width_mm * depth_mm
    As_min = max(0.005 * Ag, 516.0)
    As_req = max(As_tension, As_min)

    # Selección de barras (mínimo 4 barras de 1/2" = 12.7 mm, área unitaria 129 mm² o 12 mm = 113 mm²)
    db_mm = 12.7
    bar_area = math.pi * (db_mm ** 2) / 4.0  # 126.7 mm²
    n_bars = max(4, math.ceil(As_req / bar_area))
    if n_bars % 2 != 0:
        n_bars += 1  # número par simétrico
    As_provided = n_bars * bar_area

    stirrups = "Estribos cerrados #3 (9.5mm) c/100mm en zonas de confinamiento y c/150mm en zona central"

    return Nsr10TieBeamResult(
        code_article="NSR-10 Artículo A.3.6.4.2",
        seismic_zone=seismic_zone,
        Aa=Aa,
        Pu_col_max_kN=Pu_col_max_kN,
        axial_force_Tu_kN=T_u_kN,
        axial_force_Cu_kN=C_u_kN,
        width_mm=width_mm,
        depth_mm=depth_mm,
        length_mm=length_m * 1000.0,
        As_tension_mm2=As_tension,
        As_min_mm2=As_min,
        As_provided_mm2=As_provided,
        n_bars=n_bars,
        bar_diameter_mm=db_mm,
        stirrup_spec=stirrups,
        note=f"Fuerza axial = {factor:.2f} · Aa · Pu calculada exactamente según NSR-10 A.3.6.4.2.",
    )


__all__ = [
    "StrapBeamSpec",
    "GroundType",
    "Nsr10TieBeamResult",
    "strap_for_two_footings",
    "seismic_tie_force",
    "tie_beam_minimum_dimensions",
    "design_tie_beam_nsr10",
]

