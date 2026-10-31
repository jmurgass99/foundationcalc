"""foundationcalc._common.identity [EXPERIMENTAL - D-CI-3] — identidad persistente e inmutable
de objetos estructurales para interoperabilidad (Sprint 1B, 2026-09-07).

Diseño aprobado en docs/interoperability/PHASE_0_5_ARCHITECTURAL_PRECONDITIONS.md §4.

REGLA DE ORO: ni ``name``, ni ``label``, ni el indice en una coleccion forman
parte de los hashes ni de la igualdad. Dos objetos con distinto nombre pero
identicos ``geometry_hash`` y ``properties_hash`` son la MISMA entidad fisica
con metadatos cambiados, no dos entidades (``ObjectIdentity.same_entity``).

Identificadores:
    source_system   sistema de origen (valores alineados con CSIProgramType).
    source_id       id NATIVO estable: GUID de CSI (GetGUID), UniqueId de Revit,
                    Identifier.GUID de Tekla, GlobalId de IFC, handle DXF; o
                    sintetizado (``IdStability.SYNTHESIZED``) si la fuente no lo da.
    canonical_id    UUID v5 determinista: uuid5(JM_IDENTITY_NAMESPACE,
                    f"{source_system}:{source_id}"). Se asigna una vez; el
                    validador rechaza un canonical_id incoherente con su par.
    source_hash     SHA-256 del payload nativo tal como lo entrego la fuente.
    geometry_hash   SHA-256 de coordenadas/conectividad/orientacion normalizadas
                    (redondeo a ``tol_decimals``; 4 = 0.1 mm en metros).
    properties_hash SHA-256 de seccion, material, offsets, releases y extras.

Hashing determinista: mismo patron que ``reconcile.ElementSpec.compute_hash``
(json canonico ``sort_keys`` + ``separators=(",", ":")``), extendido con la
normalizacion de flotantes (redondeo, -0.0 -> 0.0, enteros como flotantes) y la
exclusion recursiva de claves de nombre.

Puro Python + pydantic (ya dependencia del paquete). Sin logica de ningun
adaptador: aqui no se sabe que es un FrameObj, un FamilyInstance ni un Beam.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from enum import Enum
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .csi_types import CSIProgramType

__all__ = [
    "JM_IDENTITY_NAMESPACE",
    "SourceSystem",
    "MappingStatus",
    "IdStability",
    "ObjectIdentity",
    "compute_canonical_id",
    "compute_source_hash",
    "compute_geometry_hash",
    "compute_properties_hash",
    "canonical_json",
]

#: Namespace fijo de Structural JM para uuid5. NO cambiar: cambiarlo re-identifica
#: todos los objetos ya mapeados.
JM_IDENTITY_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://structuraljm.dev/identity/v1")

#: Claves que NUNCA participan en un hash de identidad (regla de oro).
_NAME_KEYS = frozenset({"name", "label", "index", "idx", "source_name", "display_name", "mark", "story_label"})

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class SourceSystem(str, Enum):
    """Sistema de origen. Los cuatro CSI usan el MISMO valor que CSIProgramType."""
    ETABS = "ETABS"
    SAP2000 = "SAP2000"
    SAFE = "SAFE"
    CSI_BRIDGE = "CSiBridge"
    REVIT = "Revit"
    TEKLA = "Tekla"
    IFC = "IFC"
    AUTOCAD = "AutoCAD"
    BRICSCAD = "BricsCAD"
    CANONICAL = "StructuralJM"

    @classmethod
    def from_csi(cls, program: CSIProgramType | str) -> "SourceSystem":
        """CSIProgramType -> SourceSystem sin string-sniffing: por valor."""
        value = program.value if isinstance(program, CSIProgramType) else str(program)
        return cls(value)


class MappingStatus(str, Enum):
    """Resultado del mapping entre dos snapshots. Se calcula; no es verdad persistida."""
    MATCHED = "MATCHED"
    NEW = "NEW"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    CONFLICTING = "CONFLICTING"
    UNMAPPED = "UNMAPPED"


class IdStability(str, Enum):
    """Cuanto se puede confiar en que ``source_id`` sobreviva."""
    STABLE = "STABLE"                        # GUID CSI/Tekla, UniqueId Revit, GlobalId IFC
    VOLATILE = "VOLATILE"                    # ElementId de Revit, handle DXF ajeno
    SESSION_DEPENDENT = "SESSION_DEPENDENT"  # Identifier.ID de Tekla, #id STEP
    SYNTHESIZED = "SYNTHESIZED"              # asignado por Structural JM a falta de nativo


# --------------------------------------------------------------------------- #
# Hashing determinista
# --------------------------------------------------------------------------- #
def _normalize(value: Any, tol_decimals: int) -> Any:
    """Forma canonica hashable: flotantes redondeados (sin -0.0, enteros como
    flotantes), claves de nombre excluidas, tuplas/conjuntos como listas."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        r = round(float(value), tol_decimals)
        return 0.0 if r == 0 else r
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _normalize(v, tol_decimals) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
                if str(k).lower() not in _NAME_KEYS}
    if isinstance(value, (set, frozenset)):
        return sorted(_normalize(v, tol_decimals) for v in value)  # type: ignore[type-var]
    if isinstance(value, (list, tuple)):
        return [_normalize(v, tol_decimals) for v in value]
    return value


