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
    """Convierte una Reaction de nudo en un PointLoad de FoundationDesignJm.

    Convención de signos:
    - Reaction.fz_kN > 0 (reacción ascendente en SAP/ETABS) -> PointLoad.fz > 0 (compresión hacia abajo sobre la zapata).
    - Reaction.fz_kN < 0 (reacción descendente / tracción en SAP/ETABS) -> PointLoad.fz < 0 (levantamiento / tracción hacia arriba).
    - Momentos (mx, my) y cortantes (vx, vy) preservan sus signos reales.
    """
    return PointLoad(
        name=f"Reaction_{reaction.node_id}_{reaction.case}",
        fz=float(reaction.fz_kN),
        mx=float(reaction.mx_kNm),
        my=float(reaction.my_kNm),
        vx=float(reaction.fx_kN),
        vy=float(reaction.fy_kN),
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

    Detecta explícitamente estados de levantamiento (uplift, Fz < 0) y evita tratarlos
    falsamente como compresión sobre el terreno.

    Args:
        reactions: Secuencia de reacciones canónicas.
        allowable_bearing_kPa: Presión admisible de servicio del terreno en kPa.
        min_size_m: Dimensión mínima de lado de zapata en metros.
        size_step_m: Paso constructivo de redondeo hacia arriba.

    Returns:
        Diccionario {node_id: {"N_max_kN": ..., "B_m": ..., "L_m": ..., "q_act_kPa": ..., "qa_kPa": ..., "has_uplift": bool, "uplift_max_kN": float, "status": ...}}
    """
    if allowable_bearing_kPa <= 0.0:
        raise ValueError(f"allowable_bearing_kPa debe ser > 0, obtenido {allowable_bearing_kPa}")

    # Agrupar por nudo
    by_node: dict[str, list[Reaction]] = {}
    for rx in reactions:
        by_node.setdefault(rx.node_id, []).append(rx)

    results: dict[str, dict[str, Any]] = {}

    for node_id, rx_list in by_node.items():
        # Separar compresiones (Fz > 0) y tracciones/uplift (Fz < 0)
        comp_forces = [float(r.fz_kN) for r in rx_list if float(r.fz_kN) > 0.0]
        uplift_forces = [abs(float(r.fz_kN)) for r in rx_list if float(r.fz_kN) < 0.0]

        has_uplift = len(uplift_forces) > 0
        uplift_max = max(uplift_forces) if has_uplift else 0.0
        n_max = max(comp_forces) if comp_forces else 0.0

        if n_max <= 0.0:
            # Caso de tracción pura / levantamiento gobernante
            side = min_size_m
            q_act = 0.0
            status = "UPLIFT_GOVERNS" if has_uplift else "NO_LOAD"
        else:
            a_req = n_max / allowable_bearing_kPa
            side_raw = math.sqrt(a_req)
            side = max(_round_up_step(side_raw, size_step_m), min_size_m)
            area = side * side
            q_act = n_max / area
            if q_act > allowable_bearing_kPa:
                status = "EXCEEDED"
            elif has_uplift:
                status = "OK_WITH_UPLIFT_WARNING"
            else:
                status = "OK"

        results[node_id] = {
            "node_id": node_id,
            "N_max_kN": n_max,
            "B_m": side,
            "L_m": side,
            "area_m2": side * side,
            "q_act_kPa": q_act,
            "qa_kPa": allowable_bearing_kPa,
            "has_uplift": has_uplift,
            "uplift_max_kN": uplift_max,
            "status": status,
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
