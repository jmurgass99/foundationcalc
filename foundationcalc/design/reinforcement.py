"""Flexural reinforcement and strut-and-tie design for footings.

Theory: docs/theory/03_shallow_foundations.md §3.4 + 05_pile_foundations.md §5.6.
"""

from __future__ import annotations

import math
from typing import Dict

from pydantic import BaseModel, Field

from ..core.material import Concrete, ReinforcingSteel


class ReinforcementResult(BaseModel):
    As_required: float = Field(..., description="Required area (mm²)")
    As_min: float = Field(..., description="Minimum area per EC2 (mm²)")
    As_provided: float = Field(..., description="Actually required = max(req, min) (mm²)")
    method: str
    note: str = ""


def strut_and_tie_rigid_footing(
    N_d_kN: float,
    a_mm: float,
    v_mm: float,
    d_mm: float,
    steel: ReinforcingSteel,
) -> ReinforcementResult:
    """Rigid footing under axial + small moment (strut-and-tie, EHE 58.4.1).

        T_d = N_d · (v + 0.25·a) / (0.85·d)
    """
    if d_mm <= 0:
        raise ValueError("Effective depth must be positive.")
    T_d = N_d_kN * 1000.0 * (v_mm + 0.25 * a_mm) / (0.85 * d_mm)  # N
    fyd = steel.fyd_strut_and_tie  # N/mm²
    As = T_d / fyd  # mm²
    return ReinforcementResult(
        As_required=As,
        As_min=0.0,
        As_provided=As,
        method="strut_and_tie_2D",
        note="Limit f_yd ≤ 400 N/mm² applied per EHE/EC2 STM rule.",
    )


def flexural_reinforcement(
    M_Ed_kNm: float,
    b_mm: float,
    d_mm: float,
    concrete: Concrete,
    steel: ReinforcingSteel,
) -> ReinforcementResult:
    """Bending design of a singly-reinforced rectangular section (EC2).

    Uses the lever-arm equation z = d/2 · (1 + √(1 − 3.53·K)) with z ≤ 0.95·d,
    capped at K' = 0.167 (singly reinforced limit).

    Minimum reinforcement (EC2 §9.2.1.1):
        As_min = max(0.26 · (f_ctm / f_yk) · b · d, 0.0013 · b · d)
    """
    if d_mm <= 0 or b_mm <= 0:
        raise ValueError("b and d must be positive.")
    M_Nmm = M_Ed_kNm * 1e6
    fck = concrete.fck
    fctm = concrete.fctm
    fyk = steel.fyk
    fyd = steel.fyd

    K = M_Nmm / (b_mm * d_mm ** 2 * fck)
    K_lim = 0.167
    note = ""
    if K > K_lim:
        z = 0.82 * d_mm
        note = "K > 0.167 — section under-reinforced; compression reinforcement required (approximation used)."
    else:
        z = d_mm * 0.5 * (1.0 + math.sqrt(max(0.0, 1.0 - 3.53 * K)))
        z = min(z, 0.95 * d_mm)

    As_req = M_Nmm / (fyd * z)
    As_min = max(0.26 * (fctm / fyk) * b_mm * d_mm, 0.0013 * b_mm * d_mm)

    return ReinforcementResult(
        As_required=As_req,
        As_min=As_min,
        As_provided=max(As_req, As_min),
        method="ec2_singly_reinforced",
        note=note,
    )


def critical_section_offset(a_mm: float, masonry_wall: bool = False) -> float:
    """Offset of the critical bending section inside the column (EHE 58.4.2):

        s1 at 0.15·a (concrete column)
        s1 at 0.25·a (masonry wall)
    """
    return 0.25 * a_mm if masonry_wall else 0.15 * a_mm


def reinforcement_distribution_rectangular_footing(
    As_total: float,
    a_prime_m: float,
    b_prime_m: float,
    h_m: float,
    a_m: float,
) -> Dict[str, float]:
    """Reinforcement distribution in a flexible rectangular footing (EHE 58.4.2):

    - Long side a': uniformly across width b'.
    - Short side b': the central strip of width b_strip ≤ a + 2h takes
      2·b'/(a'+b') of A_s; the rest goes in the lateral strips.
    """
    if a_prime_m + b_prime_m == 0:
        raise ValueError("Footing dimensions must be positive.")
    b_strip = min(b_prime_m, a_m + 2.0 * h_m)
    fraction_central = 2.0 * b_prime_m / (a_prime_m + b_prime_m)
    As_central = As_total * fraction_central
    As_lateral = As_total - As_central
    return {
        "b_strip_m": b_strip,
        "fraction_central": fraction_central,
        "As_central": As_central,
        "As_lateral": As_lateral,
    }


