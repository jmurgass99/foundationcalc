"""foundationcalc._common.model
==========================
Modelo de dominio estructural canonico UNICO para APIS Structural JM (Sprint 1C).

Dataclasses frozen con unidades explicitas en el nombre de cada campo (kN, m, °C
canonicos). Dos capas explicitas y separadas:

    physical    lo que se construye: Story, Grid, Section, Material, Frame, Wall,
                Slab, Opening, Foundation (posicion y dimensiones reales)
    analytical  lo que se calcula: Node, Support/Restraint, Release, Offset,
                Element/AnalyticalMember, AnalyticalPanel, Diaphragm, cargas,
                LoadCase, LoadCombination
    project     Project y AnalyticalRelationship (enlace fisico <-> analitico)
    provenance  Layer, Provenance y la base Traceable (identity: ObjectIdentity)
    core        Model (raiz) y serializacion to_dict/from_dict/to_json/from_json
    schema      JSON Schema derivado y determinista

Sin dependencias de producto: aqui no existe COM, FamilyInstance, CLR ni IFC.
Los nombres legacy (Node, Restraint, Element, ...) conservan firma y defaults.
Los resultados de analisis/diseno NO viven aqui (ResultTable, CSIHingeResult,
CalculationStatus siguen en sus contratos).
"""
from __future__ import annotations

from .provenance import Layer, Provenance, Traceable
from .analytical import (AnalyticalMember, AnalyticalPanel, Diaphragm, Element, ElementLoad, LoadCase,
                         LoadCombination, LoadPattern, MassSource, NodalLoad, Node, Offset, Reaction, Release,
                         Restraint, SectionRef, Support)
from .physical import Foundation, Frame, Grid, Material, Opening, Point3, Section, Slab, Story, Wall
from .project import AnalyticalRelationship, Project
from .core import SCHEMA_VERSION, Model, from_dict, from_json, to_dict, to_json

__all__ = [
    # legacy
    "Node", "Restraint", "Material", "SectionRef", "Element", "LoadPattern", "NodalLoad", "ElementLoad",
    "MassSource", "LoadCase", "Reaction", "Model", "to_dict", "from_dict", "to_json", "from_json",
    # provenance / identity
    "Layer", "Provenance", "Traceable",
    # analytical
    "Support", "Release", "Offset", "AnalyticalMember", "AnalyticalPanel", "Diaphragm", "LoadCombination",
    # physical
    "Point3", "Section", "Story", "Grid", "Frame", "Wall", "Slab", "Opening", "Foundation",
    # meta
    "Project", "AnalyticalRelationship", "SCHEMA_VERSION",
]
