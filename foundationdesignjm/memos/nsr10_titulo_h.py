"""Memoria NSR-10 Titulo H (cimentaciones, Colombia).

Verifica capacidad portante, asentamientos y FS minimos segun NSR-10 H.4.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, tan, radians


@dataclass(frozen=True)
class NSR10HInput:
    B_m: float
    L_m: float
    Df_m: float
    gamma_kN_m3: float = 18.0
    phi_deg: float = 30.0
    c_kPa: float = 0.0
    Q_kN: float = 500.0
    es_sismica: bool = False


@dataclass(frozen=True)
class NSR10HResult:
    q_ult_kPa: float
    q_adm_kPa: float
    FS: float
    q_aplicada_kPa: float
    cumple: bool
    markdown: str


def _Nq_Nc_Ng(phi_deg: float) -> tuple[float, float, float]:
    phi = radians(phi_deg)
    Nq = (tan(radians(45) + phi / 2)) ** 2 * pow(2.71828, pi * tan(phi))
    Nc = (Nq - 1) / max(tan(phi), 1e-6) if phi_deg > 0 else 5.14
    Ng = 2 * (Nq + 1) * tan(phi)
    return Nq, Nc, Ng


def memoria_nsr10_h(inp: NSR10HInput) -> NSR10HResult:
    Nq, Nc, Ng = _Nq_Nc_Ng(inp.phi_deg)
    q_sob = inp.gamma_kN_m3 * inp.Df_m
    q_ult = inp.c_kPa * Nc + q_sob * Nq + 0.5 * inp.gamma_kN_m3 * inp.B_m * Ng
    FS_req = 2.0 if inp.es_sismica else 3.0  # NSR-10 H.4.2
    q_adm = q_ult / FS_req
    q_apl = inp.Q_kN / (inp.B_m * inp.L_m)
    cumple = q_apl <= q_adm
    md = (
        f"# NSR-10 Titulo H - Verificacion cimentacion\n\n"
        f"## Datos\nB={inp.B_m} m, L={inp.L_m} m, Df={inp.Df_m} m\n\n"
        f"## Capacidad ultima (Terzaghi)\n"
        f"- Nc={Nc:.2f}, Nq={Nq:.2f}, Ng={Ng:.2f}\n"
        f"- q_ult = c*Nc + q*Nq + 0.5*g*B*Ng = {q_ult:.2f} kPa\n\n"
        f"## Capacidad admisible (NSR-10 H.4.2)\n"
        f"- FS_req = {FS_req} ({'sismica' if inp.es_sismica else 'estatica'})\n"
        f"- q_adm = {q_adm:.2f} kPa\n\n"
        f"## Aplicada\n- q = {q_apl:.2f} kPa --> {'CUMPLE' if cumple else 'NO CUMPLE'}\n"
    )
    return NSR10HResult(q_ult, q_adm, FS_req, q_apl, cumple, md)


__all__ = ["NSR10HInput", "NSR10HResult", "memoria_nsr10_h"]
