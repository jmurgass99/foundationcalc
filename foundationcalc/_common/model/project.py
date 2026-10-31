"""Metadatos de proyecto y relaciones entre capas (META)."""
from __future__ import annotations

from dataclasses import dataclass

from .provenance import Layer, Provenance, Traceable


@dataclass(frozen=True)
class Project(Traceable):
    """Contenedor: nombre, normativa, ingeniero y fuentes de las que se leyo el modelo."""
    layer = Layer.META
    name: str = ""
    code: str = ""                                  # norma principal (NSR-10, EC, ASCE 7, ...)
    engineer: str = ""
    notes: str = ""
    design_codes: tuple[tuple[str, str], ...] = ()  # (("concrete", "ACI 318-19"), ...)
    sources: tuple[Provenance, ...] = ()            # cada sistema del que se leyo algo


@dataclass(frozen=True)
class AnalyticalRelationship:
    """Enlace explicito fisico <-> analitico. Un fisico puede tener 0..n
    analiticos (columna mallada en 3 barras: `order` 0,1,2 con kind MESHED_PART);
    un analitico 0..1 fisico."""
    physical_id: str
    analytical_id: str
    kind: str = "PRIMARY"       # PRIMARY | MESHED_PART
    order: int = 0


__all__ = ["Project", "AnalyticalRelationship"]
