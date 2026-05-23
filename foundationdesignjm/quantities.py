"""Cuantia de acero y cubicaje de hormigon para cimentaciones."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuantitiesInput:
    B_m: float
    L_m: float
    H_m: float
    rebar_kg_per_m3: float = 80.0     # tipico zapata
    concrete_unit_m3: float = 1.0
    code: str = "EU"


@dataclass(frozen=True)
class QuantitiesResult:
    volumen_hormigon_m3: float
    masa_acero_kg: float
    cuantia_kg_m3: float
    code: str


def quantities(inp: QuantitiesInput) -> QuantitiesResult:
    if inp.code not in {"EU", "AU", "SG", "US", "CO"}:
        raise ValueError(f"code invalido: {inp.code}")
    V = inp.B_m * inp.L_m * inp.H_m * inp.concrete_unit_m3
    masa = V * inp.rebar_kg_per_m3
    return QuantitiesResult(V, masa, inp.rebar_kg_per_m3, inp.code)


__all__ = ["QuantitiesInput", "QuantitiesResult", "quantities"]
