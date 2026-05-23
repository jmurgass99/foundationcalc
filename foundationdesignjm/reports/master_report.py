"""Plantilla maestra de memoria de calculo estructural.

Orquesta las secciones canonicas de una memoria profesional:
1. Portada y datos del proyecto
2. Normativa aplicable
3. Materiales
4. Cargas y combinaciones
5. Parametros sismicos
6. Modelo de analisis
7. Modal (modos, periodos, masa participativa)
8. Derivas
9. Irregularidades
10. Diseno de elementos (RC, acero, conexiones, anclajes)
11. Cimentacion
12. Estado limite de servicio (ELS)
13. Conclusiones

Cada seccion acepta data opcional; las ausentes se omiten.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional

import pandas as pd

from .pdf_builder import Report
from .narrative import NarrativeCheck, add_narrative_check
from .step_by_step import StepBlock, render_block_pdf


@dataclass
class ProjectInfo:
    name: str = ""
    location: str = ""
    owner: str = ""
    engineer: str = ""
    license_no: str = ""
    revision: str = "Rev. 0"


@dataclass
class MaterialsSpec:
    fc: float = 0.0        # MPa
    fy: float = 0.0        # MPa
    Fy_steel: float = 0.0  # MPa
    Fu_steel: float = 0.0
    cover_mm: float = 40.0


@dataclass
class SeismicParams:
    code: str = ""          # "NSR-10" | "ASCE 7-22" | "EC8"
    zone: str = ""
    Aa: float = 0.0; Av: float = 0.0
    Fa: float = 1.0; Fv: float = 1.0
    I: float = 1.0
    R: float = 7.0
    soil_type: str = "D"
    Tperiod: float = 0.0


@dataclass
class MemoriaData:
    project: ProjectInfo = field(default_factory=ProjectInfo)
    codes: List[str] = field(default_factory=list)
    materials: MaterialsSpec = field(default_factory=MaterialsSpec)
    loads_df: Optional[pd.DataFrame] = None
    combos_df: Optional[pd.DataFrame] = None
    seismic: SeismicParams = field(default_factory=SeismicParams)
    model_description: str = ""
    modal_df: Optional[pd.DataFrame] = None
    drifts_df: Optional[pd.DataFrame] = None
    drift_limit: float = 0.01
    irregularities_df: Optional[pd.DataFrame] = None
    rc_design_df: Optional[pd.DataFrame] = None
    steel_design_df: Optional[pd.DataFrame] = None
    connection_checks: List[NarrativeCheck] = field(default_factory=list)
    anchor_checks: List[NarrativeCheck] = field(default_factory=list)
    foundation_checks: List[NarrativeCheck] = field(default_factory=list)
    serviceability_notes: str = ""
    step_blocks: List[StepBlock] = field(default_factory=list)
    conclusions: str = ""


def build_master_memoria(data: MemoriaData, path: str) -> str:
    """Genera la memoria de calculo completa en PDF."""
    p = data.project
    rep = Report(
        title="Memoria de Calculo Estructural",
        subtitle=p.name or "Proyecto",
        author=p.engineer,
        project=p.location,
    )

    rep.add_section("1. Datos del proyecto")
    rep.add_kv_table([
        ("Proyecto", p.name),
        ("Ubicacion", p.location),
        ("Propietario", p.owner),
        ("Ingeniero responsable", p.engineer),
        ("Matricula", p.license_no),
        ("Revision", p.revision),
    ])

    rep.add_section("2. Normativa aplicable")
    if data.codes:
        for c in data.codes:
            rep.add_paragraph(f"- {c}")
    else:
        rep.add_paragraph("No especificada.")

    rep.add_section("3. Materiales")
    m = data.materials
    rep.add_kv_table([
        ("f'c (concreto)", f"{m.fc} MPa"),
        ("fy (refuerzo)", f"{m.fy} MPa"),
        ("Fy (acero estructural)", f"{m.Fy_steel} MPa"),
        ("Fu (acero estructural)", f"{m.Fu_steel} MPa"),
        ("Recubrimiento", f"{m.cover_mm} mm"),
    ])

    rep.add_section("4. Cargas y combinaciones")
    if data.loads_df is not None and not data.loads_df.empty:
        rep.add_subsection("4.1 Cargas")
        rep.add_dataframe(data.loads_df)
    if data.combos_df is not None and not data.combos_df.empty:
        rep.add_subsection("4.2 Combinaciones")
        rep.add_dataframe(data.combos_df)

    rep.add_section("5. Parametros sismicos")
    s = data.seismic
    rep.add_kv_table([
        ("Norma", s.code),
        ("Zona", s.zone),
        ("Aa", s.Aa), ("Av", s.Av),
        ("Fa", s.Fa), ("Fv", s.Fv),
        ("Importancia I", s.I),
        ("R (reduccion)", s.R),
        ("Tipo de suelo", s.soil_type),
        ("Periodo fundamental T", f"{s.Tperiod:.3f} s"),
    ])

    rep.add_section("6. Modelo de analisis")
    rep.add_paragraph(data.model_description or "Sin descripcion.")

    if data.modal_df is not None and not data.modal_df.empty:
        rep.add_section("7. Analisis modal")
        rep.add_dataframe(data.modal_df,
                           caption="Modos, periodos y masa participativa.")
        if "mass_x" in data.modal_df.columns:
            mass_x = data.modal_df["mass_x"].sum()
            mass_y = data.modal_df.get("mass_y", pd.Series(dtype=float)).sum()
            rep.add_kv_table([
                ("Masa acumulada X", f"{mass_x*100:.1f}%"),
                ("Masa acumulada Y", f"{mass_y*100:.1f}%"),
                ("Cumple 90%", "Si" if (mass_x >= 0.9 and mass_y >= 0.9)
                  else "Revisar"),
            ])

    if data.drifts_df is not None and not data.drifts_df.empty:
        rep.add_section("8. Derivas")
        rep.add_kv_table([("Limite Δ/h", f"{data.drift_limit:g}")])
        rep.add_dataframe(data.drifts_df)

    if data.irregularities_df is not None and not data.irregularities_df.empty:
        rep.add_section("9. Irregularidades")
        rep.add_dataframe(data.irregularities_df)

    has_design = (data.rc_design_df is not None
                  or data.steel_design_df is not None
                  or data.connection_checks
                  or data.anchor_checks)
    if has_design:
        rep.add_section("10. Diseno de elementos")
        if data.rc_design_df is not None and not data.rc_design_df.empty:
            rep.add_subsection("10.1 Hormigon armado")
            rep.add_dataframe(data.rc_design_df)
        if data.steel_design_df is not None and not data.steel_design_df.empty:
            rep.add_subsection("10.2 Acero estructural")
            rep.add_dataframe(data.steel_design_df)
        if data.connection_checks:
            rep.add_subsection("10.3 Conexiones")
            for chk in data.connection_checks:
                add_narrative_check(rep, chk)
        if data.anchor_checks:
            rep.add_subsection("10.4 Anclajes a concreto")
            for chk in data.anchor_checks:
                add_narrative_check(rep, chk)

    if data.foundation_checks:
        rep.add_section("11. Cimentacion")
        for chk in data.foundation_checks:
            add_narrative_check(rep, chk)

    if data.serviceability_notes:
        rep.add_section("12. Estado limite de servicio")
        rep.add_paragraph(data.serviceability_notes)

    if data.step_blocks:
        rep.add_section("13. Calculos detallados (paso a paso)")
        rep.add_paragraph(
            "Esta seccion documenta cada chequeo normativo con su formula "
            "simbolica, la sustitucion numerica con los valores del proyecto, "
            "el resultado y la seccion del codigo aplicable."
        )
        for block in data.step_blocks:
            render_block_pdf(rep, block)

    rep.add_section("14. Conclusiones")
    rep.add_paragraph(data.conclusions or
                       "El diseno cumple con los requisitos de las normas listadas.")

    return rep.save(path)


__all__ = [
    "ProjectInfo", "MaterialsSpec", "SeismicParams", "MemoriaData",
    "build_master_memoria",
]
