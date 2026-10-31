"""`Model`: raiz del modelo canonico UNICO, con serializacion generica sin perdida.

Compatibilidad: los once campos legacy conservan nombre, orden y defaults; los
nuevos van despues con default `()` / `None`. `to_dict` conserva tuplas (como
`asdict`) y serializa `ObjectIdentity` como dict; `from_dict` reconstruye por
las anotaciones de tipo de cada dataclass (acepta listas o tuplas y dicts sin
las claves nuevas).
"""
from __future__ import annotations

import dataclasses
import json
import math
import types
import typing
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

from ..identity import ObjectIdentity
from .analytical import (AnalyticalPanel, Diaphragm, Element, ElementLoad, LoadCase, LoadCombination, LoadPattern,
                         MassSource, NodalLoad, Node, Reaction, Restraint, SectionRef, Support)
from .physical import Foundation, Frame, Grid, Material, Opening, Section, Slab, Story, Wall
from .project import AnalyticalRelationship, Project

SCHEMA_VERSION = "2.0"

#: Tolerancia de coincidencia de nudos, en metros. 1e-4 m = 0,1 mm (regla legacy).
NODE_TOLERANCE_M = 1e-4

#: Desplazamientos del cubo 3x3x3 alrededor de una celda de la rejilla espacial.
_CELDAS_VECINAS = tuple((dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1))


def assert_no_coincident_nodes(nodes: Sequence[Node], tol_m: float = NODE_TOLERANCE_M) -> None:
    """Rechaza nudos separados menos de `tol_m`, en tiempo LINEAL (fase 1E.1).

    Rejilla espacial (spatial hash) con celda de lado igual a la tolerancia: si
    dos nudos distan menos de `tol_m`, cada una de sus coordenadas difiere menos
    de `tol_m`, luego sus indices de celda difieren como mucho en 1 por eje y
    caen forzosamente dentro del cubo 3x3x3 alrededor del nudo. Basta con mirar
    esas 27 celdas.

    Sustituye a un doble bucle cuadratico. Medido en este repositorio antes del
    cambio: 4 000 nudos 7,64 s y 20 000 nudos 188,8 s, lo que hacia inviable
    importar un modelo real de ETABS. Se conservan exactamente la tolerancia, el
    texto del error y el orden de aparicion de los dos nudos en el mensaje.
    """
    rejilla: dict[tuple[int, int, int], list[Node]] = {}
    tol2 = tol_m * tol_m
    for nuevo in nodes:
        cx = math.floor(nuevo.x_m / tol_m)
        cy = math.floor(nuevo.y_m / tol_m)
        cz = math.floor(nuevo.z_m / tol_m)
        for dx, dy, dz in _CELDAS_VECINAS:
            for previo in rejilla.get((cx + dx, cy + dy, cz + dz), ()):
                d2 = ((nuevo.x_m - previo.x_m) ** 2 + (nuevo.y_m - previo.y_m) ** 2
                      + (nuevo.z_m - previo.z_m) ** 2)
                if d2 < tol2:
                    d = math.sqrt(d2)
                    raise ValueError(
                        f"Nudos duplicados o excesivamente cercanos ({d*1000:.3f} mm): "
                        f"'{previo.id}' y '{nuevo.id}'")
        rejilla.setdefault((cx, cy, cz), []).append(nuevo)


def _dup(items: Any, key: str, what: str) -> None:
    seen: set[str] = set()
    for it in items:
        k = getattr(it, key)
        if k in seen:
            raise ValueError(f"{what} duplicado: '{k}'")
        seen.add(k)


