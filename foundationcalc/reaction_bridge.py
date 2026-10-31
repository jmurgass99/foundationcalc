"""foundationcalc.reaction_bridge
====================================
Puente puro de datos entre las reacciones de apoyo (jmstructural-common / fastsap)
y las funciones de dimensionamiento y chequeo geotécnico de FoundationCalc.

Convierte instancias canónicas de Reaction en PointLoad y calcula el dimensionado
en planta de zapatas aisladas cuadradas bajo criterio de presión admisible de servicio.
Cero llamadas COM.
"""
from __future__ import annotations
import math
from typing import Any, Sequence

from foundationcalc.core.loading import ActionCategory, LoadType, PointLoad
from foundationcalc._common.model import Model, Reaction


def reaction_to_point_load(
    reaction: Reaction,
    load_type: LoadType = LoadType.PERMANENT,
    category: ActionCategory = ActionCategory.DEFAULT,
) -> PointLoad:
    """Convierte una Reaction de nudo en un PointLoad de FoundationCalc.

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
    max_size_m: float = 15.0,
    friction_coef: float = 0.35,
    sliding_fs: float = 1.50,
) -> dict[str, dict[str, Any]]:
    """Dimensiona en planta zapatas aisladas cuadradas bajo criterios de servicio.

    Verifica simultáneamente tres estados límite de servicio y equilibrio:
    1. Presión efectiva de contacto según Meyerhof (1953):
       B' = B - 2*e_x, L' = B - 2*e_y
       q_eff = N / (B' * L') <= allowable_bearing_kPa
       Fuente: Meyerhof, G.G. (1953), "The Bearing Capacity of Footings under
       Eccentric and Inclined Loads", Géotechnique 4(1):11-26; EN 1997-1 §6.5.2.2.
    2. Núcleo central / Estabilidad al vuelco:
       e_x = |My| / N <= B / 6, e_y = |Mx| / N <= B / 6 (sin despegue en servicio)
       Fuente: CTE DB-SE-C §4.2.1 / EN 1997-1 §6.5.4.
    3. Resistencia al deslizamiento horizontal por rozamiento en la base:
       F_h = sqrt(Fx^2 + Fy^2) <= (friction_coef * N) / sliding_fs
       Fuente: EN 1997-1 §6.5.3 / CTE DB-SE-C §4.3.4.

    Args:
        reactions: Secuencia de reacciones canónicas.
        allowable_bearing_kPa: Presión admisible de servicio del terreno en kPa [kN/m^2].
        min_size_m: Dimensión mínima de lado de zapata en metros.
        size_step_m: Paso constructivo de redondeo hacia arriba en metros.
        max_size_m: Cota superior de lado para iteración de zapata cuadrada en metros.
        friction_coef: Coeficiente de rozamiento base hormigón-terreno (default 0.35).
        sliding_fs: Factor de seguridad al deslizamiento en servicio (default 1.50).

    Returns:
        Diccionario {node_id: {
            "node_id": str,
            "N_max_kN": float,
            "B_m": float,
            "L_m": float,
            "area_m2": float,
            "q_act_kPa": float,
            "qa_kPa": float,
            "e_x_m": float,
            "e_y_m": float,
            "kern_limit_m": float,
            "sliding_dcr": float,
            "has_uplift": bool,
            "uplift_max_kN": float,
            "status": "OK" | "BEARING_GOVERNS" | "OVERTURNING_GOVERNS" | "SLIDING_GOVERNS" | ...
        }}
    """
    if allowable_bearing_kPa <= 0.0:
        raise ValueError(f"allowable_bearing_kPa debe ser > 0, obtenido {allowable_bearing_kPa}")
    if min_size_m <= 0.0:
        raise ValueError(f"min_size_m debe ser > 0, obtenido {min_size_m}")
    if friction_coef <= 0.0:
        raise ValueError(f"friction_coef debe ser > 0, obtenido {friction_coef}")
    if sliding_fs <= 0.0:
        raise ValueError(f"sliding_fs debe ser > 0, obtenido {sliding_fs}")

    # Agrupar por nudo
    by_node: dict[str, list[Reaction]] = {}
    for rx in reactions:
        by_node.setdefault(rx.node_id, []).append(rx)

    results: dict[str, dict[str, Any]] = {}

    for node_id, rx_list in by_node.items():
        comp_rxs = [r for r in rx_list if float(r.fz_kN) > 0.0]
        uplift_forces = [abs(float(r.fz_kN)) for r in rx_list if float(r.fz_kN) < 0.0]

        has_uplift = len(uplift_forces) > 0
        uplift_max = max(uplift_forces) if has_uplift else 0.0

        if not comp_rxs:
            side = min_size_m
            results[node_id] = {
                "node_id": node_id,
                "N_max_kN": 0.0,
                "B_m": side,
                "L_m": side,
                "area_m2": side * side,
                "q_act_kPa": 0.0,
                "qa_kPa": allowable_bearing_kPa,
                "e_x_m": 0.0,
                "e_y_m": 0.0,
                "kern_limit_m": side / 6.0,
                "sliding_dcr": 0.0,
                "has_uplift": has_uplift,
                "uplift_max_kN": uplift_max,
                "status": "UPLIFT_GOVERNS" if has_uplift else "NO_LOAD",
            }
            continue

        n_max = max(float(r.fz_kN) for r in comp_rxs)

        # 1. Analizar excentricidades y demandas de cortante por combinación
        case_data = []
        max_ex = 0.0
        max_ey = 0.0
        max_sliding_dcr = 0.0

        for r in comp_rxs:
            N = float(r.fz_kN)
            Mx = float(r.mx_kNm)
            My = float(r.my_kNm)
            Fx = float(r.fx_kN)
            Fy = float(r.fy_kN)

            ex = abs(My) / N if N > 0 else 0.0
            ey = abs(Mx) / N if N > 0 else 0.0
            Fh = math.hypot(Fx, Fy)

            R_slide_allow = (friction_coef * N) / sliding_fs if N > 0 else 0.0
            dcr_slide = Fh / max(R_slide_allow, 1e-9)

            if ex > max_ex:
                max_ex = ex
            if ey > max_ey:
                max_ey = ey
            if dcr_slide > max_sliding_dcr:
                max_sliding_dcr = dcr_slide

            case_data.append({"N": N, "ex": ex, "ey": ey, "Fh": Fh, "dcr_slide": dcr_slide})

        # 1b. Deslizamiento en las combinaciones SIN axil de compresion (B48, §8.18).
        #
        # El bucle de arriba solo recorre `comp_rxs` (Fz > 0), que es lo correcto
        # para presion, nucleo y Meyerhof. Pero el DESLIZAMIENTO no puede excluir
        # las demas: una base sin axil --o traccionada-- no genera rozamiento, y
        # si recibe cortante esa es precisamente la combinacion que desliza.
        # Medido: {Fz 500, Fx 10} + {Fz 0.0, Fx 300} firmaba CALCULADO_CUMPLE, y
        # el MISMO nudo con Fz = +1 (estrictamente menos desfavorable) daba
        # FALLA: la envolvente no era monotona.
        #
        # Formula del propio docstring (F_h <= mu*N/FS) con N_fric = max(Fz, 0),
        # y el MISMO suelo de 1e-9 que usa la linea de arriba: resistencia nula
        # con cortante da un dcr no acotado (> 1), y un cortante MEDIDO nulo
        # sigue dando 0 -- el caso sano no cae.
        for r in rx_list:
            if float(r.fz_kN) > 0.0:
                continue                      # ya contada arriba
            Fh = math.hypot(float(r.fx_kN), float(r.fy_kN))
            if Fh > 0.0:
                dcr_slide = Fh / 1e-9
                if dcr_slide > max_sliding_dcr:
                    max_sliding_dcr = dcr_slide

        # 2. Lado mínimo por carga axial pura (referencia)
        a_req_axial = n_max / allowable_bearing_kPa
        side_axial = max(_round_up_step(math.sqrt(a_req_axial), size_step_m), min_size_m)

        # 3. Lado mínimo requerido para mantener resultante dentro del núcleo central (e <= B/6)
        side_kern = 6.0 * max(max_ex, max_ey)
        side_cand = max(side_axial, _round_up_step(side_kern, size_step_m))

        # 4. Iteración para cumplir Meyerhof y núcleo en todas las combinaciones
        solved_side = None
        max_q_act = 0.0

        while side_cand <= max_size_m + 1e-9:
            all_ok = True
            current_max_q = 0.0
            kern_lim = side_cand / 6.0

            for cd in case_data:
                ex = cd["ex"]
                ey = cd["ey"]
                # Núcleo central
                if ex > kern_lim + 1e-9 or ey > kern_lim + 1e-9:
                    all_ok = False
                    break
                # Dimensiones efectivas de Meyerhof (1953)
                B_prime = side_cand - 2.0 * ex
                L_prime = side_cand - 2.0 * ey
                if B_prime <= 1e-6 or L_prime <= 1e-6:
                    all_ok = False
                    break
                q_eff = cd["N"] / (B_prime * L_prime)
                if q_eff > current_max_q:
                    current_max_q = q_eff
                if q_eff > allowable_bearing_kPa + 1e-9:
                    all_ok = False
                    break

            if all_ok:
                solved_side = side_cand
                max_q_act = current_max_q
                break

            side_cand = _round_up_step(side_cand + size_step_m, size_step_m)

        if solved_side is None:
            # No converge dentro de max_size_m: zapata cuadrada no es viable
            final_side = max_size_m
            final_q_act = max_q_act
            status = "OVERTURNING_GOVERNS" if max(max_ex, max_ey) * 6.0 > max_size_m else "EXCEEDED"
        else:
            final_side = solved_side
            final_q_act = max_q_act

            # Determinación de qué criterio gobierna el dimensionado
            if max_sliding_dcr > 1.0:
                status = "SLIDING_GOVERNS"
            elif final_side > side_axial:
                # El momento obligó a ensanchar
                if side_kern > side_axial - 1e-9 and final_side <= _round_up_step(side_kern, size_step_m) + 1e-9:
                    status = "OVERTURNING_GOVERNS"
                else:
                    status = "BEARING_GOVERNS"
            else:
                status = "OK_WITH_UPLIFT_WARNING" if has_uplift else "OK"

        area = final_side * final_side
        results[node_id] = {
            "node_id": node_id,
            "N_max_kN": n_max,
            "B_m": round(final_side, 4),
            "L_m": round(final_side, 4),
            "area_m2": round(area, 4),
            "q_act_kPa": round(final_q_act, 4),
            "qa_kPa": allowable_bearing_kPa,
            "e_x_m": round(max_ex, 4),
            "e_y_m": round(max_ey, 4),
            "kern_limit_m": round(final_side / 6.0, 4),
            "sliding_dcr": round(max_sliding_dcr, 4),
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
    max_size_m: float = 15.0,
    friction_coef: float = 0.35,
    sliding_fs: float = 1.50,
) -> dict[str, dict[str, Any]]:
    """Dimensiona zapatas a partir de las reacciones presentes en un Model canónico."""
    return size_isolated_footing_from_reactions(
        reactions=model.reactions,
        allowable_bearing_kPa=allowable_bearing_kPa,
        min_size_m=min_size_m,
        size_step_m=size_step_m,
        max_size_m=max_size_m,
        friction_coef=friction_coef,
        sliding_fs=sliding_fs,
    )


__all__ = [
    "reaction_to_point_load",
    "size_isolated_footing_from_reactions",
    "design_footings_from_model",
]
