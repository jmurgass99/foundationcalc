"""foundationdesignjm.reaction_bridge
====================================
Puente puro de datos entre las reacciones de apoyo (jmstructural-common / fastsap)
y las funciones de dimensionamiento y chequeo geotécnico de FoundationDesignJm.

Convierte instancias canónicas de Reaction en PointLoad y calcula el dimensionado
en planta de zapatas aisladas cuadradas bajo criterio de presión admisible de servicio.
Cero llamadas COM.
"""
from __future__ import annotations
import math
from typing import Any, Sequence

from foundationdesignjm.core.loading import ActionCategory, LoadType, PointLoad
from jmstructural_common.model import Model, Reaction


def reaction_to_point_load(
    reaction: Reaction,
    load_type: LoadType = LoadType.PERMANENT,
    category: ActionCategory = ActionCategory.DEFAULT,
) -> PointLoad:
    """Convierte una Reaction de nudo en un PointLoad de FoundationDesignJm."""
    return PointLoad(
        name=f"Reaction_{reaction.node_id}_{reaction.case}",
        fz=abs(float(reaction.fz_kN)),
        mx=abs(float(reaction.mx_kNm)),
        my=abs(float(reaction.my_kNm)),
        vx=abs(float(reaction.fx_kN)),
        vy=abs(float(reaction.fy_kN)),
        load_type=load_type,
        category=category,
    )


def _round_up_step(val: float, step: float) -> float:
    if step <= 0.0:
        return val
    return math.ceil(val / step - 1e-9) * step


def size_isolated_footing_from_reactions(
    reactions: Sequence[Reaction],
    allowable_bearing_kPa: float = 200.0,
    min_size_m: float = 1.0,
    size_step_m: float = 0.05,
) -> dict[str, dict[str, Any]]:
    """Dimensiona en planta zapatas aisladas cuadradas a partir de las reacciones de apoyo.

    Args:
        reactions: Secuencia de reacciones canónicas.
        allowable_bearing_kPa: Presión admisible de servicio del terreno en kPa.
        min_size_m: Dimensión mínima de lado de zapata en metros.
        size_step_m: Paso constructivo de redondeo hacia arriba.

    Returns:
        Diccionario {node_id: {"N_max_kN": ..., "B_m": ..., "L_m": ..., "q_act_kPa": ..., "qa_kPa": ..., "status": ...}}
    """
    if allowable_bearing_kPa <= 0.0:
        raise ValueError(f"allowable_bearing_kPa debe ser > 0, obtenido {allowable_bearing_kPa}")

    # Agrupar por nudo
    by_node: dict[str, list[Reaction]] = {}
    for rx in reactions:
        by_node.setdefault(rx.node_id, []).append(rx)

    results: dict[str, dict[str, Any]] = {}

    for node_id, rx_list in by_node.items():
        n_max = max(abs(float(r.fz_kN)) for r in rx_list)
        if n_max <= 0.0:
            side = min_size_m
            q_act = 0.0
        else:
            a_req = n_max / allowable_bearing_kPa
            side_raw = math.sqrt(a_req)
            side = max(_round_up_step(side_raw, size_step_m), min_size_m)
            area = side * side
            q_act = n_max / area

        results[node_id] = {
            "node_id": node_id,
            "N_max_kN": n_max,
            "B_m": side,
            "L_m": side,
            "area_m2": side * side,
            "q_act_kPa": q_act,
            "qa_kPa": allowable_bearing_kPa,
            "status": "OK" if q_act <= allowable_bearing_kPa else "EXCEEDED",
        }

    return results


def design_footings_from_model(
    model: Model,
    allowable_bearing_kPa: float = 200.0,
    min_size_m: float = 1.0,
    size_step_m: float = 0.05,
) -> dict[str, dict[str, Any]]:
    """Dimensiona zapatas a partir de las reacciones presentes en un Model canónico."""
    return size_isolated_footing_from_reactions(
        reactions=model.reactions,
        allowable_bearing_kPa=allowable_bearing_kPa,
        min_size_m=min_size_m,
        size_step_m=size_step_m,
    )


__all__ = [
    "reaction_to_point_load",
    "size_isolated_footing_from_reactions",
    "design_footings_from_model",
]
