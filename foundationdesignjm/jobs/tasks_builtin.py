"""Tasks built-in para FoundationDesignJm."""
from __future__ import annotations
from typing import Callable

from .queue import register_task
from .models import ProgressUpdate


@register_task("design_footing")
def task_design_footing(payload: dict, *, report_progress: Callable) -> dict:
    from foundationdesignjm.services.footings import (
        IsolatedFootingInput, design_isolated_footing,
    )
    report_progress(ProgressUpdate(0.2, "Construyendo input..."))
    res = design_isolated_footing(IsolatedFootingInput(**payload))
    report_progress(ProgressUpdate(0.9, "Empacando resultados..."))
    return {
        "pressures": res.pressures,
        "punching": res.punching,
        "flexure_x": res.flexure_x,
        "flexure_y": res.flexure_y,
        "notes": res.notes,
    }


@register_task("design_wall")
def task_design_wall(payload: dict, *, report_progress: Callable) -> dict:
    from foundationdesignjm.services.walls import (
        CantileverWallInput, design_cantilever_wall,
    )
    report_progress(ProgressUpdate(0.3, "Analizando muro..."))
    res = design_cantilever_wall(CantileverWallInput(**payload))
    return {
        "sliding_FS": res.sliding_FS,
        "overturning_FS": res.overturning_FS,
        "bearing_FS": res.bearing_FS,
        "stem_design": res.stem_design,
        "notes": res.notes,
    }


@register_task("design_pile_axial")
def task_design_pile_axial(payload: dict, *, report_progress: Callable) -> dict:
    from foundationdesignjm.services.piles import (
        PileAxialInput, design_pile_axial,
    )
    # tuplas no son JSON-friendly: payload puede traer listas
    if "layers_qu_kPa" in payload:
        payload["layers_qu_kPa"] = tuple(payload["layers_qu_kPa"])
    if "layers_thickness" in payload:
        payload["layers_thickness"] = tuple(payload["layers_thickness"])
    report_progress(ProgressUpdate(0.4, "Calculando capacidad pilote..."))
    res = design_pile_axial(PileAxialInput(**payload))
    return {
        "Q_skin_kN": res.Q_skin_kN,
        "Q_tip_kN": res.Q_tip_kN,
        "Q_ultimate_kN": res.Q_ultimate_kN,
        "Q_allowable_kN": res.Q_allowable_kN,
        "FS": res.FS,
        "notes": res.notes,
    }


@register_task("bearing_capacity")
def task_bearing_capacity(payload: dict, *, report_progress: Callable) -> dict:
    from foundationdesignjm.services.bearing import (
        BearingInput, SoilLayerSpec, bearing_capacity_multilayer,
    )
    report_progress(ProgressUpdate(0.3, "Resolviendo capacidad portante..."))
    layers = tuple(SoilLayerSpec(**l) for l in payload.pop("layers", []))
    res = bearing_capacity_multilayer(BearingInput(layers=layers, **payload))
    return {
        "qu_kPa": res.qu_kPa,
        "qa_kPa": res.qa_kPa,
        "FS": res.FS,
        "method": res.method,
        "notes": res.notes,
    }


@register_task("mononobe_okabe")
def task_mononobe_okabe(payload: dict, *, report_progress: Callable) -> dict:
    from foundationdesignjm.services.seismic import (
        MononobeOkabeInput, mononobe_okabe_thrust,
    )
    report_progress(ProgressUpdate(0.3, "Calculando empuje sísmico..."))
    res = mononobe_okabe_thrust(MononobeOkabeInput(**payload))
    return {
        "K_AE": res.K_AE,
        "P_AE_kN_per_m": res.P_AE,
        "theta_deg": res.theta,
        "notes": res.notes,
    }
