"""Servicios de diseño de pilotes."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PileAxialInput:
    D: float              # diámetro (m)
    L: float              # longitud (m)
    fc_MPa: float = 25.0
    layers_qu_kPa: tuple[float, ...] = ()    # resistencia cohesiva por capa
    layers_thickness: tuple[float, ...] = ()
    Nq_tip: float = 9.0


@dataclass(frozen=True)
class PileAxialResult:
    Q_skin_kN: float
    Q_tip_kN: float
    Q_ultimate_kN: float
    Q_allowable_kN: float
    FS: float
    notes: list[str]


def design_pile_axial(inp: PileAxialInput) -> PileAxialResult:
    """Capacidad axial de pilote en suelo cohesivo (α-method)."""
    import math
    perimeter = math.pi * inp.D
    Q_skin = 0.0
    depth = 0.0
    for qu, t in zip(inp.layers_qu_kPa, inp.layers_thickness):
        alpha = 0.5  # típico para arcillas medianas
        Q_skin += alpha * qu * perimeter * t
        depth += t
    A_tip = math.pi * inp.D ** 2 / 4
    qu_tip = inp.layers_qu_kPa[-1] if inp.layers_qu_kPa else 0.0
    Q_tip = inp.Nq_tip * qu_tip * A_tip
    Q_ult = Q_skin + Q_tip
    FS = 3.0
    Q_allow = Q_ult / FS
    return PileAxialResult(
        Q_skin_kN=Q_skin, Q_tip_kN=Q_tip,
        Q_ultimate_kN=Q_ult, Q_allowable_kN=Q_allow, FS=FS,
        notes=[f"Q_skin = {Q_skin:.1f} kN, Q_tip = {Q_tip:.1f} kN",
               f"Q_admisible = {Q_allow:.1f} kN (FS = {FS})"],
    )
