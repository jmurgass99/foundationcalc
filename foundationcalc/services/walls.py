"""Servicios de diseño de muros de contención."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CantileverWallInput:
    H: float
    base_width: float
    stem_thickness: float
    toe_width: float
    heel_width: float
    fc_MPa: float = 25.0
    fy_MPa: float = 420.0
    gamma_soil: float = 18.0
    phi_soil: float = 30.0
    surcharge_kPa: float = 10.0


@dataclass(frozen=True)
class WallDesignResult:
    sliding_FS: float
    overturning_FS: float
    #: None = NO EVALUADO. Este servicio no calcula la capacidad portante.
    bearing_FS: float | None
    stem_design: dict
    notes: list[str]


def design_cantilever_wall(inp: CantileverWallInput) -> WallDesignResult:
    """Predimensionado de muro en ménsula con factores de seguridad globales.

    Rankine sin talud, base de 0,30 m de canto fija, pesos con su brazo real
    respecto a la puntera. No es una comprobación EN 1997-1 (para eso,
    `design.retaining_wall.CantileverWallDesigner`) y NO calcula la capacidad
    portante: `bearing_FS` sale None.

    DEFECTOS CORREGIDOS (1.1.0): `bearing_FS` devolvía un 3.0 fijo
    («placeholder») que se leía como comprobación superada, y el momento
    estabilizador ponía TODOS los pesos en B/2 (el relleno del talón, que es
    el mayor, está más lejos: el FS al vuelco salía bajo).
    """
    import math
    # Empuje activo Rankine
    Ka = math.tan(math.radians(45 - inp.phi_soil / 2)) ** 2
    Pa = 0.5 * Ka * inp.gamma_soil * inp.H ** 2
    Pa_surcharge = Ka * inp.surcharge_kPa * inp.H
    Pa_total = Pa + Pa_surcharge
    M_over = Pa * inp.H / 3 + Pa_surcharge * inp.H / 2
    # Pesos y brazos respecto a la puntera (x desde el borde de la puntera)
    t_base = 0.3
    W_stem = 24.0 * inp.stem_thickness * inp.H
    W_base = 24.0 * inp.base_width * t_base
    W_soil_heel = inp.gamma_soil * inp.heel_width * inp.H
    W_total = W_stem + W_base + W_soil_heel
    x_stem = inp.toe_width + inp.stem_thickness / 2.0
    x_base = inp.base_width / 2.0
    x_heel = inp.toe_width + inp.stem_thickness + inp.heel_width / 2.0
    M_resist = W_stem * x_stem + W_base * x_base + W_soil_heel * x_heel
    # FS
    overturning_FS = M_resist / M_over if M_over > 0 else 99
    sliding_FS = W_total * math.tan(math.radians(2 / 3 * inp.phi_soil)) / Pa_total
    return WallDesignResult(
        sliding_FS=sliding_FS, overturning_FS=overturning_FS,
        bearing_FS=None,
        stem_design={"M_stem": Pa_total * inp.H / 3,
                     "thickness_min_mm": inp.stem_thickness * 1000},
        notes=[f"Ka = {Ka:.3f}", f"Pa = {Pa_total:.1f} kN/m",
               f"FS sliding = {sliding_FS:.2f}, FS overturning = {overturning_FS:.2f}",
               "Capacidad portante NO evaluada (bearing_FS = None); base de "
               f"{t_base:.2f} m de canto supuesta."],
    )
