"""MemoriaBuilder -- API fluida para componer memorias de calculo.

Encapsula `fastsap.reports.MemoriaData` con una interfaz declarativa
estilo builder. Reduce de ~40 lineas a ~10 la construccion de una
memoria completa.

Ejemplo:
    (MemoriaBuilder("Edif. Central", "Bogota", "Ing. JM")
        .with_codes("NSR-10", "ACI 318-19")
        .with_materials(fc=28, fy=420)
        .with_seismic(code="NSR-10", Aa=0.15, Av=0.20, R=7.0)
        .with_modal(modal_df)
        .with_drifts(drift_df, limit=0.01)
        .with_conclusions("El diseno cumple.")
        .save("memoria.pdf"))
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from .reports import (
    MaterialsSpec,
    MemoriaData,
    NarrativeCheck,
    ProjectInfo,
    SeismicParams,
    StepBlock,
    build_master_memoria,
)


@dataclass
class MemoriaBuilder:
    """Construye `MemoriaData` paso a paso con method chaining."""

    name: str
    location: str = ""
    engineer: str = ""

    def __post_init__(self):
        self._data = MemoriaData(
            project=ProjectInfo(name=self.name,
                                 location=self.location,
                                 engineer=self.engineer),
        )

    # --- Project ---
    def with_project(self, **kwargs) -> "MemoriaBuilder":
        for k, v in kwargs.items():
            setattr(self._data.project, k, v)
        return self

    # --- Codes ---
    def with_codes(self, *codes: str) -> "MemoriaBuilder":
        self._data.codes.extend(codes)
        return self

    # --- Materials ---
    def with_materials(self, **kwargs) -> "MemoriaBuilder":
        for k, v in kwargs.items():
            setattr(self._data.materials, k, v)
        return self

    # --- Loads ---
    def with_loads(self, df: pd.DataFrame) -> "MemoriaBuilder":
        self._data.loads_df = df
        return self

    def with_combos(self, df: pd.DataFrame) -> "MemoriaBuilder":
        self._data.combos_df = df
        return self

    # --- Seismic ---
    def with_seismic(self, **kwargs) -> "MemoriaBuilder":
        for k, v in kwargs.items():
            setattr(self._data.seismic, k, v)
        return self

    def with_model_description(self, text: str) -> "MemoriaBuilder":
        self._data.model_description = text
        return self

    # --- Modal ---
    def with_modal(self, df: pd.DataFrame) -> "MemoriaBuilder":
        self._data.modal_df = df
        return self

    # --- Drifts ---
    def with_drifts(self, df: pd.DataFrame,
                     *, limit: float = 0.01) -> "MemoriaBuilder":
        self._data.drifts_df = df
        self._data.drift_limit = limit
        return self

    # --- Irregularities ---
    def with_irregularities(self, df: pd.DataFrame) -> "MemoriaBuilder":
        self._data.irregularities_df = df
        return self

    # --- Element design ---
    def with_rc_design(self, df: pd.DataFrame) -> "MemoriaBuilder":
        self._data.rc_design_df = df
        return self

    def with_steel_design(self, df: pd.DataFrame) -> "MemoriaBuilder":
        self._data.steel_design_df = df
        return self

    def with_connection_check(self, check: NarrativeCheck) -> "MemoriaBuilder":
        self._data.connection_checks.append(check)
        return self

    def with_anchor_check(self, check: NarrativeCheck) -> "MemoriaBuilder":
        self._data.anchor_checks.append(check)
        return self

    def with_foundation_check(self, check: NarrativeCheck) -> "MemoriaBuilder":
        self._data.foundation_checks.append(check)
        return self

    def with_serviceability(self, notes: str) -> "MemoriaBuilder":
        self._data.serviceability_notes = notes
        return self

    def with_conclusions(self, text: str) -> "MemoriaBuilder":
        self._data.conclusions = text
        return self

    # --- Step-by-step calculation blocks ---
    def with_step_block(self, block: StepBlock) -> "MemoriaBuilder":
        self._data.step_blocks.append(block)
        return self

    def with_step_blocks(self, blocks: List[StepBlock]) -> "MemoriaBuilder":
        self._data.step_blocks.extend(blocks)
        return self

    # --- Build ---
    def build(self) -> MemoriaData:
        return self._data

    def save(self, path: str) -> str:
        return build_master_memoria(self._data, path)


__all__ = ["MemoriaBuilder"]