class FootingFlexureDetail(BaseModel):
    """Detalle de armado por flexión en una dirección de la zapata."""

    direction: str = Field(..., description="Dirección: 'X' (paralela a L) o 'Y' (paralela a B)")
    M_Ed_kNm: float = Field(..., description="Momento flector de cálculo en la sección de referencia (kNm)")
    As_req_mm2: float = Field(..., description="Área de acero requerida por cálculo (mm²)")
    As_min_mm2: float = Field(..., description="Cuantía mínima geométrica EC2 §9.2.1.1 (mm²)")
    As_prov_mm2: float = Field(..., description="Área de acero dispuesta = max(req, min) (mm²)")
    bar_diameter_mm: float = Field(..., description="Diámetro comercial de barra (mm)")
    spacing_mm: float = Field(..., description="Separación entre barras (mm)")
    n_bars: int = Field(..., description="Número total de barras")
    l_bd_mm: float = Field(..., description="Longitud básica/diseño de anclaje EC2 §8.4.4 (mm)")
    l_avail_mm: float = Field(..., description="Longitud recta disponible en el vuelo (mm)")
    hook_required: bool = Field(False, description="Indica si se requiere patilla/gancho a 90° por anclaje")
    status: str = Field("OK", description="Estado de verificación ('OK', 'HOOK_REQUIRED' o 'NO CALCULADO')")
    motivo_no_evaluado: str | None = Field(
        None, description="Por qué no se comprobó la flexión (status 'NO CALCULADO')")


def anchorage_length_ec2(
    phi_mm: float,
    fck_MPa: float,
    fyk_MPa: float = 500.0,
    As_req_mm2: float = 0.0,
    As_prov_mm2: float = 0.0,
    alpha_hook: bool = False,
    good_bond: bool = True,
) -> tuple[float, float]:
    """Calcula longitud básica l_b,rqd y de diseño l_bd de anclaje según Eurocode 2 §8.4.3/§8.4.4.

    Args:
        phi_mm: Diámetro nominal de la barra en mm.
        fck_MPa: Resistencia característica del hormigón en MPa.
        fyk_MPa: Límite elástico característico del acero en MPa (default 500).
        As_req_mm2: Área de acero requerida.
        As_prov_mm2: Área de acero provista.
        alpha_hook: True si se usa gancho a 90° (alpha1 = 0.7 para tracción).
        good_bond: True para condiciones de buena adherencia (eta1 = 1.0).

    Returns:
        Tupla (l_b_rqd_mm, l_bd_mm).
    """
    fctm = 0.30 * (fck_MPa ** (2.0 / 3.0))
    fctk_005 = 0.70 * fctm
    fctd = fctk_005 / 1.5
    eta1 = 1.0 if good_bond else 0.7
    eta2 = 1.0 if phi_mm <= 32.0 else (132.0 - phi_mm) / 100.0
    fbd = 2.25 * eta1 * eta2 * fctd  # N/mm²

    fyd = fyk_MPa / 1.15  # N/mm²
    if As_prov_mm2 > 0 and As_req_mm2 > 0:
        sigma_sd = min(fyd, fyd * (As_req_mm2 / As_prov_mm2))
    else:
        sigma_sd = fyd

    l_b_rqd = (phi_mm / 4.0) * (sigma_sd / fbd)
    alpha1 = 0.7 if alpha_hook else 1.0
    l_b_min = max(0.3 * l_b_rqd, 10.0 * phi_mm, 100.0)
    l_bd = max(alpha1 * l_b_rqd, l_b_min)
    return l_b_rqd, l_bd


