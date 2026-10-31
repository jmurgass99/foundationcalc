"""AISC 360-22 -- conexiones acero. Placa base, soldadura filete, pernos.

- Placa base (Design Guide 1 + Cap. J8): area requerida por aplastamiento,
  espesor por flexion del voladizo.
- Soldadura filete (J2): resistencia por longitud, Fnw = 0.6*FEXX*(1+0.5*sin^1.5(theta)).
- Pernos (J3): cortante (Fnv), traccion (Fnt) e interaccion.
- Aplastamiento en agujeros (J3.10).

Unidades: N, mm, MPa. phi de Cap. J: weld=0.75, bolt=0.75, base plate=0.65.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Literal


PHI_WELD = 0.75
PHI_BOLT = 0.75
PHI_BASE = 0.65


@dataclass
class BasePlateResult:
    A1_req: Optional[float]   # area requerida (mm^2); None = no evaluado
    A1: float
    fp_max: float       # presion maxima admisible (MPa)
    m: float; n: float; l: float   # voladizos
    tp_req: Optional[float]   # espesor minimo (mm); None = no evaluado
    ok: Optional[bool]        # None = fuera del alcance de DG-1 (ver motivo)
    #: Por que no se evaluo. Patron `DesignCheckMemoir.motivo_no_evaluado`.
    motivo_no_evaluado: Optional[str] = None


def design_base_plate(*, Pu: float, fc: float, B: float, N: float,
                       d: float, bf: float, Fy_plate: float,
                       A2_over_A1: float = 4.0) -> BasePlateResult:
    """Placa base bajo compresion concentrica (AISC DG-1).

    Args:
        Pu: axial factorizada (N), POSITIVO = COMPRESION (el convenio de
            `aisc_360.interaction_H1` y de SteelConnectionJm). Un Pu < 0 es un
            LEVANTAMIENTO y queda fuera del alcance de este metodo: ver abajo.
        fc: f'c del pedestal (MPa).
        B, N: dimensiones de la placa (mm).
        d, bf: peralte y ancho de aleta del perfil (mm).
        Fy_plate: fy de la placa (MPa).
        A2_over_A1: relacion de area de aplastamiento (max 4).
    """
    A1 = B * N
    sqrt_ratio = min(math.sqrt(A2_over_A1), 2.0)
    fp_max = 0.85 * fc * sqrt_ratio       # phi se aplica abajo
    m = (N - 0.95 * d) / 2.0
    n = (B - 0.80 * bf) / 2.0
    if Pu < 0:
        # DG-1 es, por su titulo, COMPRESION CONCENTRICA: dimensiona la placa
        # por aplastamiento del hormigon bajo ella. Un LEVANTAMIENTO no aplasta
        # nada: lo que gobierna es la traccion en los anclajes, la flexion de la
        # placa por esos anclajes y el cono del hormigon, y nada de eso se
        # calcula aqui.
        #
        # Antes se evaluaba con `abs(Pu)` y un levantamiento de 150 kN daba un
        # resultado IDENTICO al de 150 kN de compresion, ok=True. Estrictamente
        # menor: un Pu = 0 MEDIDO se sigue evaluando.
        return BasePlateResult(
            A1_req=None, A1=A1, fp_max=fp_max, m=m, n=n, l=max(m, n),
            tp_req=None, ok=None,
            motivo_no_evaluado=(
                f"Pu = {Pu:+.4g} N < 0 (levantamiento): fuera del alcance de "
                "AISC DG-1 (compresion concentrica). Traccion en anclajes, "
                "flexion de placa y cono de hormigon NO evaluados"
            ),
        )
    A1_req = Pu / (PHI_BASE * 0.85 * fc * sqrt_ratio)
    # n' = sqrt(d*bf)/4
    n_p = math.sqrt(d * bf) / 4.0
    # X = (4*d*bf/(d+bf)^2) * Pu/(phi*Pp)
    Pp = 0.85 * fc * A1 * sqrt_ratio
    X = (4.0 * d * bf / (d + bf) ** 2) * Pu / max(PHI_BASE * Pp, 1e-9)
    lam = 2.0 * math.sqrt(X) / (1.0 + math.sqrt(max(1.0 - X, 0.0))) if X < 1.0 else 1.0
    l = max(m, n, lam * n_p)
    fp = Pu / A1
    tp_req = l * math.sqrt(2.0 * fp / (0.90 * Fy_plate))
    return BasePlateResult(
        A1_req=A1_req, A1=A1, fp_max=fp_max,
        m=m, n=n, l=l, tp_req=tp_req,
        ok=(A1 >= A1_req),
    )


@dataclass
class FilletWeldResult:
    Rn_per_mm: float    # N/mm por linea
    phi_Rn_per_mm: float
    Lreq_mm: float
    theta_deg: float
    ok: bool


def fillet_weld_strength(*, w: float, FEXX: float, theta_deg: float = 0.0,
                          Ru: float = 0.0) -> FilletWeldResult:
    """Resistencia de soldadura filete por unidad de longitud (AISC J2.4).

    Rn = 0.6 * FEXX * te * (1.0 + 0.5*sin^1.5(theta))
    te = 0.707*w (filete).
    """
    te = 0.707 * w
    fac = 1.0 + 0.5 * math.sin(math.radians(theta_deg)) ** 1.5
    Rn = 0.6 * FEXX * te * fac
    phi_Rn = PHI_WELD * Rn
    Lreq = abs(Ru) / max(phi_Rn, 1e-9) if Ru > 0 else 0.0
    return FilletWeldResult(
        Rn_per_mm=Rn, phi_Rn_per_mm=phi_Rn,
        Lreq_mm=Lreq, theta_deg=theta_deg, ok=True,
    )


@dataclass
class BoltShearResult:
    phi_Rn: float       # N por perno
    n_req: float
    ok: bool


def bolt_shear_capacity(*, Ab: float, Fnv: float, n_bolts: int = 1,
                         Vu: float = 0.0,
                         threads_in_plane: bool = True) -> BoltShearResult:
    """Cortante por perno (AISC J3.6). Fnv tipico A325-N=372 MPa, A325-X=457."""
    Rn_per = Fnv * Ab
    phi_Rn_total = PHI_BOLT * Rn_per * n_bolts
    n_req = abs(Vu) / max(PHI_BOLT * Rn_per, 1e-9) if Vu > 0 else 0.0
    return BoltShearResult(phi_Rn=phi_Rn_total, n_req=n_req,
                            ok=phi_Rn_total >= abs(Vu))


def bolt_tension_capacity(*, Ab: float, Fnt: float, n_bolts: int = 1) -> float:
    """Traccion por perno (AISC J3.6). Devuelve phi*Rn total (N)."""
    return PHI_BOLT * Fnt * Ab * n_bolts


def bolt_combined(*, fv: float, Fnv: float, Fnt: float) -> dict:
    """Interaccion traccion-cortante (J3.7): Fnt' = 1.3*Fnt - Fnt/(phi*Fnv)*fv <= Fnt.

    Args:
        fv: tension cortante actuante (MPa).
        Fnv, Fnt: nominales (MPa).
    """
    Fnt_prime = min(1.3 * Fnt - Fnt / (PHI_BOLT * Fnv) * fv, Fnt)
    return {"Fnt_prime": max(Fnt_prime, 0.0),
            "phi_rn_per_area": PHI_BOLT * max(Fnt_prime, 0.0)}


def bearing_at_bolt_hole(*, d: float, t: float, Fu: float,
                          Lc: float, deformation_ok: bool = True) -> float:
    """Aplastamiento en agujero (J3.10): phi*Rn por perno (N).

    Rn = min(1.2*Lc*t*Fu, 2.4*d*t*Fu) si deformacion aceptable;
    si no, 1.5*Lc*t*Fu y 3.0*d*t*Fu.
    """
    a, b = (1.2, 2.4) if deformation_ok else (1.5, 3.0)
    Rn = min(a * Lc * t * Fu, b * d * t * Fu)
    return PHI_BOLT * Rn


__all__ = [
    "BasePlateResult", "FilletWeldResult", "BoltShearResult",
    "design_base_plate", "fillet_weld_strength",
    "bolt_shear_capacity", "bolt_tension_capacity",
    "bolt_combined", "bearing_at_bolt_hole",
]
