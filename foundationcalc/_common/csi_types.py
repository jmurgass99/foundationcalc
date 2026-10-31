"""foundationcalc._common.csi_types
==============================
Contratos canónicos de conexión, información de modelo, fuerzas y máquina de estados
para la Capa Operacional CSI (ETABS, SAP2000, CSiBridge).

Tipado estricto con Pydantic v2, inmutabilidad (frozen) y desacoplamiento total
entre estado de modelo (condición física/operativa) y veredicto de cálculo
(CalculationStatus).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from .audit_status import CalculationStatus


class CSIProgramType(StrEnum):
    """Programas soportados en la familia CSI."""
    ETABS = "ETABS"
    SAP2000 = "SAP2000"
    CSIBRIDGE = "CSiBridge"
    SAFE = "SAFE"


# ---------------------------------------------------------------------------
# 1. Sesión vs Modelo
# ---------------------------------------------------------------------------

class CSIConnection(BaseModel):
    """Representa la conexión/sesión con el proceso CSI activo.

    Desacoplado de los datos del archivo o del modelo en sí.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    program_type: CSIProgramType = Field(
        ...,
        description="Programa CSI conectado (ETABS, SAP2000, CSiBridge, SAFE)",
    )
    program_version: str = Field(
        ...,
        min_length=1,
        description="Versión del programa reportada por la API (e.g. '21.2.0', '26.1.0')",
    )
    process_id: int | None = Field(
        default=None,
        description="PID del proceso del sistema operativo cuando esté disponible",
    )
    connected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp UTC en que se estableció la conexión",
    )
    connection_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único de la sesión de conexión",
    )