def canonical_json(payload: Any, *, tol_decimals: int = 4) -> str:
    """JSON canonico (claves ordenadas, sin espacios, flotantes normalizados)."""
    return json.dumps(_normalize(payload, tol_decimals), sort_keys=True, separators=(",", ":"), default=str)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_canonical_id(
    source_system: SourceSystem,
    source_id: str,
    object_type: str = "",
) -> uuid.UUID:
    """UUID v5 determinista del par (sistema, id nativo) o (sistema, tipo, id nativo).
    Nunca usa el nombre.

    El `object_type` se normaliza a minusculas y sin espacios antes de entrar en la
    clave. MEDIDO el 2026-09-18: el contrato de Tekla produce identidades con
    ``object_type="frame"`` y los deltas de su ChangeSet los declaran como
    ``"Frame"``; con la clave sensible a mayusculas, el adaptador calculaba un
    identificador distinto del de la entidad que queria modificar y el delta **no
    se aplicaba, en silencio**. El tipo es un vocabulario canonico, no texto
    libre: una diferencia de mayusculas no puede partir una identidad.
    """
    sid = (source_id or "").strip()
    if not sid:
        raise ValueError("source_id vacio: sin id nativo no hay identidad; sintetiza uno (IdStability.SYNTHESIZED)")
    tipo = (object_type or "").strip().lower()
    sistema = SourceSystem(source_system).value
    key = f"{sistema}:{tipo}:{sid}" if tipo else f"{sistema}:{sid}"
    return uuid.uuid5(JM_IDENTITY_NAMESPACE, key)


def compute_source_hash(raw_payload: Any) -> str:
    """SHA-256 del payload nativo tal cual (solo canonicaliza orden de claves y
    flotantes a 10 decimales: aqui NO se excluyen nombres, es la huella de la fuente)."""
    blob = json.dumps(_normalize_keep_names(raw_payload), sort_keys=True, separators=(",", ":"), default=str)
    return _sha256(blob)


def _normalize_keep_names(value: Any, tol_decimals: int = 10) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        r = round(float(value), tol_decimals)
        return 0.0 if r == 0 else r
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _normalize_keep_names(v, tol_decimals) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_normalize_keep_names(v, tol_decimals) for v in value]
        return sorted(items, key=str) if isinstance(value, (set, frozenset)) else items
    return value


def compute_geometry_hash(coords_or_nodes: Any, tol_decimals: int = 4) -> str:
    """SHA-256 de la geometria normalizada.

    Acepta una secuencia de puntos ``[(x, y, z), ...]`` o un mapping con
    coordenadas, conectividad y orientacion (``{"nodes": [...], "rotation_deg":
    ..., "offsets": ...}``). Las claves de nombre se descartan recursivamente.
    El ORDEN de los puntos importa (define la conectividad i -> j). Una
    secuencia desnuda de puntos es la forma canonica de ``{"nodes": puntos}``."""
    payload = coords_or_nodes if isinstance(coords_or_nodes, Mapping) else {"nodes": coords_or_nodes}
    return _sha256(canonical_json({"geometry": payload}, tol_decimals=tol_decimals))


