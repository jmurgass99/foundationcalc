"""Servicios de capacidad portante.

ESTADO: MÓDULO DE SERVICIO HISTÓRICO / DEPRECADO.
La implementación CANÓNICA de capacidad portante de este paquete y del monorepo
es ``foundationdesignjm.analysis.bearing_capacity`` (EN 1997-1:2004 Anexo D).
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SoilLayerSpec:
    thickness: float    # m
    gamma: float        # kN/m³
    phi: float = 0.0    # grados
    c: float = 0.0      # kPa
    qu: float = 0.0     # kPa, sólo cohesivos


@dataclass(frozen=True)
class BearingInput:
    L_x: float
    L_y: float
    depth: float
    layers: tuple[SoilLayerSpec, ...]
    water_table: float | None = None
    method: str = "vesic"   # "vesic" | "meyerhof" | "hansen"
    seismic_kh: float = 0.0  # coeficiente sísmico horizontal


@dataclass(frozen=True)
class BearingResult:
    qu_kPa: float           # capacidad última
    qa_kPa: float           # capacidad admisible (FS aplicado)
    FS: float
    method: str
    notes: list[str]


def bearing_capacity_multilayer(inp: BearingInput) -> BearingResult:
    """Capacidad portante considerando estratificación.

    DEPRECADO: Usa foundationdesignjm.analysis.bearing_capacity para el análisis
    riguroso según EN 1997-1 Anexo D.
    """
    warnings.warn(
        "foundationdesignjm.services.bearing.bearing_capacity_multilayer está deprecada "
        "como calculadora analítica. La implementación canónica de capacidad portante en "
        "este paquete es foundationdesignjm.analysis.bearing_capacity (EN 1997-1:2004 Anexo D).",
        DeprecationWarning,
        stacklevel=2,
    )
    # Encuentra la capa de fundación
    depth_acc = 0.0
    found_layer = inp.layers[0]
    for layer in inp.layers:
        if depth_acc <= inp.depth < depth_acc + layer.thickness:
            found_layer = layer
            break
        depth_acc += layer.thickness

    phi_rad = math.radians(found_layer.phi)
    # Factores de capacidad (Vesic)
    if phi_rad > 0:
        Nq = math.exp(math.pi * math.tan(phi_rad)) * \
             math.tan(math.radians(45 + found_layer.phi / 2)) ** 2
        Nc = (Nq - 1) / math.tan(phi_rad)
        Ngamma = 2 * (Nq + 1) * math.tan(phi_rad)
    else:
        Nq = 1.0
        Nc = 5.14
        Ngamma = 0.0

    # Factores de forma (Vesic)
    B = min(inp.L_x, inp.L_y)
    L = max(inp.L_x, inp.L_y)
    Sc = 1 + (B / L) * (Nq / Nc) if Nc > 0 else 1.0
    Sq = 1 + (B / L) * math.tan(phi_rad)
    Sgamma = 1 - 0.4 * (B / L)
    # Sobrecarga efectiva
    q_overburden = found_layer.gamma * inp.depth
    # Capacidad última
    qu = (found_layer.c * Nc * Sc
          + q_overburden * Nq * Sq
          + 0.5 * found_layer.gamma * B * Ngamma * Sgamma)
    # Reducción sísmica simplificada
    if inp.seismic_kh > 0:
        qu *= (1 - inp.seismic_kh / 0.5) if inp.seismic_kh < 0.5 else 0.5
    FS = 3.0 if inp.seismic_kh == 0 else 2.5
    qa = qu / FS

    notes = [
        f"Capa fundación: φ={found_layer.phi:.0f}°, c={found_layer.c:.1f} kPa, "
        f"γ={found_layer.gamma:.1f} kN/m³",
        f"B/L = {B/L:.2f}",
        f"FS = {FS}, qa = {qa:.1f} kPa",
    ]
    if inp.water_table is not None:
        warnings.warn(
            f"bearing_capacity_multilayer: water_table={inp.water_table:g}m declarado pero "
            "no considerado en el cálculo analítico de estrato único.",
            UserWarning,
            stacklevel=2,
        )
        notes.append(
            f"ADVERTENCIA: water_table={inp.water_table:g}m declarado pero ignorado por esta formulación simplificada."
        )

    return BearingResult(
        qu_kPa=qu, qa_kPa=qa, FS=FS, method=inp.method,
        notes=notes,
    )


def bearing_capacity_canonical(inp: BearingInput) -> BearingResult:
    """Delega en la implementación canónica foundationdesignjm.analysis.bearing_capacity."""
    from foundationdesignjm.analysis.bearing_capacity import (
        drained_bearing_capacity, BearingCapacityFormula,
    )
    from foundationdesignjm.core.geometry import RectangularFoundation
    from foundationdesignjm.core.soil import SoilLayer

    depth_acc = 0.0
    found_layer = inp.layers[0]
    for layer in inp.layers:
        if depth_acc <= inp.depth < depth_acc + layer.thickness:
            found_layer = layer
            break
        depth_acc += layer.thickness

    B = min(inp.L_x, inp.L_y)
    L = max(inp.L_x, inp.L_y)
    res = drained_bearing_capacity(
        foundation=RectangularFoundation(
            length=L * 1000.0,
            width=B * 1000.0,
            thickness=300.0,
            embedment_depth=inp.depth * 1000.0,
        ),
        soil=SoilLayer(
            thickness=10.0,
            friction_angle=found_layer.phi,
            cohesion=found_layer.c,
            unit_weight=found_layer.gamma,
        ),
        formula=BearingCapacityFormula.CHEN_EC7,
    )
    FS = 3.0
    qu = res.q_ult
    qa = qu / FS
    notes = [
        f"Canónica EN 1997-1 Anexo D (Chen): φ={found_layer.phi:.0f}°, c={found_layer.c:.1f} kPa, "
        f"γ={found_layer.gamma:.1f} kN/m³",
        f"B/L = {B/L:.2f}",
        f"FS = {FS}, qa = {qa:.1f} kPa",
    ]
    if inp.water_table is not None:
        notes.append(
            f"ADVERTENCIA: water_table={inp.water_table:g}m recibido (la canónica analítica actual "
            "no dispone de reducción por peso sumergido)."
        )
    return BearingResult(
        qu_kPa=qu, qa_kPa=qa, FS=FS, method="EN 1997-1 (Chen / Canónica)",
        notes=notes,
    )


__all__ = [
    "SoilLayerSpec",
    "BearingInput",
    "BearingResult",
    "bearing_capacity_multilayer",
    "bearing_capacity_canonical",
]

