"""Bearing capacity per EN 1997-1 Annex D — triple-N equation with shape, depth,
load-inclination, ground-inclination and base-inclination factors.

Drained:    q_ult = c'·N_c·s_c·d_c·i_c·g_c·b_c
                  + q'·N_q·s_q·d_q·i_q·g_q·b_q
                  + 0.5·γ'·B·N_γ·s_γ·d_γ·i_γ·g_γ·b_γ
Undrained:  q_ult = (π+2)·c_u·b_c·s_c·i_c·d_c·g_c + q

Bearing capacity factors (Reissner-Prandtl, Brinch-Hansen, Meyerhof, Vesic, Chen):
- N_q = e^(π·tan φ) · tan²(45° + φ/2)        (all authors)
- N_c = (N_q − 1) · cot φ                     (all authors)
- N_γ depends on the author selected.

Theory: docs/theory/04_eurocode7_examples.md (and EN 1997-1 Annex D).
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from ..core.geometry import RectangularFoundation
from ..core.soil import DrainageCondition, SoilLayer


class BearingCapacityFormula(str, Enum):
    """Author for N_γ (N_c and N_q are identical across authors)."""

    BRINCH_HANSEN = "brinch_hansen"
    MEYERHOF = "meyerhof"
    VESIC = "vesic"
    CHEN_EC7 = "chen_ec7"  # default for EC7


class BearingCapacityResult(BaseModel):
    """Detailed breakdown of the bearing-capacity calculation."""

    formula: BearingCapacityFormula
    drainage: DrainageCondition

    # Soil parameters used
    phi_d_deg: float
    c_d: float
    cu_d: Optional[float] = None
    gamma: float

    # Effective dimensions
    B_eff: float
    L_eff: float
    A_eff: float

    # Capacity factors
    Nq: float
    Nc: float
    Ngamma: float

    # Shape factors
    sq: float
    sc: float
    sgamma: float

    # Depth factors
    dq: float = 1.0
    dc: float = 1.0
    dgamma: float = 1.0

    # Inclination factors
    iq: float = 1.0
    ic: float = 1.0
    igamma: float = 1.0

    # Components of q_ult
    q_ult_overburden: float
    q_ult_cohesion: float
    q_ult_self_weight: float

    # Resultants
    q_ult: float
    R_d: float
    R_k: float

    gamma_Rv: float


def _Nq(phi_rad: float) -> float:
    if phi_rad <= 1e-9:
        return 1.0
    return math.exp(math.pi * math.tan(phi_rad)) * math.tan(math.pi / 4.0 + phi_rad / 2.0) ** 2


def _Nc(phi_rad: float, Nq: float) -> float:
    if phi_rad <= 1e-9:
        return math.pi + 2.0  # Prandtl: (π+2) for φ=0
    return (Nq - 1.0) / math.tan(phi_rad)


def _Ngamma(phi_rad: float, Nq: float, formula: BearingCapacityFormula) -> float:
    if phi_rad <= 1e-9:
        return 0.0
    if formula == BearingCapacityFormula.BRINCH_HANSEN:
        return 1.5 * (Nq - 1.0) * math.tan(phi_rad)
    if formula == BearingCapacityFormula.MEYERHOF:
        return (Nq - 1.0) * math.tan(1.4 * phi_rad)
    if formula == BearingCapacityFormula.VESIC:
        return 2.0 * (Nq + 1.0) * math.tan(phi_rad)
    # Chen / EC7
    return 2.0 * (Nq - 1.0) * math.tan(phi_rad)


def bearing_capacity_factors(
    phi_deg: float,
    formula: BearingCapacityFormula = BearingCapacityFormula.CHEN_EC7,
) -> tuple[float, float, float]:
    """Return (N_q, N_c, N_γ) for a given φ' and N_γ formula."""
    phi_rad = math.radians(phi_deg)
    Nq = _Nq(phi_rad)
    Nc = _Nc(phi_rad, Nq)
    Ng = _Ngamma(phi_rad, Nq, formula)
    return Nq, Nc, Ng


def shape_factors(B_eff: float, L_eff: float, phi_deg: float, Nq: float, Nc: float, k: float = 0.3) -> tuple[float, float, float]:
    """EC7 Annex D shape factors for rectangle B'×L' (B' < L').

    Args:
        k: 0.3 in EC7 default for B/H ≤ 1; 0.4 in Brinch-Hansen / Vesic.
    """
    if B_eff <= 0 or L_eff <= 0:
        return 1.0, 1.0, 1.0
    BL = B_eff / L_eff
    phi_rad = math.radians(phi_deg)

    sq = 1.0 + BL * math.sin(phi_rad)
    if Nq > 1.0:
        sc = (sq * Nq - 1.0) / (Nq - 1.0)
    else:
        sc = 1.0 + 0.2 * BL  # φ=0 case, EC7 D.4: s_c = 1 + 0.2·B'/L'
    sg = 1.0 - k * BL
    return sq, sc, sg