@dataclass(frozen=True)
class Model:
    """Modelo estructural canonico completo (capas fisica y analitica + metadatos)."""
    # ----- legacy (orden y defaults intactos) -----
    nodes: tuple[Node, ...] = ()
    restraints: tuple[Support, ...] = ()
    materials: tuple[Material, ...] = ()
    sections: tuple[SectionRef, ...] = ()
    elements: tuple[Element, ...] = ()
    patterns: tuple[LoadPattern, ...] = ()
    nodal_loads: tuple[NodalLoad, ...] = ()
    element_loads: tuple[ElementLoad, ...] = ()
    mass_source: MassSource | None = None
    cases: tuple[LoadCase, ...] = ()
    reactions: tuple[Reaction, ...] = ()
    # ----- meta -----
    schema_version: str = SCHEMA_VERSION
    project: Project | None = None
    # ----- fisico -----
    stories: tuple[Story, ...] = ()
    grids: tuple[Grid, ...] = ()
    section_properties: tuple[Section, ...] = ()
    frames: tuple[Frame, ...] = ()
    walls: tuple[Wall, ...] = ()
    slabs: tuple[Slab, ...] = ()
    openings: tuple[Opening, ...] = ()
    foundations: tuple[Foundation, ...] = ()
    # ----- analitico (nuevo) -----
    panels: tuple[AnalyticalPanel, ...] = ()
    diaphragms: tuple[Diaphragm, ...] = ()
    combinations: tuple[LoadCombination, ...] = ()
    # ----- enlace entre capas -----
    relationships: tuple[AnalyticalRelationship, ...] = ()

    def __post_init__(self) -> None:
        nodes_map: dict[str, Node] = {n.id: n for n in self.nodes}

        # 1. Nudos duplicados o coincidentes (regla legacy: 0.1 mm), en tiempo lineal
        assert_no_coincident_nodes(self.nodes)

        # 2. Miembros analiticos (regla legacy)
        for el in self.elements:
            if el.node_i not in nodes_map:
                raise ValueError(f"Elemento '{el.id}': nudo inicial '{el.node_i}' no existe en el modelo")
            if el.node_j not in nodes_map:
                raise ValueError(f"Elemento '{el.id}': nudo final '{el.node_j}' no existe en el modelo")
            ni, nj = nodes_map[el.node_i], nodes_map[el.node_j]
            L = math.sqrt((nj.x_m - ni.x_m) ** 2 + (nj.y_m - ni.y_m) ** 2 + (nj.z_m - ni.z_m) ** 2)
            if L < 1e-6:
                raise ValueError(f"Elemento '{el.id}' tiene longitud nula ({L:.4e} m) entre '{el.node_i}' y '{el.node_j}'")

        # 3. Unicidad de ids en las colecciones nuevas
        _dup(self.stories, "name", "story")
        _dup(self.grids, "name", "grid")
        _dup(self.section_properties, "name", "section")
        for coll, what in ((self.frames, "frame"), (self.walls, "wall"), (self.slabs, "slab"),
                           (self.openings, "opening"), (self.foundations, "foundation"), (self.panels, "panel")):
            _dup(coll, "id", what)
        _dup(self.diaphragms, "name", "diaphragm")
        _dup(self.combinations, "name", "combination")

        # 4. Referencias de la capa fisica
        story_names = {s.name for s in self.stories}
        for ent in (*self.frames, *self.walls, *self.slabs):
            if ent.story_id and story_names and ent.story_id not in story_names:
                raise ValueError(f"'{ent.id}': story '{ent.story_id}' no existe en el modelo")
        hosts = {w.id for w in self.walls} | {s.id for s in self.slabs}
        for op in self.openings:
            if op.host_id not in hosts:
                raise ValueError(f"Opening '{op.id}': host '{op.host_id}' no es un muro ni una losa del modelo")
        for fd in self.foundations:
            for nid in fd.support_node_ids:
                if nodes_map and nid not in nodes_map:
                    raise ValueError(f"Foundation '{fd.id}': nudo '{nid}' no existe en el modelo")

        # 5. Referencias de la capa analitica nueva
        for p in self.panels:
            for nid in p.node_ids:
                if nid not in nodes_map:
                    raise ValueError(f"Panel '{p.id}': nudo '{nid}' no existe en el modelo")
        for dph in self.diaphragms:
            for nid in dph.node_ids:
                if nid not in nodes_map:
                    raise ValueError(f"Diafragma '{dph.name}': nudo '{nid}' no existe en el modelo")
            if dph.story_id and story_names and dph.story_id not in story_names:
                raise ValueError(f"Diafragma '{dph.name}': story '{dph.story_id}' no existe en el modelo")
        case_names = {c.name for c in self.cases}
        combo_names = {c.name for c in self.combinations}
        for cb in self.combinations:
            for ref, _ in cb.terms:
                if ref not in case_names and ref not in combo_names:
                    raise ValueError(f"Combinacion '{cb.name}': el caso o combinacion '{ref}' no existe en el modelo")

        # 6. Relaciones fisico <-> analitico
        physical_ids = ({f.id for f in self.frames} | {w.id for w in self.walls} | {s.id for s in self.slabs}
                        | {f.id for f in self.foundations})
        analytical_ids = {e.id for e in self.elements} | {p.id for p in self.panels}
        seen_an: set[str] = set()
        for rel in self.relationships:
            if rel.physical_id not in physical_ids or rel.analytical_id not in analytical_ids:
                raise ValueError(f"relacion {rel.physical_id} -> {rel.analytical_id}: id fisico o analitico inexistente")
            if rel.analytical_id in seen_an:
                raise ValueError(f"relacion: el analitico '{rel.analytical_id}' ya tiene un fisico (0..1)")
            seen_an.add(rel.analytical_id)

    # ----- consultas -----
    def section_by_name(self, name: str) -> Section | None:
        return next((s for s in self.section_properties if s.name == name), None)

    def analytical_of(self, physical_id: str) -> tuple[str, ...]:
        rels = sorted((r for r in self.relationships if r.physical_id == physical_id), key=lambda r: r.order)
        return tuple(r.analytical_id for r in rels)

    def physical_of(self, analytical_id: str) -> str | None:
        return next((r.physical_id for r in self.relationships if r.analytical_id == analytical_id), None)

    # ----- serializacion -----
    def to_dict(self) -> dict[str, Any]:
        """Serializa el modelo a diccionario compatible JSON."""
        return to_dict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Model":
        """Reconstruye un modelo canonico desde diccionario."""
        return from_dict(d)


