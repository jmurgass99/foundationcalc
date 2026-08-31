"""foundationdesignjm.integration.foundation_chain
=================================================
Cadena de cálculo completa de cimentaciones: ETABS → FoundationDesignJm → SAFE.

Flujo integral:
1. Reacciones de base por combinación (desde ETABS / jmstructural-common).
2. Dimensionado geotécnico en planta (tensión admisible de servicio + detección de uplift).
3. Muelles elásticos de Winkler por zapata / losa (integración con FastSAPWinklerExporter).
4. Verificación de punzonamiento según Eurocode 2 (§6.4).
5. Generación de especificación declarativa pura para SAFE 2022 (y ejecución live opcional).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Sequence, Optional

from foundationdesignjm.core.geometry import Column, RectangularFoundation
from foundationdesignjm.design.punching_shear import PunchingShearResult, punching_shear_check
from foundationdesignjm.integration.fastsap_winkler import WinklerSpring
from foundationdesignjm.reaction_bridge import (
    reaction_to_point_load,
    size_isolated_footing_from_reactions,
)
from jmstructural_common.model import Reaction


@dataclass
class FoundationChainResult:
    """Resultado completo de la cadena de diseño y preparación SAFE."""

    design_summary: dict[str, dict[str, Any]]
    punching_checks: dict[str, PunchingShearResult]
    winkler_springs: list[WinklerSpring]
    safe_model_spec: dict[str, Any]
    total_concrete_m3: float = 0.0
    has_global_uplift: bool = False
    safe_injection_status: Optional[dict[str, Any]] = None


def foundation_chain_from_etabs(
    etabs_or_reactions: Any,
    soil_params: dict[str, Any],
    *,
    footing_thickness_m: float = 0.50,
    concrete_fck_MPa: float = 30.0,
    column_dimensions: dict[str, tuple[float, float]] | tuple[float, float] = (0.40, 0.40),
    column_coordinates: Optional[dict[str, tuple[float, float]]] = None,
    combos: Optional[list[str]] = None,
    safe_client: Any = None,
) -> FoundationChainResult:
    """Ejecuta la cadena completa desde reacciones ETABS hasta especificación SAFE.

    Args:
        etabs_or_reactions: Instancia de EtabsClient, lista de Reaction, o lista de dicts.
        soil_params: Parámetros del terreno:
            - allowable_bearing_kPa (float, default 200.0)
            - subgrade_modulus_ks_kN_m3 (float, default 40000.0)
        footing_thickness_m: Canto / espesor de las zapatas en metros.
        concrete_fck_MPa: Resistencia característica del hormigón a compresión en MPa.
        column_dimensions: Dimensiones (cx, cy) de columna en metros (por nudo o global).
        column_coordinates: Coordenadas (x, y) de cada nudo de columna (default (0,0)).
        combos: Filtro opcional de combinaciones a procesar.
        safe_client: Instancia opcional de SafeClient para inyección física live.

    Returns:
        FoundationChainResult con diseño, punzonamiento, muelles Winkler y spec SAFE.
    """
    # 1. Resolver reacciones canónicas
    if hasattr(etabs_or_reactions, "get_joint_reactions"):
        reactions: list[Reaction] = etabs_or_reactions.get_joint_reactions(combos=combos, story="Base")
    elif isinstance(etabs_or_reactions, Sequence):
        if len(etabs_or_reactions) > 0 and isinstance(etabs_or_reactions[0], dict):
            reactions = [
                Reaction(
                    node_id=str(r.get("joint", r.get("Point", r.get("node_id", "")))),
                    case=str(r.get("case", r.get("OutputCase", ""))),
                    fx_kN=float(r.get("Fx", r.get("FX", 0.0))),
                    fy_kN=float(r.get("Fy", r.get("FY", 0.0))),
                    fz_kN=float(r.get("Fz", r.get("FZ", 0.0))),
                    mx_kNm=float(r.get("Mx", r.get("MX", 0.0))),
                    my_kNm=float(r.get("My", r.get("MY", 0.0))),
                    mz_kNm=float(r.get("Mz", r.get("MZ", 0.0))),
                )
                for r in etabs_or_reactions
            ]
        else:
            reactions = list(etabs_or_reactions)
    else:
        raise TypeError(f"Tipo no soportado para etabs_or_reactions: {type(etabs_or_reactions)}")

    if combos:
        reactions = [r for r in reactions if r.case in combos]

    qa_kPa = float(soil_params.get("allowable_bearing_kPa", 200.0))
    ks_kN_m3 = float(soil_params.get("subgrade_modulus_ks_kN_m3", 40000.0))

    # 2. Dimensionado geotécnico en planta
    design_summary = size_isolated_footing_from_reactions(
        reactions=reactions,
        allowable_bearing_kPa=qa_kPa,
        min_size_m=float(soil_params.get("min_size_m", 1.0)),
        size_step_m=float(soil_params.get("size_step_m", 0.05)),
    )

    # 3. Muelles Winkler y Chequeo de Punzonamiento por nudo
    punching_checks: dict[str, PunchingShearResult] = {}
    winkler_springs: list[WinklerSpring] = []
    total_vol = 0.0
    has_global_uplift = False

    by_node: dict[str, list[Reaction]] = {}
    for rx in reactions:
        by_node.setdefault(rx.node_id, []).append(rx)

    # Coordenadas por defecto si no se pasaron
    col_coords = column_coordinates or {}

    for node_id, summary in design_summary.items():
        B = float(summary["B_m"])
        L = float(summary["L_m"])
        h = footing_thickness_m
        vol = B * L * h
        summary["thickness_m"] = h
        summary["concrete_volume_m3"] = vol
        total_vol += vol

        if summary.get("has_uplift"):
            has_global_uplift = True

        # Muelle Winkler vertical: Kz = ks * Area
        area_m2 = B * L
        kz = ks_kN_m3 * area_m2
        kx = 0.5 * kz
        ky = 0.5 * kz
        winkler_springs.append(WinklerSpring(joint_name=node_id, kx_kN_m=kx, ky_kN_m=ky, kz_kN_m=kz))

        # Dimensión de columna
        if isinstance(column_dimensions, dict):
            cx, cy = column_dimensions.get(node_id, (0.40, 0.40))
        else:
            cx, cy = column_dimensions

        # Punzonamiento bajo la mayor compresión de diseño (ELU)
        n_max = float(summary["N_max_kN"])
        if n_max > 0:
            footing_geom = RectangularFoundation(
                length=L * 1000.0,
                width=B * 1000.0,
                thickness=h * 1000.0,
            )
            col_geom = Column(
                length=cx * 1000.0,
                width=cy * 1000.0,
                pos_x=(L * 1000.0) / 2.0,
                pos_y=(B * 1000.0) / 2.0,
            )

            d_eff = max(h - 0.05, 0.15)  # 50 mm de recubrimiento
            p_res = punching_shear_check(
                foundation=footing_geom,
                column=col_geom,
                N_sd_kN=n_max,
                fck_MPa=concrete_fck_MPa,
                rho_x=0.005,
                rho_y=0.005,
                d_eff_m=d_eff,
            )
            punching_checks[node_id] = p_res

    # 4. Construcción de la especificación declarativa para SAFE 2022
    footing_specs = []
    for node_id, summary in design_summary.items():
        B = float(summary["B_m"])
        L = float(summary["L_m"])
        cx_mid, cy_mid = col_coords.get(node_id, (0.0, 0.0))
        # 4 esquinas centradas en la posición de la columna
        dx = B / 2.0
        dy = L / 2.0
        poly = [
            (cx_mid - dx, cy_mid - dy),
            (cx_mid + dx, cy_mid - dy),
            (cx_mid + dx, cy_mid + dy),
            (cx_mid - dx, cy_mid + dy),
        ]
        footing_specs.append({
            "name": f"FOOTING_{node_id}",
            "node_id": node_id,
            "coordinates": poly,
            "thickness": footing_thickness_m,
            "material": "CONC",
            "subgrade_modulus_ks": ks_kN_m3,
        })

    # Cargas por combinación con signos exactos
    column_loads = []
    for rx in reactions:
        column_loads.append({
            "point_name": rx.node_id,
            "case": rx.case,
            "P": rx.fz_kN,      # Fz positivo = compresión en PointLoad -> Fz=-P en SAFE
            "Vx": rx.fx_kN,
            "Vy": rx.fy_kN,
            "Mx": rx.mx_kNm,
            "My": rx.my_kNm,
            "Mz": rx.mz_kNm,
        })

    safe_model_spec = {
        "footings": footing_specs,
        "soil_subgrade_modulus_ks": ks_kN_m3,
        "column_loads": column_loads,
        "n_footings": len(footing_specs),
        "n_loads": len(column_loads),
    }

    # 5. Inyección live opcional si se proporcionó un SafeClient
    injection_status = None
    if safe_client is not None:
        injected_footings = 0
        injected_loads = 0
        for f_spec in footing_specs:
            try:
                safe_client.add_mat_slab(
                    name=f_spec["name"],
                    coordinates=f_spec["coordinates"],
                    thickness=f_spec["thickness"],
                    material=f_spec["material"],
                )
                safe_client.add_winkler_springs(
                    area_name=f_spec["name"],
                    subgrade_modulus_ks=f_spec["subgrade_modulus_ks"],
                )
                injected_footings += 1
            except Exception:
                pass

        for c_load in column_loads:
            try:
                safe_client.add_column_load(
                    point_name=c_load["point_name"],
                    pattern=c_load["case"],
                    P=c_load["P"],
                    Mx=c_load["Mx"],
                    My=c_load["My"],
                    Vx=c_load["Vx"],
                    Vy=c_load["Vy"],
                    Mz=c_load["Mz"],
                )
                injected_loads += 1
            except Exception:
                pass

        injection_status = {
            "injected_footings": injected_footings,
            "injected_loads": injected_loads,
            "success": injected_footings > 0 or injected_loads > 0,
        }

    return FoundationChainResult(
        design_summary=design_summary,
        punching_checks=punching_checks,
        winkler_springs=winkler_springs,
        safe_model_spec=safe_model_spec,
        total_concrete_m3=total_vol,
        has_global_uplift=has_global_uplift,
        safe_injection_status=injection_status,
    )


__all__ = [
    "FoundationChainResult",
    "foundation_chain_from_etabs",
]
