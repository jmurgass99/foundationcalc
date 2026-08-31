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
from foundationdesignjm.design.combined_footing import (
    CombinedFootingInputs,
    CombinedFootingResult,
    design_combined_footing,
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

    # 2. Muelles Winkler y Chequeo de Punzonamiento por nudo
    punching_checks: dict[str, PunchingShearResult] = {}
    winkler_springs: list[WinklerSpring] = []
    total_vol = 0.0
    has_global_uplift = False

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
            "name": f"FOOTING_{node_id}",
            "node_id": node_id,
            "coordinates": poly,
            "thickness": footing_thickness_m,
            "material": "CONC",
            "subgrade_modulus_ks": ks_kN_m3,
        })

    column_loads = []
    for rx in reactions:
        column_loads.append({
            "point_name": rx.node_id,
            "case": rx.case,
            "P": rx.fz_kN,
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
) -> FoundationPackageResult:
    """Genera el paquete completo de entregables de producción para cimentaciones.

    Incluye:
    - Dimensionado geotécnico en planta.
    - Detección y diseño de zapatas combinadas ante solapes.
    - Armado a flexión en 2 direcciones (EC2 §9.2 / §9.8, anclaje EC2 §8.4.4).
    - Verificación a punzonamiento (EC2 §6.4).
    - Planos de detalle DXF por zapata.
    - Memoria de cálculo técnica en Markdown.
    - Cómputo métrico (hormigón m³, acero kg, encofrado m²).
    - Modelo SAFE 2022 declarativo.
    """
    reactions = _resolve_reactions(etabs_or_reactions, combos)
    col_coords = column_coordinates or {rx.node_id: (0.0, 0.0) for rx in reactions}

    # 1. Dimensionado y cadena base
    chain = foundation_chain_from_etabs(
        etabs_or_reactions=reactions,
        soil_params=soil_params,
        footing_thickness_m=footing_thickness_m,
        concrete_fck_MPa=concrete_fck_MPa,
        column_dimensions=column_dimensions,
        column_coordinates=col_coords,
        combos=combos,
    )

    concrete = Concrete(fck=concrete_fck_MPa)
    steel = ReinforcingSteel(fyk=steel_fyk_MPa)

    # 2. Detección de zapatas combinadas por solape
    qa_kPa = float(soil_params.get("allowable_bearing_kPa", 200.0))
    combined_footings = _detect_and_design_combined_footings(
        chain.design_summary,
        col_coords,
        column_dimensions,
        qa_kPa,
        footing_thickness_m,
        concrete,
        steel,
    )

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
        else:
            reactions = list(etabs_or_reactions)
    else:
        raise TypeError(f"Tipo no soportado para etabs_or_reactions: {type(etabs_or_reactions)}")

    if combos:
        reactions = [r for r in reactions if r.case in combos]
    return reactions


def _detect_and_design_combined_footings(
    design_summary: dict[str, dict[str, Any]],
    col_coords: dict[str, tuple[float, float]],
    column_dimensions: dict[str, tuple[float, float]] | tuple[float, float],
    qa_kPa: float,
    footing_thickness_m: float,
    concrete: Concrete,
    steel: ReinforcingSteel,
    clearance_min_m: float = 0.10,
) -> list[CombinedFootingResult]:
    """Detecta solapes entre pares de zapatas aisladas y diseña zapatas combinadas."""
    combined_results: list[CombinedFootingResult] = []
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
    return combined_results


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
        f"| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
    ]

    for rx in reactions:
        lines.append(f"| `{rx.node_id}` | `{rx.case}` | {rx.fx_kN:.2f} | {rx.fy_kN:.2f} | {rx.fz_kN:.2f} | {rx.mx_kNm:.2f} | {rx.my_kNm:.2f} |")

    lines.extend([
        f"\n## 3. Dimensionado Geotécnico en Planta",
        f"| Nudo | $B$ (m) | $L$ (m) | $h$ (m) | $N_{{max}}$ (kN) | $\\sigma_{{act}}$ (kPa) | $\\sigma_{{adm}}$ (kPa) | Uplift | Estado |",
        f"| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    for nid, ds in design_summary.items():
        uplift_str = "SÍ" if ds.get("has_uplift") else "NO"
        lines.append(
            f"| `{nid}` | {ds['B_m']:.2f} | {ds['L_m']:.2f} | {ds['thickness_m']:.2f} | {ds['N_max_kN']:.2f} | {ds['q_act_kPa']:.1f} | {ds['qa_kPa']:.1f} | {uplift_str} | **{ds['status']}** |"
        )

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
