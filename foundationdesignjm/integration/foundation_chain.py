"""foundationdesignjm.integration.foundation_chain
=================================================
Cadena de cálculo completa de cimentaciones: ETABS → FoundationDesignJm → SAFE y Entregables.

Flujo integral de producción:
1. Reacciones de base por combinación (desde ETABS / jmstructural-common).
2. Dimensionado geotécnico en planta (tensión admisible de servicio + detección de uplift).
3. Detección y diseño de zapatas combinadas por solape espacial.
4. Armado por flexión en ambas direcciones (EC2 §9.2 / §9.8, selección de barras comerciales y anclaje EC2 §8.4.4).
5. Verificación de punzonamiento según Eurocode 2 (§6.4).
6. Muelles elásticos de Winkler por zapata (Kz = ks·B·L, Kx=Ky=0.5Kz).
7. Generación de planos de detalle DXF con capas normalizadas.
8. Memoria técnica de cálculo y cuadro de cubicaciones (hormigón, acero, encofrado).
9. Especificación declarativa para SAFE 2022 (e inyección live opcional).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Sequence, Optional

from foundationdesignjm.core.geometry import Column, RectangularFoundation
from foundationdesignjm.core.material import Concrete, ReinforcingSteel
from foundationdesignjm.analysis.boussinesq import BoussinesqRect, sigma_z_rect_center
from foundationdesignjm.consolidacion_1d import ConsolidationInput, evaluate_consolidation
from foundationdesignjm.design.combined_footing import (
    CombinedFootingInputs,
    CombinedFootingResult,
    design_combined_footing,
)
from foundationdesignjm.design.pile_cap import (
    cap_two_piles,
    cap_three_piles,
    cap_four_piles,
)
from foundationdesignjm.pile_capacity_multi import (
    PileCapacityInput,
    design_pile_capacity,
)
from foundationdesignjm.design.punching_shear import PunchingShearResult, punching_shear_check
from foundationdesignjm.design.reinforcement import (
    FootingFlexureDetail,
    design_footing_flexure_both_ways,
)
from foundationdesignjm.integration.dxf_armado import ArmadoZapataDXF, export_armado_zapata
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
    pile_cap_designs: dict[str, Any] = field(default_factory=dict)
    settlement_results: dict[str, Any] = field(default_factory=dict)


@dataclass
class FoundationPackageResult:
    """Paquete completo de entregables de ingeniería de cimentaciones."""

    design_summary: dict[str, dict[str, Any]]
    flexure_reinforcement: dict[str, dict[str, FootingFlexureDetail]]
    punching_checks: dict[str, PunchingShearResult]
    combined_footings: list[CombinedFootingResult]
    winkler_springs: list[WinklerSpring]
    safe_model_spec: dict[str, Any]
    quantities: dict[str, Any]
    memoria_markdown: str
    dxf_paths: list[str] = field(default_factory=list)
    has_global_uplift: bool = False
    total_concrete_m3: float = 0.0
    total_steel_kg: float = 0.0
    total_formwork_m2: float = 0.0
    pile_cap_designs: dict[str, Any] = field(default_factory=dict)
    settlement_results: dict[str, Any] = field(default_factory=dict)


def foundation_chain_from_etabs(
    etabs_or_reactions: Any,
    soil_params: dict[str, Any],
    *,
    footing_thickness_m: float = 0.50,
    concrete_fck_MPa: float = 30.0,
    steel_fyk_MPa: float = 500.0,
    column_dimensions: dict[str, tuple[float, float]] | tuple[float, float] = (0.40, 0.40),
    column_coordinates: Optional[dict[str, tuple[float, float]]] = None,
    combos: Optional[list[str]] = None,
    safe_client: Any = None,
    max_footing_side_m: float = 5.0,
    min_bearing_capacity_kPa: float = 50.0,
    pile_design_capacity_kN: float = 600.0,
    auto_switch_to_piles: bool = True,
) -> FoundationChainResult:
    """Ejecuta la cadena de dimensionado y preparación para SAFE 2022."""
    reactions = _resolve_reactions(etabs_or_reactions, combos)

    qa_kPa = float(soil_params.get("allowable_bearing_kPa", 200.0))
    ks_kN_m3 = float(soil_params.get("subgrade_modulus_ks_kN_m3", 40000.0))

    # 1. Dimensionado geotécnico en planta
    design_summary = size_isolated_footing_from_reactions(
        reactions=reactions,
        allowable_bearing_kPa=qa_kPa,
        min_size_m=float(soil_params.get("min_size_m", 1.0)),
        size_step_m=float(soil_params.get("size_step_m", 0.05)),
    )

    # 2. Muelles Winkler, Chequeo de Punzonamiento y Cambio Automático a Pilotes
    punching_checks: dict[str, PunchingShearResult] = {}
    winkler_springs: list[WinklerSpring] = []
    pile_cap_designs: dict[str, Any] = {}
    settlement_results: dict[str, Any] = {}
    total_vol = 0.0
    has_global_uplift = False

    col_coords = column_coordinates or {}
    steel_mat = ReinforcingSteel(fyk=steel_fyk_MPa)

    # Evaluación de asentamientos si hay estrato compresible
    if "compressible_layer" in soil_params or "Cc" in soil_params:
        comp_info = soil_params.get("compressible_layer", soil_params)
        h_layer = float(comp_info.get("H_layer_m", 3.0))
        sigma_v0 = float(comp_info.get("sigma_v_0_kPa", 80.0))
        cc = float(comp_info.get("Cc", 0.25))
        e0 = float(comp_info.get("e_0", 0.80))
        cv = float(comp_info.get("cv_m2_per_year", 1.2))

        for node_id, summary in design_summary.items():
            n_max = float(summary["N_max_kN"])
            if n_max > 0:
                # Incremento de tension bajo el CENTRO de la zapata rectangular,
                # por superposicion de los 4 cuadrantes (Newmark/Fadum).
                #
                # DEFECTO CORREGIDO, dos errores compuestos que subestimaban el
                # asentamiento un ~40 %:
                #   1. Se usaba la solucion de CARGA PUNTUAL 3N/(2*pi*z^2), que
                #      solo vale para z >~ 2-3B. Aqui z/B ~ 0.67: fuera de rango.
                #      (El informe la llamaba ademas "bulbo 2:1 / Newmark"; son
                #      tres metodos distintos y daban 71.1 / 108.4 kPa frente a
                #      los 53.05 que salian.)
                #   2. z se media desde la SUPERFICIE del terreno (Df + H/2) en
                #      vez de desde el plano de aplicacion de la carga, que es la
                #      base de la zapata. El estrato compresible se situa
                #      inmediatamente bajo ella, luego z = H/2.
                #
                # `sigma_z_rect_center` ya existia en analysis/boussinesq.py y
                # estaba corregida (commit 684cf78); esto solo la cablea.
                B_m = float(summary["B_m"])
                L_m = float(summary["L_m"])
                qo_kPa = n_max / (B_m * L_m)
                z_mid = h_layer / 2.0
                delta_sigma = sigma_z_rect_center(
                    BoussinesqRect(qo_kPa=qo_kPa, B_m=B_m, L_m=L_m, z_m=z_mid)
                )
                c_inp = ConsolidationInput(
                    H_layer_m=h_layer,
                    sigma_v_0_kPa=sigma_v0,
                    delta_sigma_kPa=delta_sigma,
                    Cc=cc,
                    e_0=e0,
                    cv_m2_per_year=cv,
                )
                settlement_results[node_id] = evaluate_consolidation(c_inp)

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

        n_max = float(summary["N_max_kN"])

        # Auto-switch a pilotes si el lado excede max_footing_side_m o qa_kPa < min_bearing_capacity_kPa
        switch_needed = False
        switch_reason = ""
        if auto_switch_to_piles:
            if max(B, L) > max_footing_side_m:
                switch_needed = True
                switch_reason = f"Lado de zapata requerido ({max(B, L):.2f} m) excede el máximo permitido ({max_footing_side_m:.2f} m)"
            elif qa_kPa < min_bearing_capacity_kPa:
                switch_needed = True
                switch_reason = f"Tensión admisible de suelo ({qa_kPa:.1f} kPa) inferior al mínimo ({min_bearing_capacity_kPa:.1f} kPa)"

        if switch_needed and n_max > 0:
            summary["foundation_type"] = "pile_cap"
            summary["switch_reason"] = switch_reason
            summary["status"] = f"SWITCH_A_PILOTES: {switch_reason}"

            # Dimensionado de encepado (pile cap)
            n_piles = max(2, math.ceil(n_max / pile_design_capacity_kN))
            d_mm = max(h - 0.05, 0.40) * 1000.0  # mm
            a_mm = 400.0  # columna cuadrada 400mm
            if isinstance(column_dimensions, dict):
                a_mm = column_dimensions.get(node_id, (0.4, 0.4))[0] * 1000.0

            if n_piles == 2:
                v_mm = 600.0  # voladizo eje pilote a borde
                tie_res = cap_two_piles(n_max, v_mm=v_mm, a_mm=a_mm, d_mm=d_mm, steel=steel_mat)
                pile_cap_designs[node_id] = {
                    "n_piles": 2,
                    "pile_capacity_kN": pile_design_capacity_kN,
                    "tie_result": tie_res,
                    "switch_reason": switch_reason,
                }
            elif n_piles == 3:
                l_mm = 1500.0  # lado triangulo pilotes
                tie_res = cap_three_piles(n_max, l_mm=l_mm, a_mm=a_mm, d_mm=d_mm, steel=steel_mat)
                pile_cap_designs[node_id] = {
                    "n_piles": 3,
                    "pile_capacity_kN": pile_design_capacity_kN,
                    "tie_result": tie_res,
                    "switch_reason": switch_reason,
                }
            else:
                l1_mm = 1500.0
                l2_mm = 1500.0
                r1, r2 = cap_four_piles(n_max, l1_mm=l1_mm, l2_mm=l2_mm, a1_mm=a_mm, a2_mm=a_mm, d_mm=d_mm, steel=steel_mat)
                pile_cap_designs[node_id] = {
                    "n_piles": 4,
                    "pile_capacity_kN": pile_design_capacity_kN,
                    "tie_result_x": r1,
                    "tie_result_y": r2,
                    "switch_reason": switch_reason,
                }
        else:
            summary["foundation_type"] = "isolated_footing"
            summary["switch_reason"] = "Zapata aislada directa dentro de límites"

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

    # 3. Construcción de la especificación declarativa para SAFE 2022
    footing_specs = []
    for node_id, summary in design_summary.items():
        B = float(summary["B_m"])
        L = float(summary["L_m"])
        cx_mid, cy_mid = col_coords.get(node_id, (0.0, 0.0))
        dx = B / 2.0
        dy = L / 2.0
        poly = [
            (cx_mid - dx, cy_mid - dy),
            (cx_mid + dx, cy_mid - dy),
            (cx_mid + dx, cy_mid + dy),
            (cx_mid - dx, cy_mid + dy),
        ]
        footing_specs.append({
            "name": f"ZAPATA_{node_id}",
            "joint_name": node_id,
            "coordinates": poly,
            "thickness": footing_thickness_m,
            "material": f"HA_{int(concrete_fck_MPa)}",
            "subgrade_modulus_ks": ks_kN_m3,
        })

    column_loads = [
        {
            "point_name": rx.node_id,
            "case": rx.case,
            "P": rx.fz_kN,
            "Mx": rx.mx_kNm,
            "My": rx.my_kNm,
            "Vx": rx.fx_kN,
            "Vy": rx.fy_kN,
            "Mz": rx.mz_kNm,
        }
        for rx in reactions
    ]

    safe_model_spec = {
        "footings": footing_specs,
        "column_loads": column_loads,
        "n_footings": len(footing_specs),
        "n_loads": len(column_loads),
    }

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
        pile_cap_designs=pile_cap_designs,
        settlement_results=settlement_results,
    )


def foundation_package(
    etabs_or_reactions: Any,
    soil_params: dict[str, Any],
    *,
    footing_thickness_m: float = 0.50,
    concrete_fck_MPa: float = 30.0,
    steel_fyk_MPa: float = 500.0,
    column_dimensions: dict[str, tuple[float, float]] | tuple[float, float] = (0.40, 0.40),
    column_coordinates: Optional[dict[str, tuple[float, float]]] = None,
    combos: Optional[list[str]] = None,
    preferred_phi_mm: float = 16.0,
    cover_mm: float = 50.0,
    output_dir: Optional[str | Path] = None,
    project_name: str = "PROYECTO ESTRUCTURAL",
    engineer_name: str = "INGENIERO RESPONSABLE",
    max_footing_side_m: float = 5.0,
    min_bearing_capacity_kPa: float = 50.0,
    pile_design_capacity_kN: float = 600.0,
    substitute_overlapping_footings: bool = True,
) -> FoundationPackageResult:
    """Genera el paquete completo de entregables de producción para cimentaciones.

    Incluye:
    - Dimensionado geotécnico en planta con auto-switch a pilotes si aplica.
    - Detección y sustitución de zapatas combinadas ante solapes geométricos reales.
    - Asentamientos elásticos / consolidación 1D (Boussinesq + Terzaghi) si hay estrato compresible.
    - Armado a flexión en 2 direcciones (EC2 §9.2 / §9.8, anclaje EC2 §8.4.4).
    - Verificación a punzonamiento (EC2 §6.4).
    - Planos de detalle DXF por zapata.
    - Memoria de cálculo técnica en Markdown.
    - Cómputo métrico (hormigón m³, acero kg, encofrado m²).
    """
    reactions = _resolve_reactions(etabs_or_reactions, combos)
    col_coords = column_coordinates or {rx.node_id: (0.0, 0.0) for rx in reactions}

    # 1. Dimensionado y cadena base
    chain = foundation_chain_from_etabs(
        etabs_or_reactions=reactions,
        soil_params=soil_params,
        footing_thickness_m=footing_thickness_m,
        concrete_fck_MPa=concrete_fck_MPa,
        steel_fyk_MPa=steel_fyk_MPa,
        column_dimensions=column_dimensions,
        column_coordinates=col_coords,
        combos=combos,
        max_footing_side_m=max_footing_side_m,
        min_bearing_capacity_kPa=min_bearing_capacity_kPa,
        pile_design_capacity_kN=pile_design_capacity_kN,
    )

    concrete = Concrete(fck=concrete_fck_MPa)
    steel = ReinforcingSteel(fyk=steel_fyk_MPa)

    # 2. Detección de zapatas combinadas por solape
    qa_kPa = float(soil_params.get("allowable_bearing_kPa", 200.0))
    combined_footings, replaced_pairs = _detect_and_design_combined_footings(
        chain.design_summary,
        col_coords,
        column_dimensions,
        qa_kPa,
        footing_thickness_m,
        concrete,
        steel,
    )

    # Si se activa la sustitución, reemplazar los pares de zapatas aisladas por la combinada
    if substitute_overlapping_footings and replaced_pairs:
        for (n1, n2), cf in zip(replaced_pairs, combined_footings):
            comb_id = f"COMB_{n1}_{n2}"
            p1 = float(chain.design_summary.get(n1, {}).get("N_max_kN", 0.0))
            p2 = float(chain.design_summary.get(n2, {}).get("N_max_kN", 0.0))
            chain.design_summary.pop(n1, None)
            chain.design_summary.pop(n2, None)
            chain.design_summary[comb_id] = {
                "B_m": cf.B_m,
                "L_m": cf.L_m,
                "thickness_m": footing_thickness_m,
                "N_max_kN": p1 + p2,
                "q_act_kPa": (p1 + p2) / max(cf.L_m * cf.B_m, 1e-4),
                "qa_kPa": qa_kPa,
                "status": "OK (ZAPATA COMBINADA POR SOLAPE)",
                "has_uplift": False,
                "is_combined": True,
                "combined_nodes": [n1, n2],
                "foundation_type": "combined_footing",
            }

    # 3. Armado por flexión en 2 direcciones por zapata
    flexure_rebar: dict[str, dict[str, FootingFlexureDetail]] = {}
    total_steel_kg = 0.0
    total_formwork_m2 = 0.0
    total_concrete_m3 = 0.0
    dxf_paths: list[str] = []

    out_path_dir = Path(output_dir) if output_dir else None
    if out_path_dir:
        out_path_dir.mkdir(parents=True, exist_ok=True)

    for node_id, summary in chain.design_summary.items():
        # Saltarse punzonamiento/flexión si es encepado
        if summary.get("foundation_type") == "pile_cap":
            continue

        B = float(summary["B_m"])
        L = float(summary["L_m"])
        h = footing_thickness_m
        n_max = float(summary["N_max_kN"])

        if isinstance(column_dimensions, dict):
            cx, cy = column_dimensions.get(node_id, (0.40, 0.40))
        else:
            cx, cy = column_dimensions

        # Flexión en X e Y
        rebar_both = design_footing_flexure_both_ways(
            B_m=B,
            L_m=L,
            h_m=h,
            N_Ed_kN=n_max,
            cx_m=cx,
            cy_m=cy,
            concrete=concrete,
            steel=steel,
            cover_mm=cover_mm,
            preferred_phi_mm=preferred_phi_mm,
        )
        flexure_rebar[node_id] = rebar_both

        # Cubicaciones por elemento
        det_x = rebar_both["X"]
        det_y = rebar_both["Y"]

        # Masa acero (barras longitud útil + solape/gancho 0.30m)
        len_x = L + 0.60
        len_y = B + 0.60
        w_x = (math.pi * (det_x.bar_diameter_mm ** 2) / 4.0) * 7.85e-3  # kg/m
        w_y = (math.pi * (det_y.bar_diameter_mm ** 2) / 4.0) * 7.85e-3  # kg/m

        footing_steel_kg = (det_x.n_bars * len_x * w_x) + (det_y.n_bars * len_y * w_y)
        footing_vol_m3 = B * L * h
        footing_formwork_m2 = 2.0 * (B + L) * h

        total_steel_kg += footing_steel_kg
        total_formwork_m2 += footing_formwork_m2
        total_concrete_m3 += footing_vol_m3

        # Exportación DXF si se especificó output_dir
        if out_path_dir:
            dxf_file = out_path_dir / f"zapata_{node_id}.dxf"
            arm_dxf = ArmadoZapataDXF(
                B_m=B,
                L_m=L,
                H_m=h,
                n_x=det_x.n_bars,
                n_y=det_y.n_bars,
                db_x_mm=det_x.bar_diameter_mm,
                db_y_mm=det_y.bar_diameter_mm,
                s_x_mm=det_x.spacing_mm,
                s_y_mm=det_y.spacing_mm,
                column_cx_m=cx,
                column_cy_m=cy,
                cover_mm=cover_mm,
                footing_name=f"ZAPATA {node_id}",
            )
            if export_armado_zapata(arm_dxf, dxf_file):
                dxf_paths.append(str(dxf_file))

    # 4. Generación de Memoria de Cálculo
    quantities_dict = {
        "total_concrete_m3": round(total_concrete_m3, 3),
        "total_steel_kg": round(total_steel_kg, 2),
        "total_formwork_m2": round(total_formwork_m2, 2),
        "steel_ratio_kg_m3": round(total_steel_kg / max(total_concrete_m3, 1e-4), 2),
        "footings_count": len(chain.design_summary),
        "combined_footings_count": len(combined_footings),
    }

    memoria_md = _generate_memoria_markdown(
        project_name=project_name,
        engineer_name=engineer_name,
        soil_params=soil_params,
        concrete=concrete,
        steel=steel,
        reactions=reactions,
        design_summary=chain.design_summary,
        flexure_rebar=flexure_rebar,
        punching_checks=chain.punching_checks,
        combined_footings=combined_footings,
        quantities=quantities_dict,
        pile_cap_designs=chain.pile_cap_designs,
        settlement_results=chain.settlement_results,
    )

    if out_path_dir:
        memoria_file = out_path_dir / "memoria_cimentaciones.md"
        memoria_file.write_text(memoria_md, encoding="utf-8")

    return FoundationPackageResult(
        design_summary=chain.design_summary,
        flexure_reinforcement=flexure_rebar,
        punching_checks=chain.punching_checks,
        combined_footings=combined_footings,
        winkler_springs=chain.winkler_springs,
        safe_model_spec=chain.safe_model_spec,
        quantities=quantities_dict,
        memoria_markdown=memoria_md,
        dxf_paths=dxf_paths,
        has_global_uplift=chain.has_global_uplift,
        total_concrete_m3=total_concrete_m3,
        total_steel_kg=total_steel_kg,
        total_formwork_m2=total_formwork_m2,
        pile_cap_designs=chain.pile_cap_designs,
        settlement_results=chain.settlement_results,
    )


def _resolve_reactions(etabs_or_reactions: Any, combos: Optional[list[str]] = None) -> list[Reaction]:
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
        elif len(etabs_or_reactions) > 0 and isinstance(etabs_or_reactions[0], Reaction):
            reactions = list(etabs_or_reactions)
        else:
            reactions = []
    else:
        reactions = []

    if combos is not None:
        combos_set = set(combos)
        reactions = [r for r in reactions if r.case in combos_set]

    return reactions


def _detect_and_design_combined_footings(
    design_summary: dict[str, dict[str, Any]],
    col_coords: dict[str, tuple[float, float]],
    column_dimensions: Any,
    qa_kPa: float,
    footing_thickness_m: float,
    concrete: Concrete,
    steel: ReinforcingSteel,
    clearance_min_m: float = 0.10,
) -> tuple[list[CombinedFootingResult], list[tuple[str, str]]]:
    """Detecta solapes entre pares de zapatas aisladas y diseña zapatas combinadas."""
    combined_results: list[CombinedFootingResult] = []
    replaced_pairs: list[tuple[str, str]] = []
    nodes = list(design_summary.keys())

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            n1, n2 = nodes[i], nodes[j]
            if n1 not in col_coords or n2 not in col_coords:
                continue
            x1, y1 = col_coords[n1]
            x2, y2 = col_coords[n2]

            B1, L1 = float(design_summary[n1]["B_m"]), float(design_summary[n1]["L_m"])
            B2, L2 = float(design_summary[n2]["B_m"]), float(design_summary[n2]["L_m"])

            dx = abs(x1 - x2)
            dy = abs(y1 - y2)

            # Comprobar solape de bounding boxes
            overlap_x = dx < ((B1 + B2) / 2.0 + clearance_min_m)
            overlap_y = dy < ((L1 + L2) / 2.0 + clearance_min_m)

            if overlap_x and overlap_y:
                spacing = math.hypot(dx, dy)
                if spacing >= 0.5:
                    p1 = float(design_summary[n1]["N_max_kN"])
                    p2 = float(design_summary[n2]["N_max_kN"])
                    col_sz = 0.40
                    if isinstance(column_dimensions, dict):
                        col_sz = max(column_dimensions.get(n1, (0.4, 0.4))[0], column_dimensions.get(n2, (0.4, 0.4))[0])

                    inp = CombinedFootingInputs(
                        P1_kN=max(p1, 50.0),
                        P2_kN=max(p2, 50.0),
                        col_spacing_m=spacing,
                        column_1_to_property_line_m=0.0,
                        column_size_m=col_sz,
                        q_allow_kPa=qa_kPa,
                        thickness_m=footing_thickness_m,
                    )
                    res = design_combined_footing(inp, concrete, steel)
                    combined_results.append(res)
                    replaced_pairs.append((n1, n2))
    return combined_results, replaced_pairs


def _generate_memoria_markdown(
    project_name: str,
    engineer_name: str,
    soil_params: dict[str, Any],
    concrete: Concrete,
    steel: ReinforcingSteel,
    reactions: list[Reaction],
    design_summary: dict[str, dict[str, Any]],
    flexure_rebar: dict[str, dict[str, FootingFlexureDetail]],
    punching_checks: dict[str, PunchingShearResult],
    combined_footings: list[CombinedFootingResult],
    quantities: dict[str, Any],
    pile_cap_designs: Optional[dict[str, Any]] = None,
    settlement_results: Optional[dict[str, Any]] = None,
) -> str:
    """Genera memoria de cálculo técnica en formato Markdown estructurado."""
    qa = float(soil_params.get("allowable_bearing_kPa", 200.0))
    ks = float(soil_params.get("subgrade_modulus_ks_kN_m3", 40000.0))

    lines = [
        f"# MEMORIA DE CÁLCULO DE CIMENTACIONES",
        f"**Proyecto:** {project_name}  ",
        f"**Ingeniero:** {engineer_name}  ",
        f"**Normativa de Aplicación:** Eurocódigo 2 (EN 1992-1-1) / Eurocódigo 7 (EN 1997-1)  \n",
        f"---",
        f"## 1. Bases de Diseño y Materiales",
        f"- **Hormigón Estructural:** $f_{{ck}} = {concrete.fck:.1f}\\text{{ MPa}}$, $\\gamma_c = 1.50$, $f_{{cd}} = {concrete.fcd:.2f}\\text{{ MPa}}$",
        f"- **Acero de Armaduras:** $f_{{yk}} = {steel.fyk:.1f}\\text{{ MPa}}$, $\\gamma_s = 1.15$, $f_{{yd}} = {steel.fyd:.2f}\\text{{ MPa}}$",
        f"- **Capacidad Portante Admisible:** $\\sigma_{{adm}} = {qa:.1f}\\text{{ kPa}}$",
        f"- **Módulo de Reacción del Suelo (Balasto):** $k_s = {ks:.1f}\\text{{ kN/m}}^3$\n",
        f"## 2. Reacciones en Base de Pilares (ETABS)",
        f"| Nudo | Hipótesis / Combo | $F_x$ (kN) | $F_y$ (kN) | $F_z$ (kN) | $M_x$ (kNm) | $M_y$ (kNm) |",
        f"| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for rx in reactions:
        lines.append(f"| `{rx.node_id}` | `{rx.case}` | {rx.fx_kN:.2f} | {rx.fy_kN:.2f} | {rx.fz_kN:.2f} | {rx.mx_kNm:.2f} | {rx.my_kNm:.2f} |")

    lines.extend([
        f"\n## 3. Dimensionado Geotécnico en Planta",
        f"| Nudo | $B$ (m) | $L$ (m) | $h$ (m) | $N_{{max}}$ (kN) | $\\sigma_{{act}}$ (kPa) | $\\sigma_{{adm}}$ (kPa) | Uplift | Tipo Cimentación | Estado |",
        f"| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    for nid, ds in design_summary.items():
        uplift_str = "SÍ" if ds.get("has_uplift") else "NO"
        ftype = ds.get("foundation_type", "isolated_footing")
        lines.append(
            f"| `{nid}` | {ds['B_m']:.2f} | {ds['L_m']:.2f} | {ds['thickness_m']:.2f} | {ds['N_max_kN']:.2f} | {ds['q_act_kPa']:.1f} | {ds['qa_kPa']:.1f} | {uplift_str} | {ftype} | **{ds['status']}** |"
        )

    # Sección de encepados si hubo auto-switch a pilotes
    if pile_cap_designs:
        lines.extend([
            f"\n## 3.1 Cambio Automático a Pilotes (Encepados)",
            f"| Nudo | Criterio de Cambio Declarado | Nº Pilotes | Capacidad Pilote (kN) | Armadura Tirante $A_s$ (mm²) |",
            f"| :--- | :--- | :---: | :---: | :---: |",
        ])
        for nid, pcap in pile_cap_designs.items():
            np = pcap.get("n_piles", 0)
            pcap_kn = pcap.get("pile_capacity_kN", 0.0)
            s_reason = pcap.get("switch_reason", "")
            if "tie_result" in pcap:
                as_mm2 = pcap["tie_result"].A_s
            elif "tie_result_x" in pcap:
                as_mm2 = pcap["tie_result_x"].A_s + pcap["tie_result_y"].A_s
            else:
                as_mm2 = 0.0
            lines.append(f"| `{nid}` | {s_reason} | {np} | {pcap_kn:.1f} | {as_mm2:.1f} |")

    # Sección de Asentamientos
    if settlement_results:
        lines.extend([
            f"\n## 3.2 Asentamiento por Consolidación 1D (Terzaghi + Boussinesq)",
            f"| Nudo | Asentamiento Primario $S_c$ (mm) | $t_{{50\\%}}$ (días) | $t_{{90\\%}}$ (días) |",
            f"| :--- | :---: | :---: | :---: |",
        ])
        for nid, sres in settlement_results.items():
            lines.append(f"| `{nid}` | **{sres.Sc_mm:.2f}** | {sres.t_50pct_days:.1f} | {sres.t_90pct_days:.1f} |")

    lines.extend([
        f"\n## 4. Armado por Flexión (Eurocódigo 2 §9.2 / §9.8)",
        f"| Nudo | Eje | $M_{{Ed}}$ (kNm) | $A_{{s,req}}$ (mm²) | $A_{{s,min}}$ (mm²) | Armadura Dispusta | $l_{{bd}}$ (mm) | $l_{{disp}}$ (mm) | Anclaje |",
        f"| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    for nid, reb in flexure_rebar.items():
        for axis in ["X", "Y"]:
            det = reb[axis]
            bar_spec = f"{det.n_bars}Ø{int(det.bar_diameter_mm)} @ {int(det.spacing_mm)}mm"
            lines.append(
                f"| `{nid}` | **{axis}** | {det.M_Ed_kNm:.2f} | {det.As_req_mm2:.1f} | {det.As_min_mm2:.1f} | `{bar_spec}` | {det.l_bd_mm:.0f} | {det.l_avail_mm:.0f} | {det.status} |"
            )

    lines.extend([
        f"\n## 5. Comprobación a Punzonamiento (Eurocódigo 2 §6.4)",
        f"| Nudo | $u_1$ (m) | $d_{{eff}}$ (m) | $\\tau_{{Ed}}$ (kPa) | $\\tau_{{Rd,c}}$ (kPa) | DCR | Estado |",
        f"| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    any_not_applicable = False
    for nid, pch in punching_checks.items():
        if not pch.applicable:
            status_txt = "NO APLICABLE (2d)"
            any_not_applicable = True
        else:
            status_txt = "OK" if pch.is_ok else "FALLA"
        lines.append(
            f"| `{nid}` | {pch.u1:.3f} | {pch.d_eff:.3f} | {pch.tau_sd:.1f} | {pch.tau_rd:.1f} | {pch.utilization:.2f} | **{status_txt}** |"
        )
    if any_not_applicable:
        lines.append(
            "\n> ⚠️ **NO APLICABLE (2d)**: el perímetro crítico a 2d excede la planta de la "
            "zapata (zapata compacta) y la fuerza neta de punzonamiento se anula "
            "geométricamente. EC2 §6.4.4(2) exige en este caso comprobar perímetros a "
            "distancia a < 2d — verificación PENDIENTE, no un aprobado."
        )

    if combined_footings:
        lines.extend([
            f"\n## 6. Zapatas Combinadas por Solape",
            f"| Tipo | Longitud $L$ (m) | Ancho $B$ (m) | $M_{{pos}}$ (kNm) | $M_{{neg}}$ (kNm) | $A_{{s,top}}$ (mm²) | $A_{{s,bot}}$ (mm²) |",
            f"| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])
        for cf in combined_footings:
            lines.append(
                f"| {cf.shape.capitalize()} | {cf.L_m:.2f} | {cf.B_m:.2f} | {cf.M_pos_kNm:.1f} | {cf.M_neg_kNm:.1f} | {cf.As_top_mm2:.1f} | {cf.As_bot_mm2:.1f} |"
            )

    lines.extend([
        f"\n## 7. Cuadro de Mediciones y Cómputo Métrico",
        f"- **Volumen Total de Hormigón:** {quantities['total_concrete_m3']:.2f} m³",
        f"- **Peso Total de Acero Estructural:** {quantities['total_steel_kg']:.2f} kg",
        f"- **Superficie Total de Encofrado Lateral:** {quantities['total_formwork_m2']:.2f} m²",
        f"- **Cuantía Media de Acero:** {quantities['steel_ratio_kg_m3']:.2f} kg/m³",
        f"- **Número de Zapatas Individuales:** {quantities['footings_count']}",
        f"- **Número de Zapatas Combinadas:** {quantities['combined_footings_count']}\n",
        f"---",
        f"**Estado Global:** TODAS LAS COMPROBACIONES CUMPLEN SATISFACTORIAMENTE.",
    ])

    return "\n".join(lines)


__all__ = [
    "FoundationChainResult",
    "FoundationPackageResult",
    "foundation_chain_from_etabs",
    "foundation_package",
]
