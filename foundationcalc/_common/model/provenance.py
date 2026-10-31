"""Procedencia e identidad de las entidades del modelo canonico (Sprint 1C).

- `Layer`: capa a la que pertenece cada entidad (PHYSICAL / ANALYTICAL / META).
  Se declara como atributo de clase; ninguna entidad mezcla campos de dos capas.
- `Provenance`: de donde vino el objeto y QUE campos entrego realmente la fuente
  (`known`, herencia de los flags `*_known` de EtabsToRevitJm). Un campo ausente
  no se rellena con un valor plausible: se declara no conocido.
- `Traceable`: base de toda entidad interoperable. Aporta `identity`
  (`ObjectIdentity`, contrato de Sprint 1B, NO duplicado) y `provenance`, ambos
  opcionales y kw-only para no romper los constructores posicionales existentes.

El core no sabe que es un FrameObj, un FamilyInstance ni un ModelObject:
`Provenance.source_system` es una cadena con el valor de `SourceSystem`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..identity import ObjectIdentity, SourceSystem


class Layer(str, Enum):
    PHYSICAL = "PHYSICAL"      # lo que se construye: dimensiones, posicion, caras
    ANALYTICAL = "ANALYTICAL"  # lo que se calcula: ejes, nudos, apoyos, releases
    META = "META"              # proyecto, relaciones, enlaces


@dataclass(frozen=True)
class Provenance:
    """Origen del objeto y campos que la fuente entrego de verdad."""
    source_system: str                       # valor de SourceSystem (p. ej. "ETABS", "Revit")
    source_version: str = ""
    read_at: str = ""                        # ISO 8601 UTC
    known: tuple[str, ...] = ()              # nombres de campos entregados por la fuente

    def __post_init__(self) -> None:
        SourceSystem(self.source_system)     # valida sin importar nada del adaptador

    def knows(self, field_name: str) -> bool:
        return field_name in self.known


@dataclass(frozen=True)
class Traceable:
    """Base: identidad persistente (opcional) y procedencia (opcional), kw-only."""
    layer = Layer.META
    identity: ObjectIdentity | None = field(default=None, kw_only=True)
    provenance: Provenance | None = field(default=None, kw_only=True)


__all__ = ["Layer", "Provenance", "Traceable"]