def select_footing_rebar(
    As_prov_mm2: float,
    width_mm: float,
    thickness_mm: float,
    preferred_phi_mm: float = 16.0,
    cover_mm: float = 50.0,
) -> tuple[float, float, int]:
    """Selecciona diámetro comercial, separación y número de barras para una zapata.

    Cumple límites de separación EC2 §9.8.2.2: s ≤ min(2.5h, 250 mm).
    """
    commercial_bars = [10.0, 12.0, 16.0, 20.0, 25.0, 32.0]
    if preferred_phi_mm not in commercial_bars:
        preferred_phi_mm = 16.0

    s_max = min(2.5 * thickness_mm, 250.0)
    s_min = 100.0

    # Ordenar priorizando preferred_phi_mm
    ordered_bars = [preferred_phi_mm] + [b for b in commercial_bars if b != preferred_phi_mm]

    for phi in ordered_bars:
        area_bar = (math.pi * phi ** 2) / 4.0
        n_needed = math.ceil(As_prov_mm2 / area_bar)
        n_bars = max(n_needed, 3)

        effective_width = max(width_mm - 2.0 * cover_mm, 100.0)
        spacing = effective_width / max(n_bars - 1, 1)

        # Redondear espaciado a múltiplos de 10 mm hacia abajo
        spacing = math.floor(spacing / 10.0) * 10.0
        spacing = max(spacing, s_min)

        if spacing <= s_max:
            # Recalcular n_bars reales con el espaciado
            n_bars_real = math.floor(effective_width / spacing) + 1
            if n_bars_real * area_bar >= As_prov_mm2 * 0.98:
                return phi, spacing, n_bars_real

    # Fallback con preferred_phi
    area_bar = (math.pi * preferred_phi_mm ** 2) / 4.0
    n_bars = max(math.ceil(As_prov_mm2 / area_bar), 3)
    spacing = min(s_max, max(s_min, (width_mm - 2.0 * cover_mm) / (n_bars - 1)))
    return preferred_phi_mm, round(spacing, -1), n_bars