def inclination_factors(
    H: float,
    V: float,
    A_eff: float,
    c_d: float,
    phi_deg: float,
    m: Optional[float] = None,
    B_eff: Optional[float] = None,
    L_eff: Optional[float] = None,
    load_direction: str = "B",
) -> tuple[float, float, float]:
    """Vesic / EC7 Annex D load-inclination factors.

    The exponent m depends on the load direction relative to the footing:

        m_B = (2 + B'/L') / (1 + B'/L')   load parallel to B'
        m_L = (2 + L'/B') / (1 + L'/B')   load parallel to L'
        m  = m_L · cos²θ + m_B · sin²θ    general direction θ

    If only `m` is given (legacy mode) it is used directly. Otherwise
    `B_eff` and `L_eff` together with `load_direction` ('B', 'L' or
    angle in degrees) determine the correct m.
    """
    if H <= 0:
        # Sin carga horizontal no hay inclinación de carga: factores neutros.
        return 1.0, 1.0, 1.0
    if m is None:
        if B_eff is None or L_eff is None or B_eff <= 0 or L_eff <= 0:
            m = 2.0
        else:
            if load_direction == "B":
                m = (2.0 + B_eff / L_eff) / (1.0 + B_eff / L_eff)
            elif load_direction == "L":
                m = (2.0 + L_eff / B_eff) / (1.0 + L_eff / B_eff)
            else:
                try:
                    theta = math.radians(float(load_direction))
                    m_B = (2.0 + B_eff / L_eff) / (1.0 + B_eff / L_eff)
                    m_L = (2.0 + L_eff / B_eff) / (1.0 + L_eff / B_eff)
                    m = m_L * math.cos(theta) ** 2 + m_B * math.sin(theta) ** 2
                except (TypeError, ValueError):
                    m = 2.0

    phi_rad = math.radians(phi_deg)

    if phi_rad <= 1e-9:
        # No drenado (EC7 D.3): el ic depende de H y c_u, NO de V. Se computa aunque
        # V<=0 — el error de abajo es solo de la vía drenada, que sí necesita V.
        ic = 0.5 * (1.0 + math.sqrt(max(0.0, 1.0 - H / (A_eff * c_d)))) if c_d > 0 else 1.0
        return 1.0, ic, 1.0

    # Drenado (Vesic / EN 1997-1 Anexo D): la fórmula asume una resultante de
    # compresión. Con H>0 y V<=0 la inclinación NO es neutra (1,1,1) —sería
    # inseguro— ni está definida: gobierna deslizamiento/levantamiento, no
    # hundimiento. Se niega en vez de aprobar en silencio (el default V_load=0.0
    # hacía fácil el error, dejando q_ult ~31% del lado inseguro).
    if V <= 0:
        raise ValueError(
            f"inclination_factors: H={H:g} kN>0 con V={V:g} kN<=0. La inclinación de "
            "carga drenada (Vesic / EN 1997-1 Anexo D) exige una resultante de "
            "compresión (V>0); con V<=0 el estado límite es deslizamiento o "
            "levantamiento, no hundimiento. Pasa V_load>0 o usa el chequeo correcto."
        )
    denom = V + A_eff * c_d / max(math.tan(phi_rad), 1e-9)
    iq = max(0.0, (1.0 - H / denom)) ** m
    ig = max(0.0, (1.0 - H / denom)) ** (m + 1)
    Nc_factor = _Nq(phi_rad) - 1.0
    if Nc_factor > 1e-9 and abs(math.tan(phi_rad)) > 1e-9:
        ic = iq - (1.0 - iq) / Nc_factor
    else:
        ic = iq
    return iq, ic, ig


