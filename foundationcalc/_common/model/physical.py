"""Capa FISICA del modelo canonico: lo que se construye.

Niveles, ejes de replanteo, secciones con propiedades, materiales, y elementos
fisicos con posicion y dimensiones reales (barras, muros, losas, huecos,
cimentaciones). Ninguna entidad de esta capa conoce nudos analiticos ni
releases: el enlace con la capa analitica es `project.AnalyticalRelationship`.

Coordenadas canonicas en metros (kN, m, °C fijos en el core; la conversion es
del adaptador). `Point3 = (x_m, y_m, z_m)`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .provenance import Layer, Traceable

Point3 = tuple[float, float, float]


def _check_outline(owner: str, outline: tuple[Point3, ...]) -> None:
    if len(outline) < 3:
        raise ValueError(f"'{owner}': el contorno necesita al menos 3 puntos, tiene {len(outline)}")


@dataclass(frozen=True)
class Material(Traceable):
    """Material estructural (campos legacy intactos + tipo y resistencia opcionales)."""
    layer = Layer.PHYSICAL
    name: str
    E_MPa: float
    nu: float = 0.3
    fy_MPa: float = 0.0
    rho_kg_m3: float = 0.0
    kind: str = ""              # CONCRETE | STEEL | TIMBER | MASONRY | ALUMINUM | OTHER
    fc_MPa: float = 0.0
    G_MPa: float = 0.0

    def __post_init__(self) -> None:
        if self.E_MPa <= 0.0:
            raise ValueError(f"E_MPa debe ser > 0, obtenido {self.E_MPa}")
        if not (-1.0 < self.nu < 0.5):
            raise ValueError(f"nu debe estar en (-1.0, 0.5), obtenido {self.nu}")
        if self.fy_MPa < 0.0:
            raise ValueError(f"fy_MPa debe ser >= 0, obtenido {self.fy_MPa}")
        if self.rho_kg_m3 < 0.0:
            raise ValueError(f"rho_kg_m3 debe ser >= 0, obtenido {self.rho_kg_m3}")
        if self.fc_MPa < 0.0 or self.G_MPa < 0.0:
            raise ValueError("fc_MPa y G_MPa deben ser >= 0")


@dataclass(frozen=True)
class Section(Traceable):
    """Seccion transversal con dimensiones y propiedades (la capa analitica la
    referencia por `SectionRef.name`)."""
    layer = Layer.PHYSICAL
    name: str
    family: str = "OTHER"       # RECT | CIRC | I | TUBE | CHANNEL | ANGLE | T | OTHER
    material: str = ""
    b_m: float = 0.0
    h_m: float = 0.0
    tw_m: float = 0.0
    tf_m: float = 0.0
    A_m2: float = 0.0
    Iy_m4: float = 0.0
    Iz_m4: float = 0.0
    J_m4: float = 0.0
    source_catalog: str = ""

    def __post_init__(self) -> None:
        for f in ("b_m", "h_m", "tw_m", "tf_m", "A_m2", "Iy_m4", "Iz_m4", "J_m4"):
            if getattr(self, f) < 0.0:
                raise ValueError(f"Seccion '{self.name}': {f} debe ser >= 0")

    def ref(self):
        from .analytical import SectionRef
        return SectionRef(self.name, self.family)


@dataclass(frozen=True)
class Story(Traceable):
    """Nivel de referencia."""
    layer = Layer.PHYSICAL
    name: str
    elevation_m: float
    height_m: float = 0.0
    is_base: bool = False
    is_master: bool = False
    similar_to: str = ""


@dataclass(frozen=True)
class Grid(Traceable):
    """Eje de replanteo (recto; los curvos llevan centro/radio opcionales)."""
    layer = Layer.PHYSICAL
    name: str
    start_m: Point3
    end_m: Point3
    center_m: Point3 | None = None
    radius_m: float = 0.0


@dataclass(frozen=True)
class Frame(Traceable):
    """Barra fisica (columna/viga/riostra) con posicion real de sus extremos."""
    layer = Layer.PHYSICAL
    id: str
    kind: str                   # COLUMN | BEAM | BRACE
    section: str                # nombre de Section
    material: str
    start_m: Point3
    end_m: Point3
    story_id: str = ""
    rotation_deg: float = 0.0
    justification: str = ""     # p. ej. "TOP_CENTER", "MIDDLE_CENTER"
    phase: str = ""

    def __post_init__(self) -> None:
        if self.length_m < 1e-6:
            raise ValueError(f"Frame '{self.id}': longitud nula")

    @property
    def length_m(self) -> float:
        return math.dist(self.start_m, self.end_m)


@dataclass(frozen=True)
class Wall(Traceable):
    """Muro fisico definido por su contorno (>= 3 puntos) y espesor."""
    layer = Layer.PHYSICAL
    id: str
    outline_m: tuple[Point3, ...]
    thickness_m: float
    material: str
    story_id: str = ""
    pier_label: str = ""

    def __post_init__(self) -> None:
        _check_outline(self.id, self.outline_m)
        if self.thickness_m <= 0.0:
            raise ValueError(f"Wall '{self.id}': thickness_m debe ser > 0")


@dataclass(frozen=True)
class Slab(Traceable):
    """Losa/forjado fisico definido por su contorno y espesor."""
    layer = Layer.PHYSICAL
    id: str
    outline_m: tuple[Point3, ...]
    thickness_m: float
    material: str
    story_id: str = ""
    deck_kind: str = ""         # SOLID | FILLED_DECK | UNFILLED_DECK | RIBBED | ...

    def __post_init__(self) -> None:
        _check_outline(self.id, self.outline_m)
        if self.thickness_m <= 0.0:
            raise ValueError(f"Slab '{self.id}': thickness_m debe ser > 0")


@dataclass(frozen=True)
class Opening(Traceable):
    """Hueco en un muro o losa (host)."""
    layer = Layer.PHYSICAL
    id: str
    host_id: str
    outline_m: tuple[Point3, ...]

    def __post_init__(self) -> None:
        _check_outline(self.id, self.outline_m)


@dataclass(frozen=True)
class Foundation(Traceable):
    """Cimentacion fisica (zapata, pilote, losa) con huella y canto."""
    layer = Layer.PHYSICAL
    id: str
    kind: str                   # FOOTING | PILE | MAT | PILE_CAP
    footprint_m: tuple[Point3, ...]
    depth_m: float
    material: str
    support_node_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_outline(self.id, self.footprint_m)
        if self.depth_m <= 0.0:
            raise ValueError(f"Foundation '{self.id}': depth_m debe ser > 0")


__all__ = ["Point3", "Material", "Section", "Story", "Grid", "Frame", "Wall", "Slab", "Opening", "Foundation"]
