"""Servicios de diseño de muros de contención."""
from __future__ import annotations

import math
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
    cohesion_soil: float = 0.0
    embedment_front: float = 0.8
    evaluate_bearing: bool = False


@dataclass(frozen=True)
class WallDesignResult:
    sliding_FS: float
    overturning_FS: float
    #: None = NO EVALUADO cuando evaluate_bearing=False. Si evaluate_bearing=True, devuelve q_Rd / q_Ed.
    bearing_FS: float | None
    stem_design: dict
    notes: list[str]


def design_cantilever_wall_ec7(inp: CantileverWallInput) -> WallDesignResult:
    """Evalúa el muro en ménsula con ``CantileverWallDesigner`` (EN 1997-1) incluyendo capacidad portante."""
    from foundationcalc.core.material import Concrete
    from foundationcalc.core.soil import SoilLayer, SoilType
    from foundationcalc.design.retaining_wall import (
        CantileverWallDesigner,
        CantileverWallGeometry,
        RetainingWallLoading,
    )

    t_base = 0.30
    geo = CantileverWallGeometry(
        H=inp.H,
        stem_top=inp.stem_thickness,
        stem_bottom=inp.stem_thickness,
        toe=inp.toe_width,
        heel=inp.heel_width,
        base_thickness=t_base,
        embedment_front=inp.embedment_front,
    )
    soil = SoilLayer(
        name="BackfillAndFoundation",
        thickness=10.0,
        soil_type=SoilType.COHESIONLESS if inp.phi_soil > 0 else SoilType.COHESIVE,
        unit_weight=inp.gamma_soil,
        friction_angle=inp.phi_soil,
        cohesion=inp.cohesion_soil,
    )
    loading = RetainingWallLoading(
        backfill=soil,
        foundation_soil=soil,
        surcharge_q=inp.surcharge_kPa,
        analysis_method="rankine_virtual_back",
        use_coulomb=False,
    )
    concrete = Concrete(f_ck=inp.fc_MPa)
    designer = CantileverWallDesigner(geometry=geo, loading=loading, concrete=concrete)
    chk = designer.check()
    bearing_fs = chk.bearing_q_Rd / max(chk.bearing_q_Ed, 1e-9)
    sliding_fs = chk.sliding_H_Rd / max(chk.sliding_H_Ed, 1e-9)
    overturning_fs = 1.0 / max(chk.overturning_utilization, 1e-9)
    return WallDesignResult(
        sliding_FS=sliding_fs,
        overturning_FS=overturning_fs,
        bearing_FS=bearing_fs,
        stem_design={
            "M_stem": chk.M_stem_base,
            "V_stem": chk.V_stem_base,
            "M_heel": chk.M_heel,
            "M_toe": chk.M_toe,
            "bearing_q_Ed_kPa": chk.bearing_q_Ed,
            "bearing_q_Rd_kPa": chk.bearing_q_Rd,
            "thickness_min_mm": inp.stem_thickness * 1000.0,
        },
        notes=[
            f"EN 1997-1 ({chk.design_approach}): q_Ed = {chk.bearing_q_Ed:.1f} kPa, q_Rd = {chk.bearing_q_Rd:.1f} kPa",
            f"FS sliding = {sliding_fs:.2f}, FS overturning = {overturning_fs:.2f}, FS bearing = {bearing_fs:.2f}",
        ],
    )


def design_cantilever_wall(inp: CantileverWallInput) -> WallDesignResult:
    """Predimensionado de muro en ménsula con factores de seguridad globales.

    Si ``inp.evaluate_bearing=True``, evalúa también la capacidad portante del
    cimiento mediante ``CantileverWallDesigner`` (EN 1997-1 Anexo D con ancho
    efectivo de Meyerhof ``B' = B - 2|e|``). Por defecto (``evaluate_bearing=False``)
    mantiene ``bearing_FS=None`` para compatibilidad con el predimensionado Rankine.
    """
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

    bearing_FS: float | None = None
    stem_design: dict = {
        "M_stem": Pa_total * inp.H / 3,
        "thickness_min_mm": inp.stem_thickness * 1000,
    }
    notes = [
        f"Ka = {Ka:.3f}",
        f"Pa = {Pa_total:.1f} kN/m",
        f"FS sliding = {sliding_FS:.2f}, FS overturning = {overturning_FS:.2f}",
    ]

    if inp.evaluate_bearing:
        ec7_res = design_cantilever_wall_ec7(inp)
        bearing_FS = ec7_res.bearing_FS
        stem_design["bearing_q_Ed_kPa"] = ec7_res.stem_design["bearing_q_Ed_kPa"]
        stem_design["bearing_q_Rd_kPa"] = ec7_res.stem_design["bearing_q_Rd_kPa"]
        notes.append(
            f"Capacidad portante evaluada (EN 1997-1): bearing_FS = {bearing_FS:.2f}"
        )
    else:
        notes.append(
            "Capacidad portante NO evaluada (bearing_FS = None); base de "
            f"{t_base:.2f} m de canto supuesta."
        )

    return WallDesignResult(
        sliding_FS=sliding_FS,
        overturning_FS=overturning_FS,
        bearing_FS=bearing_FS,
        stem_design=stem_design,
        notes=notes,
    )


__all__ = [
    "CantileverWallInput",
    "WallDesignResult",
    "design_cantilever_wall",
    "design_cantilever_wall_ec7",
]