class CSIModelInfo(BaseModel):
    """Metadatos estáticos y propiedades globales del modelo abierto en CSI."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str = Field(
        ...,
        min_length=1,
        description="Identificador único del modelo (UUID, slug o hash)",
    )
    model_name: str = Field(
        ...,
        min_length=1,
        description="Nombre corto o título del modelo",
    )
    model_path: str | None = Field(
        default=None,
        description="Ruta absoluta al archivo .edb, .sdb, etc., cuando esté disponible",
    )
    current_units: str = Field(
        ...,
        description="Código de unidades actual de la sesión (e.g. 'kN_m_C', 'N_mm_C')",
    )
    force_unit: str = Field(
        ...,
        description="Unidad base de fuerza (e.g. 'kN', 'N', 'kip')",
    )
    length_unit: str = Field(
        ...,
        description="Unidad base de longitud (e.g. 'm', 'mm', 'ft')",
    )
    temperature_unit: str = Field(
        ...,
        description="Unidad base de temperatura (e.g. 'C', 'F')",
    )
    design_codes: dict[str, str] = Field(
        default_factory=dict,
        description="Códigos normativos configurados en el modelo (e.g. {'concrete': 'ACI 318-19', 'steel': 'AISC 360-16'})",
    )
    model_hash: str | None = Field(
        default=None,
        description="Hash criptográfico (SHA-256) o huella del modelo cuando esté calculada",
    )


# ---------------------------------------------------------------------------
# 2. CSI Frame Force (Granularidad real)
# ---------------------------------------------------------------------------

class CSIFrameForce(BaseModel):
    """Esfuerzo concurrente en barra (Frame) preservando la granularidad REAL de CSI.

    Conserva: element + load_combo + station + step + P + V2/V3 + T + M2/M3.
    No colapsa ni reordena resultados de modo que se pierda la concurrencia.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    element: str = Field(
        ...,
        description="Identificador del elemento barra o frame",
    )
    load_combo: str = Field(
        ...,
        description="Nombre del caso de carga o combinación de diseño",
    )
    station: float = Field(
        ...,
        description="Ubicación o distancia de la estación a lo largo de la barra",
    )
    step: str | int | float | None = Field(
        default=None,
        description="Paso / modo / tiempo para casos multi-paso (pushover, modal, time-history)",
    )
    P: float | None = Field(
        default=None,
        description="Axil (CSI convención: >0 tracción, <0 compresión)",
    )
    V2: float | None = Field(
        default=None,
        description="Cortante principal eje 2",
    )
    V3: float | None = Field(
        default=None,
        description="Cortante eje 3",
    )
    T: float | None = Field(
        default=None,
        description="Torsor",
    )
    M2: float | None = Field(
        default=None,
        description="Momento flector eje 2",
    )
    M3: float | None = Field(
        default=None,
        description="Momento flector principal eje 3",
    )
    step_type: str | None = Field(
        default=None,
        description="Tipo de paso reportado por CSI (e.g. 'Max', 'Min', 'Step')",
    )
    row_index: int | None = Field(
        default=None,
        description="Índice de fila de origen para trazabilidad absoluta de envolventes",
    )
    force_unit: str = Field(
        default="kN",
        description="Unidad de los esfuerzos axil y cortante (P, V2, V3)",
    )
    moment_unit: str = Field(
        default="kN*m",
        description="Unidad de los momentos y torsor (M2, M3, T)",
    )
    length_unit: str = Field(
        default="m",
        description="Unidad de la coordenada de estación",
    )

    def to_canonical_units(
        self,
        target_force_unit: str = "kN",
        target_moment_unit: str = "kN*m",
        target_length_unit: str = "m",
    ) -> "CSIFrameForce":
        """Convierte los esfuerzos y posición de la estación a unidades canónicas con guardia dimensional."""
        from .units import convert, assert_compatible_units

        assert_compatible_units(self.force_unit, target_force_unit, expected_dimension="force")
        assert_compatible_units(self.moment_unit, target_moment_unit, expected_dimension="moment")
        assert_compatible_units(self.length_unit, target_length_unit, expected_dimension="length")

        if (
            self.force_unit == target_force_unit
            and self.moment_unit == target_moment_unit
            and self.length_unit == target_length_unit
        ):
            return self

        def _conv_f(val: float | None) -> float | None:
            return convert(val, self.force_unit, target_force_unit) if val is not None else None

        def _conv_m(val: float | None) -> float | None:
            return convert(val, self.moment_unit, target_moment_unit) if val is not None else None

        def _conv_l(val: float) -> float:
            return convert(val, self.length_unit, target_length_unit)

        return self.model_copy(
            update={
                "P": _conv_f(self.P),
                "V2": _conv_f(self.V2),
                "V3": _conv_f(self.V3),
                "T": _conv_m(self.T),
                "M2": _conv_m(self.M2),
                "M3": _conv_m(self.M3),
                "station": _conv_l(self.station),
                "force_unit": target_force_unit,
                "moment_unit": target_moment_unit,
                "length_unit": target_length_unit,
            }
        )