def drained_bearing_capacity(
    foundation: RectangularFoundation,
    soil: SoilLayer,
    e_x: float = 0.0,
    e_y: float = 0.0,
    H_load: float = 0.0,
    V_load: float = 0.0,
    overburden_pressure: Optional[float] = None,
    gamma_Rv: float = 1.0,
    gamma_phi: float = 1.0,
    gamma_c: float = 1.0,
    gamma_gamma: float = 1.0,
    formula: BearingCapacityFormula = BearingCapacityFormula.CHEN_EC7,
    use_inclination: bool = True,
) -> BearingCapacityResult:
    """Drained bearing capacity per EC7 Annex D (effective stress, φ', c').

    Args:
        foundation: footing geometry.
        soil: a single SoilLayer; for layered profiles use the founding-level layer.
        e_x, e_y: eccentricities at footing base level (m).
        H_load, V_load: design horizontal and vertical forces (kN).
        overburden_pressure: σ'_v at footing base (kPa). Default = γ · D.
        gamma_Rv, gamma_phi, gamma_c, gamma_gamma: partial factors per the active DA.
        formula: N_γ author.
        use_inclination: whether to compute load-inclination factors.
    """
    phi_d_rad = math.atan(math.tan(math.radians(soil.friction_angle)) / gamma_phi)
    phi_d_deg = math.degrees(phi_d_rad)
    c_d = soil.cohesion / gamma_c
    gamma = soil.unit_weight / gamma_gamma

    Nq, Nc, Ng = bearing_capacity_factors(phi_d_deg, formula)

    L_eff, B_eff = foundation.effective_dimensions(e_x, e_y)
    if B_eff > L_eff:
        L_eff, B_eff = B_eff, L_eff  # ensure B' ≤ L'
    A_eff = max(L_eff * B_eff, 0.0)

    sq, sc, sg = shape_factors(B_eff, L_eff, phi_d_deg, Nq, Nc)

    if use_inclination:
        iq, ic, ig = inclination_factors(
            H_load, V_load, A_eff, c_d, phi_d_deg,
            B_eff=B_eff, L_eff=L_eff, load_direction="B",
        )
    else:
        iq = ic = ig = 1.0

    if overburden_pressure is None:
        overburden_pressure = gamma * foundation.depth_m

    q_ult_q = overburden_pressure * Nq * sq * iq
    q_ult_c = c_d * Nc * sc * ic
    q_ult_g = 0.5 * gamma * B_eff * Ng * sg * ig
    q_ult = q_ult_q + q_ult_c + q_ult_g

    R_k = q_ult * A_eff
    R_d = R_k / gamma_Rv

    return BearingCapacityResult(
        formula=formula,
        drainage=DrainageCondition.DRAINED,
        phi_d_deg=phi_d_deg,
        c_d=c_d,
        gamma=gamma,
        B_eff=B_eff,
        L_eff=L_eff,
        A_eff=A_eff,
        Nq=Nq,
        Nc=Nc,
        Ngamma=Ng,
        sq=sq,
        sc=sc,
        sgamma=sg,
        iq=iq,
        ic=ic,
        igamma=ig,
        q_ult_overburden=q_ult_q,
        q_ult_cohesion=q_ult_c,
        q_ult_self_weight=q_ult_g,
        q_ult=q_ult,
        R_k=R_k,
        R_d=R_k / gamma_Rv,
        gamma_Rv=gamma_Rv,
    )


def undrained_bearing_capacity(
    foundation: RectangularFoundation,
    soil: SoilLayer,
    e_x: float = 0.0,
    e_y: float = 0.0,
    H_load: float = 0.0,
    overburden_pressure: Optional[float] = None,
    gamma_Rv: float = 1.0,
    gamma_cu: float = 1.0,
) -> BearingCapacityResult:
    """Undrained bearing capacity per EC7 Annex D.3:

        R / A' = (π + 2) · c_u · b_c · s_c · i_c · d_c · g_c + q
    """
    if soil.undrained_shear_strength is None:
        raise ValueError("Soil layer must define `undrained_shear_strength` (c_u).")
    cu_d = soil.undrained_shear_strength / gamma_cu

    L_eff, B_eff = foundation.effective_dimensions(e_x, e_y)
    if B_eff > L_eff:
        L_eff, B_eff = B_eff, L_eff
    A_eff = max(L_eff * B_eff, 0.0)

    BL = B_eff / L_eff if L_eff > 0 else 0.0
    sc = 1.0 + 0.2 * BL  # EC7 Annex D.3 undrained

    if H_load > 0 and A_eff * cu_d > 0:
        arg = max(0.0, 1.0 - H_load / (A_eff * cu_d))
        ic = 0.5 * (1.0 + math.sqrt(arg))
    else:
        ic = 1.0

    if overburden_pressure is None:
        overburden_pressure = soil.unit_weight * foundation.depth_m

    q_ult_c = (math.pi + 2.0) * cu_d * sc * ic
    q_ult = q_ult_c + overburden_pressure

    R_k = q_ult * A_eff
    R_d = R_k / gamma_Rv

    return BearingCapacityResult(
        formula=BearingCapacityFormula.CHEN_EC7,
        drainage=DrainageCondition.UNDRAINED,
        phi_d_deg=0.0,
        c_d=0.0,
        cu_d=cu_d,
        gamma=soil.unit_weight,
        B_eff=B_eff,
        L_eff=L_eff,
        A_eff=A_eff,
        Nq=1.0,
        Nc=math.pi + 2.0,
        Ngamma=0.0,
        sq=1.0,
        sc=sc,
        sgamma=1.0,
        iq=1.0,
        ic=ic,
        igamma=1.0,
        q_ult_overburden=overburden_pressure,
        q_ult_cohesion=q_ult_c,
        q_ult_self_weight=0.0,
        q_ult=q_ult,
        R_k=R_k,
        R_d=R_d,
        gamma_Rv=gamma_Rv,
    )