def design_footing_flexure_both_ways(
    B_m: float,
    L_m: float,
    h_m: float,
    N_Ed_kN: float,
    Mx_Ed_kNm: float = 0.0,
    My_Ed_kNm: float = 0.0,
    cx_m: float = 0.40,
    cy_m: float = 0.40,
    concrete: Concrete = Concrete(fck=30),
    steel: ReinforcingSteel = ReinforcingSteel(fyk=500),
    cover_mm: float = 50.0,
    preferred_phi_mm: float = 16.0,
) -> dict[str, FootingFlexureDetail]:
    """Diseña la armadura por flexión en ambas direcciones (X e Y) de una zapata aislada.

    Calcula momentos en las secciones de referencia críticas (cara de columna + 0.15*a),
    aplica cuantías mínimas de flexión EC2 §9.2.1.1 / §9.8.2, selecciona barras y
    comprueba la longitud de anclaje en el vuelo.
    """
    if B_m <= 0 or L_m <= 0 or h_m <= 0:
        raise ValueError("Dimensiones de zapata deben ser positivas.")

    # 1. Presión media y brazos de palanca al voladizo
    # Vuelo en dirección X (paralelo a L): vx = (L - cx)/2 + 0.15*cx
    # Vuelo en dirección Y (paralelo a B): vy = (B - cy)/2 + 0.15*cy
    vx_m = max((L_m - cx_m) / 2.0 + 0.15 * cx_m, 0.10)
    vy_m = max((B_m - cy_m) / 2.0 + 0.15 * cy_m, 0.10)

    # Presión de FLEXIÓN (B48, §8.19). Antes: `q_avg = max(N/A, 0)`, y los
    # momentos Mx_Ed/My_Ed que esta función RECIBE no se usaban en ninguna parte.
    # Con e_x = L/6 la presión de borde es el doble de la media y el plano salía
    # con la mitad del momento. Se reutiliza la presión del PROPIO paquete
    # (`services/footings._compute_pressures`, con sus ramas de despegue) y su
    # regla `q_flex = q_max` («conservador para flexión», footings.py:168).
    # Convenio de ejes, el de ese módulo y el de reaction_bridge: e_x = My/N a lo
    # largo de L (L_x), e_y = Mx/N a lo largo de B (L_y). Una zapata cuadrada
    # tapa un cruce de ejes: el test usa una excentricidad en UNA sola dirección.
    from types import SimpleNamespace
    from ..services.footings import _compute_pressures

    motivo = None
    if N_Ed_kN <= 0.0:
        motivo = (f"N_Ed = {N_Ed_kN:+.1f} kN <= 0: no hay presión portante. La flexión "
                  "por levantamiento (anclajes, columna a tracción) no la calcula "
                  "este módulo; se dispone la cuantía MÍNIMA, que es un requisito "
                  "geométrico, no un armado comprobado.")
        q_flex_kPa = 0.0
    else:
        presiones, notas = _compute_pressures(SimpleNamespace(
            L_x=L_m, L_y=B_m, N=N_Ed_kN, M_x=Mx_Ed_kNm, M_y=My_Ed_kNm))
        q_flex_kPa = float(presiones["q_max"])
        if not math.isfinite(q_flex_kPa):
            motivo = ("resultante fuera de la base (e >= L/2): presión no acotada, "
                      "flexión no calculable. " + " ".join(notas))
            q_flex_kPa = 0.0

    # Momentos flectores en la sección de referencia
    # M_Ed_X (actúa sobre ancho B, brazo vx):
    M_Ed_x = q_flex_kPa * B_m * (vx_m ** 2) / 2.0
    # M_Ed_Y (actúa sobre longitud L, brazo vy):
    M_Ed_y = q_flex_kPa * L_m * (vy_m ** 2) / 2.0

    # 2. Diseño por flexión en X (paralelo a L)
    b_x_mm = B_m * 1000.0
    d_x_mm = max((h_m * 1000.0) - cover_mm - (preferred_phi_mm / 2.0), 100.0)
    res_x = flexural_reinforcement(M_Ed_x, b_x_mm, d_x_mm, concrete, steel)
    phi_x, s_x, n_x = select_footing_rebar(res_x.As_provided, b_x_mm, h_m * 1000.0, preferred_phi_mm, cover_mm)
    As_prov_x = n_x * (math.pi * phi_x ** 2) / 4.0
    _, l_bd_x = anchorage_length_ec2(phi_x, concrete.fck, steel.fyk, res_x.As_required, As_prov_x)
    l_avail_x = max(((L_m - cx_m) / 2.0 * 1000.0) - cover_mm, 50.0)
    hook_x = l_bd_x > l_avail_x

    detail_x = FootingFlexureDetail(
        direction="X",
        M_Ed_kNm=M_Ed_x,
        As_req_mm2=res_x.As_required,
        As_min_mm2=res_x.As_min,
        As_prov_mm2=As_prov_x,
        bar_diameter_mm=phi_x,
        spacing_mm=s_x,
        n_bars=n_x,
        l_bd_mm=l_bd_x,
        l_avail_mm=l_avail_x,
        hook_required=hook_x,
        status="NO CALCULADO" if motivo else ("HOOK_REQUIRED" if hook_x else "OK"),
        motivo_no_evaluado=motivo,
    )

    # 3. Diseño por flexión en Y (paralelo a B)
    b_y_mm = L_m * 1000.0
    d_y_mm = max(d_x_mm - phi_x, 100.0)  # capa superior del emparrillado
    res_y = flexural_reinforcement(M_Ed_y, b_y_mm, d_y_mm, concrete, steel)
    phi_y, s_y, n_y = select_footing_rebar(res_y.As_provided, b_y_mm, h_m * 1000.0, preferred_phi_mm, cover_mm)
    As_prov_y = n_y * (math.pi * phi_y ** 2) / 4.0
    _, l_bd_y = anchorage_length_ec2(phi_y, concrete.fck, steel.fyk, res_y.As_required, As_prov_y)
    l_avail_y = max(((B_m - cy_m) / 2.0 * 1000.0) - cover_mm, 50.0)
    hook_y = l_bd_y > l_avail_y

    detail_y = FootingFlexureDetail(
        direction="Y",
        M_Ed_kNm=M_Ed_y,
        As_req_mm2=res_y.As_required,
        As_min_mm2=res_y.As_min,
        As_prov_mm2=As_prov_y,
        bar_diameter_mm=phi_y,
        spacing_mm=s_y,
        n_bars=n_y,
        l_bd_mm=l_bd_y,
        l_avail_mm=l_avail_y,
        hook_required=hook_y,
        status="NO CALCULADO" if motivo else ("HOOK_REQUIRED" if hook_y else "OK"),
        motivo_no_evaluado=motivo,
    )

    return {"X": detail_x, "Y": detail_y}