class CSIFrameForceTable(BaseModel):
    """Colección inmutable de CSIFrameForce con unidades uniformes y guardia dimensional."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    forces: tuple[CSIFrameForce, ...]
    force_unit: str = Field(default="kN")
    moment_unit: str = Field(default="kN*m")
    length_unit: str = Field(default="m")

    def to_canonical(self) -> "CSIFrameForceTable":
        """Convierte todas las filas a unidades canónicas (kN, kN*m, m)."""
        canonical_forces = tuple(
            f.to_canonical_units(target_force_unit="kN", target_moment_unit="kN*m", target_length_unit="m")
            for f in self.forces
        )
        return self.model_copy(
            update={
                "forces": canonical_forces,
                "force_unit": "kN",
                "moment_unit": "kN*m",
                "length_unit": "m",
            }
        )



# ---------------------------------------------------------------------------
# 3. CSI Hinge Results (Rótulas plásticas no lineales)
# ---------------------------------------------------------------------------

class CSIHingeResult(BaseModel):
    """Resultado de rótula plástica preservando la granularidad y campos reales de CSI.

    Pydantic v2, inmutable (frozen), tipado estricto.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    story: str | None = Field(
        default=None,
        description="Piso o nivel del elemento (Story)",
    )
    frame_id: str = Field(
        ...,
        description="Identificador del elemento barra o frame (Frame/FrameWall)",
    )
    unique_name: str | None = Field(
        default=None,
        description="Nombre único del elemento en el modelo (UniqueName)",
    )
    load_case: str = Field(
        ...,
        description="Caso de carga o combinación de salida (OutputCase/LoadCase)",
    )
    case_type: str | None = Field(
        default=None,
        description="Tipo de caso de carga (CaseType)",
    )
    step_type: str | None = Field(
        default=None,
        description="Tipo de paso reportado por CSI (StepType, e.g. 'Max', 'Min', 'Step')",
    )
    step: str | int | float | None = Field(
        default=None,
        description="Número o identificador del paso (StepNumber/StepNum/Step)",
    )
    hinge_name: str = Field(
        ...,
        description="Nombre o identificador de la rótula (Hinge/HingeName)",
    )
    generated_hinge: str | None = Field(
        default=None,
        description="Nombre de la rótula generada automáticamente (GeneratedHinge)",
    )
    relative_distance: float | None = Field(
        default=None,
        description="Distancia relativa a lo largo de la barra [0..1] (RelDist/RelativeDistance)",
    )
    absolute_distance: float | None = Field(
        default=None,
        description="Distancia absoluta desde el nudo inicial (AbsDist/AbsoluteDistance)",
    )
    P: float | None = Field(
        default=None,
        description="Fuerza axial en la rótula",
    )
    V2: float | None = Field(
        default=None,
        description="Cortante eje 2 en la rótula",
    )
    V3: float | None = Field(
        default=None,
        description="Cortante eje 3 en la rótula",
    )
    T: float | None = Field(
        default=None,
        description="Momento torsor en la rótula",
    )
    M2: float | None = Field(
        default=None,
        description="Momento flector eje 2 en la rótula",
    )
    M3: float | None = Field(
        default=None,
        description="Momento flector eje 3 en la rótula",
    )
    plastic_deformation: float | None = Field(
        default=None,
        description="Deformación o rotación plástica (PlasticDef/PlasticRot/R3/U1)",
    )
    hinge_state: str | None = Field(
        default=None,
        description="Estado de la rótula según curva constitutiva (HingeState, e.g. 'A to B', 'B to IO', 'IO to LS', 'LS to CP', '> CP')",
    )
    hinge_status: str | None = Field(
        default=None,
        description="Condición de aceptabilidad o desempeño (HingeStatus, e.g. 'Acceptable', 'Immediate Occupancy', 'Life Safety')",
    )


# ---------------------------------------------------------------------------
# 4. CSI Design Results (Resultados normalizados de diseño)
# ---------------------------------------------------------------------------

class CSIDesignSummary(BaseModel):
    """Resultado de diseño estructural normalizado desde CSI (DCR y status).

    Pydantic v2, inmutable (frozen), tipado estricto.
    Preserva las columnas mínimas: frame_id, design_code, governing_combo,
    station, DCR, governing_equation, con mapeo honesto a CalculationStatus.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    frame_id: str = Field(
        ...,
        description="Identificador del elemento barra o frame (Frame/UniqueName)",
    )
    design_code: str = Field(
        ...,
        description="Norma o código de diseño aplicado (DesignCode)",
    )
    governing_combo: str | None = Field(
        default=None,
        description="Combinación de carga gobernante (GoverningCombo/Combo)",
    )
    station: float | None = Field(
        default=None,
        description="Ubicación crítica a lo largo de la barra (Station/Location)",
    )
    DCR: float | None = Field(
        default=None,
        description="Demand/Capacity Ratio gobernante (PMMRatio/TotalRatio/Ratio)",
    )
    governing_equation: str | None = Field(
        default=None,
        description="Ecuación o cláusula normativa crítica (Reason/Clause/Equation)",
    )
    calculation_status: CalculationStatus = Field(
        default=CalculationStatus.NO_CALCULADO,
        description="Estado canónico de cálculo derivado honestamente",
    )
    status_message: str | None = Field(
        default=None,
        description="Mensaje o advertencia de diseño de CSI (e.g. 'O/S', 'Overstressed')",
    )


# ---------------------------------------------------------------------------
# 7. Model State (Multidimensional, sin enums lineales mezclados)
# ---------------------------------------------------------------------------

class ConnectionState(StrEnum):
    """Estado del enlace de comunicación con el proceso CSI."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"


