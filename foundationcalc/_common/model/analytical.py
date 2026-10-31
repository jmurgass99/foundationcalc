"""Capa ANALITICA del modelo canonico: lo que se calcula.

Nudos, miembros (ejes), paneles, apoyos, releases, offsets, diafragmas, cargas,
patrones, casos y combinaciones. Sin dimensiones fisicas: la seccion es una
referencia por nombre (`SectionRef`); las propiedades geometricas de la seccion
viven en la capa fisica (`physical.Section`).

Nombres legacy conservados con la misma firma posicional: `Node`, `Restraint`,
`Element`, `LoadPattern`, `NodalLoad`, `ElementLoad`, `MassSource`, `LoadCase`,
`Reaction`. `Support` es el nombre canonico del apoyo (`Restraint` sigue siendo
el mismo objeto). `AnalyticalMember` es el nombre canonico de `Element`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .provenance import Layer, Traceable


@dataclass(frozen=True)
class Node(Traceable):
    """Nudo analitico 3D."""
    layer = Layer.ANALYTICAL
    id: str
    x_m: float
    y_m: float
    z_m: float
    mass_kg: float = 0.0


@dataclass(frozen=True)
class Support(Traceable):
    """Apoyo / condicion de contorno en un nudo (6 GDL restringidos)."""
    layer = Layer.ANALYTICAL
    node_id: str
    ux: bool = False
    uy: bool = False
    uz: bool = False
    rx: bool = False
    ry: bool = False
    rz: bool = False


Restraint = Support  # nombre legacy (mismo objeto)


@dataclass(frozen=True)
class Release:
    """Liberacion de extremo (True = liberado) en ejes locales."""
    ux: bool = False
    uy: bool = False
    uz: bool = False
    rx: bool = False
    ry: bool = False
    rz: bool = False

    @property
    def dofs(self) -> tuple[bool, bool, bool, bool, bool, bool]:
        return (self.ux, self.uy, self.uz, self.rx, self.ry, self.rz)


@dataclass(frozen=True)
class Offset:
    """Desplazamiento de extremo (ejes locales) entre eje analitico y nudo."""
    dx_m: float = 0.0
    dy_m: float = 0.0
    dz_m: float = 0.0
    cardinal_point: int | None = None


@dataclass(frozen=True)
class SectionRef:
    """Referencia por nombre al catalogo/propiedades de seccion (capa fisica)."""
    name: str
    family: str = "OTHER"


@dataclass(frozen=True)
class Element(Traceable):
    """Miembro analitico: eje entre dos nudos. `kind` COLUMN/BEAM/BRACE/NULL opcional."""
    layer = Layer.ANALYTICAL
    id: str
    node_i: str
    node_j: str
    section: SectionRef
    material: str
    rotation_deg: float = 0.0
    kind: str = field(default="", kw_only=True)
    release_i: Release | None = field(default=None, kw_only=True)
    release_j: Release | None = field(default=None, kw_only=True)
    offset_i: Offset | None = field(default=None, kw_only=True)
    offset_j: Offset | None = field(default=None, kw_only=True)


AnalyticalMember = Element  # nombre canonico


@dataclass(frozen=True)
class AnalyticalPanel(Traceable):
    """Panel analitico (muro, forjado o generico) definido por su contorno de nudos."""
    layer = Layer.ANALYTICAL
    id: str
    node_ids: tuple[str, ...]
    thickness_m: float
    material: str
    role: str = "GENERIC"                     # WALL | FLOOR | GENERIC
    opening_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.node_ids) < 3:
            raise ValueError(f"Panel '{self.id}': necesita al menos 3 nudos, tiene {len(self.node_ids)}")


@dataclass(frozen=True)
class Diaphragm(Traceable):
    """Diafragma (rigido/semirrigido) sobre un conjunto de nudos de un nivel."""
    layer = Layer.ANALYTICAL
    name: str
    story_id: str = ""
    node_ids: tuple[str, ...] = ()
    kind: str = "RIGID"


@dataclass(frozen=True)
class LoadPattern:
    """Patron de carga base."""
    name: str
    kind: str = "Other"  # "Dead", "Live", "Wind", "Quake", etc.
    self_weight_multiplier: float = 0.0


@dataclass(frozen=True)
class NodalLoad:
    """Fuerzas y momentos concentrados en un nudo."""
    node_id: str
    fx_kN: float = 0.0
    fy_kN: float = 0.0
    fz_kN: float = 0.0
    mx_kNm: float = 0.0
    my_kNm: float = 0.0
    mz_kNm: float = 0.0
    pattern: str = ""


@dataclass(frozen=True)
class ElementLoad:
    """Carga lineal uniformemente distribuida sobre un miembro."""
    element_id: str
    w_kN_m: float = 0.0
    direction: str = "Gravity"  # "Gravity", "LocalX", "LocalY", "LocalZ", "GlobalX", etc.
    pattern: str = ""


@dataclass(frozen=True)
class MassSource:
    """Definicion explicita de Mass Source a partir de patrones de carga."""
    from_patterns: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class LoadCase:
    """Caso de analisis (Lineal, Modal, Espectro, ...)."""
    name: str
    kind: str = "LinearStatic"  # "LinearStatic", "Modal", "ResponseSpectrum", "Nonlinear"
    patterns: tuple[tuple[str, float], ...] = ()
    mass_source: MassSource | None = None

    def __post_init__(self) -> None:
        k_lower = self.kind.lower()
        if k_lower in ("modal", "responsespectrum", "response_spectrum", "spectrum") and self.mass_source is None:
            raise ValueError(f"Caso de carga dinámico '{self.name}' ({self.kind}) requiere una Mass Source explícita.")


@dataclass(frozen=True)
class LoadCombination:
    """Combinacion de casos (o de combinaciones): terminos (referencia, factor)."""
    name: str
    terms: tuple[tuple[str, float], ...] = ()
    kind: str = "LINEAR"        # LINEAR | ENVELOPE | ABS | SRSS | RANGE
    design_type: str = ""       # STRENGTH | SERVICE | ...


@dataclass(frozen=True)
class Reaction:
    """Reaccion en un nudo para un caso (campo legacy; se conserva por compatibilidad)."""
    node_id: str
    fx_kN: float = 0.0
    fy_kN: float = 0.0
    fz_kN: float = 0.0
    mx_kNm: float = 0.0
    my_kNm: float = 0.0
    mz_kNm: float = 0.0
    case: str = ""


__all__ = [
    "Node", "Support", "Restraint", "Release", "Offset", "SectionRef", "Element", "AnalyticalMember",
    "AnalyticalPanel", "Diaphragm", "LoadPattern", "NodalLoad", "ElementLoad", "MassSource", "LoadCase",
    "LoadCombination", "Reaction",
]