def compute_properties_hash(section: str | None, material: str | None, releases: Any = None, *,
                            offsets: Any = None, extra: Mapping[str, Any] | None = None,
                            tol_decimals: int = 4) -> str:
    """SHA-256 de las propiedades no geometricas (seccion, material, releases,
    offsets y extras). Independiente del orden; las claves de nombre en ``extra``
    se descartan."""
    payload = {
        "section": (section or "").strip(),
        "material": (material or "").strip(),
        "releases": list(releases) if isinstance(releases, Iterable) and not isinstance(releases, (str, bytes)) else releases,
        "offsets": offsets,
        "extra": dict(extra) if extra else {},
    }
    return _sha256(canonical_json(payload, tol_decimals=tol_decimals))


# --------------------------------------------------------------------------- #
# Contrato
# --------------------------------------------------------------------------- #
class ObjectIdentity(BaseModel):
    """Identidad persistente e inmutable de un objeto estructural.

    Construir con ``ObjectIdentity.create(...)`` (calcula ``canonical_id``) o con
    el constructor pasando un ``canonical_id`` coherente: el validador rechaza
    cualquier otro. ``__eq__`` compara todos los campos del contrato; ninguno es
    un nombre. Para "misma entidad fisica" usar ``same_entity``.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_system: SourceSystem
    source_id: str = Field(min_length=1, description="id nativo estable o sintetizado; nunca el nombre")
    source_id_stability: IdStability
    canonical_id: uuid.UUID
    object_type: str = Field(min_length=1, description="tipo canonico: frame, column, beam, wall, slab, ...")
    source_hash: str
    geometry_hash: str
    properties_hash: str
    mapping_status: MappingStatus = MappingStatus.UNMAPPED

    @field_validator("source_id", "object_type")
    @classmethod
    def _strip_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("no puede estar en blanco")
        return v

    @field_validator("source_hash", "geometry_hash", "properties_hash")
    @classmethod
    def _sha256_hex(cls, v: str) -> str:
        if not _SHA256_HEX.match(v):
            raise ValueError("debe ser SHA-256 en hexadecimal minusculas (64 caracteres)")
        return v

    @model_validator(mode="after")
    def _coherencia(self) -> "ObjectIdentity":
        # El `object_type` ENTRA en la identidad. MEDIDO el 2026-09-18: este
        # validador y `create` llamaban a `compute_canonical_id` SIN el tipo,
        # aunque el campo es obligatorio aqui y la funcion sabe usarlo. Con
        # SAP2000 y el id nativo "1", la barra y el nudo salian con el MISMO
        # canonical_id (4330d61a-...), y en el OAPI de CSI puntos y barras tienen
        # espacios de nombres independientes numerados desde 1, asi que conviven
        # en cualquier modelo. Un mapeo entre sistemas podia casar una barra con
        # un nudo, que es justo lo que este modulo existe para impedir.
        esperado = compute_canonical_id(self.source_system, self.source_id, self.object_type)
        if self.canonical_id != esperado:
            raise ValueError(
                f"canonical_id {self.canonical_id} no corresponde a "
                f"({self.source_system.value}, {self.object_type}, "
                f"{self.source_id}); esperado {esperado}")
        if self.source_id_stability is IdStability.SYNTHESIZED and self.mapping_status is MappingStatus.MATCHED:
            raise ValueError("un id SYNTHESIZED no puede estar MATCHED sin confirmacion: usa UNMAPPED o CONFLICTING")
        return self

    @classmethod
    def create(cls, *, source_system: SourceSystem, source_id: str, source_id_stability: IdStability,
               object_type: str, source_hash: str, geometry_hash: str, properties_hash: str,
               mapping_status: MappingStatus = MappingStatus.UNMAPPED) -> "ObjectIdentity":
        """Construye calculando ``canonical_id`` de forma determinista."""
        return cls(source_system=source_system, source_id=source_id, source_id_stability=source_id_stability,
                   canonical_id=compute_canonical_id(source_system, source_id, object_type),
                   object_type=object_type,
                   source_hash=source_hash, geometry_hash=geometry_hash, properties_hash=properties_hash,
                   mapping_status=mapping_status)

    def same_entity(self, other: "ObjectIdentity") -> bool:
        """Misma entidad fisica: geometria y propiedades identicas, aunque cambien
        nombre, sistema o id nativo."""
        return (self.object_type == other.object_type and self.geometry_hash == other.geometry_hash
                and self.properties_hash == other.properties_hash)

    def with_mapping_status(self, status: MappingStatus) -> "ObjectIdentity":
        """Copia inmutable con otro ``mapping_status`` (la validacion se re-ejecuta)."""
        return self.model_validate({**self.model_dump(mode="json"), "mapping_status": status.value})