# -----------------------------------------------------------------------------
# Serializacion generica (por anotaciones de tipo)
# -----------------------------------------------------------------------------
def _encode(value: Any) -> Any:
    if isinstance(value, ObjectIdentity):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _encode(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return tuple(_encode(v) for v in value)
    if isinstance(value, list):
        return [_encode(v) for v in value]
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in value.items()}
    return value


def _decode(tp: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        inner = [a for a in args if a is not type(None)]
        return _decode(inner[0], value) if len(inner) == 1 else value
    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode(args[0], v) for v in value)
        return tuple(_decode(a, v) for a, v in zip(args, value))
    if origin is list:
        return [_decode(args[0], v) for v in value]
    if tp is ObjectIdentity:
        return value if isinstance(value, ObjectIdentity) else ObjectIdentity.model_validate(value)
    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        if isinstance(value, tp):
            return value
        hints = typing.get_type_hints(tp)
        kwargs = {f.name: _decode(hints[f.name], value[f.name]) for f in dataclasses.fields(tp) if f.name in value}
        return tp(**kwargs)
    if isinstance(tp, type) and issubclass(tp, Enum):
        return tp(value)
    if tp is float and isinstance(value, (int, float)):
        return float(value)
    return value


def to_dict(model: Model) -> dict[str, Any]:
    """Serializa el modelo a un diccionario serializable JSON (tuplas conservadas)."""
    return _encode(model)


def from_dict(d: dict[str, Any]) -> Model:
    """Reconstruye un modelo canonico a partir de un diccionario (legacy o 2.0)."""
    return _decode(Model, d)


def to_json(model: Model, indent: int = 2) -> str:
    """Serializa el modelo canonico a string JSON."""
    return json.dumps(to_dict(model), indent=indent, ensure_ascii=False)


def from_json(json_str: str) -> Model:
    """Deserializa un string JSON a Model canonico."""
    return from_dict(json.loads(json_str))


__all__ = ["Model", "SCHEMA_VERSION", "NODE_TOLERANCE_M", "assert_no_coincident_nodes",
           "to_dict", "from_dict", "to_json", "from_json"]