class ModelLoadedState(StrEnum):
    """Estado de carga del archivo del modelo."""
    NO_MODEL = "NO_MODEL"
    MODEL_LOADED = "MODEL_LOADED"


class LockState(StrEnum):
    """Estado de bloqueo / edición del modelo."""
    UNKNOWN = "UNKNOWN"
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"


class AnalysisState(StrEnum):
    """Estado de ejecución del análisis estructural."""
    NOT_ANALYZED = "NOT_ANALYZED"
    ANALYZED = "ANALYZED"


class ResultsState(StrEnum):
    """Condición de validez de la base de resultados."""
    UNKNOWN = "UNKNOWN"
    VALID = "VALID"
    INVALID = "INVALID"
    STALE = "STALE"


class CSIModelState(BaseModel):
    """Estado operativo multidimensional e inmutable de CSI.

    Responde estrictamente a: '¿En qué condición está el modelo/resultados?'.
    NUNCA se mezcla con CalculationStatus (que responde a veredictos de ingeniería).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    connection: ConnectionState = Field(
        default=ConnectionState.DISCONNECTED,
        description="Estado de la conexión",
    )
    model: ModelLoadedState = Field(
        default=ModelLoadedState.NO_MODEL,
        description="Estado de carga del modelo",
    )
    lock: LockState = Field(
        default=LockState.UNKNOWN,
        description="Estado de bloqueo",
    )
    analysis: AnalysisState = Field(
        default=AnalysisState.NOT_ANALYZED,
        description="Estado de análisis",
    )
    results: ResultsState = Field(
        default=ResultsState.UNKNOWN,
        description="Validez de resultados",
    )
    model_hash: str | None = Field(
        default=None,
        description="Hash de la geometría/cargas asociado a los resultados",
    )
    last_analysis_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp del último análisis exitoso",
    )
    invalidation_reason: str | None = Field(
        default=None,
        description="Motivo legible por el cual los resultados no son válidos",
    )
    model_info: CSIModelInfo | None = Field(
        default=None,
        description="Información contractual del modelo",
    )
    connection_info: CSIConnection | None = Field(
        default=None,
        description="Información de la conexión",
    )

    def is_valid_for_extraction(self) -> bool:
        """Determina si las compuertas físicas permiten extraer resultados vigentes."""
        return (
            self.connection == ConnectionState.CONNECTED
            and self.model == ModelLoadedState.MODEL_LOADED
            and self.lock == LockState.LOCKED
            and self.analysis == AnalysisState.ANALYZED
            and self.results == ResultsState.VALID
        )

    def on_unlock(self) -> CSIModelState:
        """Transición: el modelo se desbloquea en CSI. Los resultados quedan invalidados."""
        return self.model_copy(update={
            "lock": LockState.UNLOCKED,
            "results": ResultsState.INVALID,
            "invalidation_reason": "El modelo fue desbloqueado. Los resultados ya no son válidos.",
        })

    def on_hash_change(self, new_hash: str) -> CSIModelState:
        """Transición: el hash del modelo cambió con respecto al analizado."""
        if self.model_hash is not None and new_hash != self.model_hash:
            return self.model_copy(update={
                "results": ResultsState.STALE,
                "invalidation_reason": f"El hash del modelo cambió ({self.model_hash[:8]} -> {new_hash[:8]}). Resultados obsoletos.",
            })
        return self.model_copy(update={"model_hash": new_hash})

    def on_model_closed(self) -> CSIModelState:
        """Transición: el archivo de modelo se cierra."""
        return self.model_copy(update={
            "model": ModelLoadedState.NO_MODEL,
            "lock": LockState.UNKNOWN,
            "analysis": AnalysisState.NOT_ANALYZED,
            "results": ResultsState.INVALID,
            "invalidation_reason": "El modelo fue cerrado.",
            "model_info": None,
        })

    def on_disconnect(self) -> CSIModelState:
        """Transición: se pierde o cierra la conexión con CSI."""
        return self.model_copy(update={
            "connection": ConnectionState.DISCONNECTED,
            "results": ResultsState.INVALID,
            "invalidation_reason": "Se desconectó del programa CSI.",
        })

    def on_analysis_completed(
        self,
        model_hash: str,
        timestamp: datetime | None = None,
    ) -> CSIModelState:
        """Transición: el análisis finalizó exitosamente en un modelo bloqueado."""
        ts = timestamp or datetime.now(timezone.utc)
        return self.model_copy(update={
            "lock": LockState.LOCKED,
            "analysis": AnalysisState.ANALYZED,
            "results": ResultsState.VALID,
            "model_hash": model_hash,
            "last_analysis_timestamp": ts,
            "invalidation_reason": None,
        })


# ---------------------------------------------------------------------------
# 8 & 9. Regla de Invalidación y Assert Can Extract
# ---------------------------------------------------------------------------

class CSIResultsNotAvailableError(RuntimeError):
    """Lanzada cuando se intenta extraer resultados de un modelo no apto o desactualizado."""
    def __init__(self, reason: str, state: CSIModelState | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.state = state


def assert_can_extract_results(state: CSIModelState) -> None:
    """Bloquea la extracción cuando los resultados no sean válidos.

    Lanza CSIResultsNotAvailableError con motivo explícito.
    """
    if not state.is_valid_for_extraction():
        motivo = state.invalidation_reason or (
            f"Resultados no disponibles (connection={state.connection}, "
            f"model={state.model}, lock={state.lock}, analysis={state.analysis}, "
            f"results={state.results})"
        )
        raise CSIResultsNotAvailableError(
            f"Extracción bloqueada: {motivo}",
            state=state,
        )


def resolve_calculation_status_for_model_state(
    state: CSIModelState,
    nominal_verdict: CalculationStatus | None = None,
) -> CalculationStatus:
    """Aplica la regla de propagación normativo-operacional.

    Si los resultados no son válidos (INVALID o STALE), NINGÚN cálculo derivado
    puede emitir un veredicto favorable ni ficticio: propaga REQUIERE_REVISION.

    Que el modelo esté operacionalmente listo (conectado, bloqueado, analizado,
    con resultados VALID) NO es una comprobación normativa: es la condición
    para poder LEER resultados, no la prueba de que alguna ecuación de
    demanda/capacidad se evaluó. Sin ``nominal_verdict`` no hay veredicto que
    propagar -- es una entrada esencial ausente -- así que se declara
    NO_CALCULADO en vez de inventar un CALCULADO_CUMPLE.
    """
    if state.results in (ResultsState.INVALID, ResultsState.STALE, ResultsState.UNKNOWN):
        return CalculationStatus.REQUIERE_REVISION

    if not state.is_valid_for_extraction():
        return CalculationStatus.REQUIERE_REVISION

    if nominal_verdict is None:
        return CalculationStatus.NO_CALCULADO

    return nominal_verdict


__all__ = [
    "CSIProgramType",
    "CSIConnection",
    "CSIModelInfo",
    "CSIFrameForce",
    "CSIHingeResult",
    "CSIDesignSummary",
    "ConnectionState",
    "ModelLoadedState",
    "LockState",
    "AnalysisState",
    "ResultsState",
    "CSIModelState",
    "CSIResultsNotAvailableError",
    "assert_can_extract_results",
    "resolve_calculation_status_for_model_state",
]
