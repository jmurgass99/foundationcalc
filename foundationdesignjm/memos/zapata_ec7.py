"""Memoria EC7 zapata aislada - capacidad portante drenada (Brinch Hansen).

Genera memoria de calculo paso-a-paso renderizable en LaTeX via handcalcs.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

try:
    from handcalcs.decorator import handcalc
    _HAS_HANDCALCS = True
except ImportError:
    _HAS_HANDCALCS = False
    def handcalc(*args, **kwargs):
        def deco(f): return f
        return deco


@dataclass
class FootingBearingResult:
    """Resultado del calculo de capacidad portante."""
    R_ult_kN: float          # capacidad ultima
    R_d_kN: float            # capacidad de diseno
    sigma_ult_kPa: float     # tension ultima
    sigma_d_kPa: float       # tension de diseno
    N_q: float               # factor capacidad
    N_c: float
    N_gamma: float
    is_safe: bool            # R_d >= R_Ed
    latex: str = ""
    notes: list[str] = field(default_factory=list)


@handcalc(override="long", precision=3)
def _bearing_capacity(B, L, D_f, gamma_soil, c, phi_rad, gamma_R):
    N_q = math.exp(math.pi * math.tan(phi_rad)) * (math.tan(math.pi / 4 + phi_rad / 2)) ** 2
    N_c = (N_q - 1) / math.tan(phi_rad)
    N_gamma = 2 * (N_q - 1) * math.tan(phi_rad)
    s_q = 1 + (B / L) * math.sin(phi_rad)
    s_c = 1 + (B / L) * (N_q / N_c)
    s_gamma = 1 - 0.4 * (B / L)
    d_q = 1 + 2 * math.tan(phi_rad) * (1 - math.sin(phi_rad)) ** 2 * (D_f / B)
    d_c = d_q - (1 - d_q) / (N_c * math.tan(phi_rad))
    d_gamma = 1
    q_0 = gamma_soil * D_f
    sigma_ult = c * N_c * s_c * d_c + q_0 * N_q * s_q * d_q + 0.5 * gamma_soil * B * N_gamma * s_gamma * d_gamma
    R_ult = sigma_ult * B * L
    R_d = R_ult / gamma_R
    sigma_d = R_d / (B * L)
    return sigma_ult, R_ult, R_d, sigma_d, N_q, N_c, N_gamma


def footing_ec7_bearing_memo(B, L, D_f, gamma_soil, c, phi_deg, R_Ed,
                                gamma_R=1.4):
    """Genera memoria + verifica capacidad portante drenada EC7 6.5.

    Args:
        B: ancho menor zapata (m)
        L: largo zapata (m), L >= B
        D_f: profundidad de cimentacion (m)
        gamma_soil: peso especifico suelo (kN/m3)
        c: cohesion efectiva (kPa)
        phi_deg: angulo friccion efectivo (grados)
        R_Ed: solicitacion (kN)
        gamma_R: factor parcial resistencia EC7 (DA-2: 1.4)

    Returns:
        (latex_str, FootingBearingResult)
    """
    if B <= 0 or L <= 0 or D_f < 0:
        raise ValueError("B, L deben ser positivos; D_f no negativo")
    if L < B:
        raise ValueError("L debe ser >= B (B es el lado menor)")
    if phi_deg < 0 or phi_deg >= 50:
        raise ValueError("phi_deg debe estar en [0, 50)")
    if R_Ed < 0:
        raise ValueError("R_Ed no puede ser negativo")

    phi_rad = math.radians(phi_deg)
    latex, (sigma_ult, R_ult, R_d, sigma_d, N_q, N_c, N_gamma) = _bearing_capacity(
        B, L, D_f, gamma_soil, c, phi_rad, gamma_R,
    )
    is_safe = R_d >= R_Ed
    return latex, FootingBearingResult(
        R_ult_kN=float(R_ult), R_d_kN=float(R_d),
        sigma_ult_kPa=float(sigma_ult), sigma_d_kPa=float(sigma_d),
        N_q=float(N_q), N_c=float(N_c), N_gamma=float(N_gamma),
        is_safe=bool(is_safe), latex=latex,
        notes=[
            f"phi = {phi_deg:.1f} deg, N_q = {N_q:.2f}, N_c = {N_c:.2f}, N_gamma = {N_gamma:.2f}",
            f"R_Ed = {R_Ed:.1f} kN vs R_d = {R_d:.1f} kN ({'OK' if is_safe else 'NO CUMPLE'})",
            f"Factor utilizacion: {R_Ed / R_d * 100:.1f}%",
        ],
    )
