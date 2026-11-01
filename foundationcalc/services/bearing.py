"""Servicios de capacidad portante.

Incluye:
- ``bearing_capacity_meyerhof_hanna(inp)``: capacidad portante multicapa real
  (Meyerhof & Hanna 1978, punzonamiento de estrato fuerte sobre blando) delegando
  en ``foundationcalc.analysis.multi_layer_bc.multi_layer_bearing_capacity``.
- ``bearing_capacity_canonical(inp)``: delegación en ``foundationcalc.analysis.bearing_capacity``
  (EN 1997-1:2004 Anexo D).
- ``bearing_capacity_multilayer(inp)``: servicio histórico (si ``inp.method == "meyerhof_hanna"``
  delega en ``bearing_capacity_meyerhof_hanna``; en caso contrario mantiene la
  formulación de estrato único por compatibilidad).
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
    method: str = "vesic"   # "vesic" | "meyerhof" | "hansen" | "meyerhof_hanna"
    seismic_kh: float = 0.0  # coeficiente sísmico horizontal


@dataclass(frozen=True)
class BearingResult:
    qu_kPa: float           # capacidad última
    qa_kPa: float           # capacidad admisible (FS aplicado)
    FS: float
    method: str
    notes: list[str]


def bearing_capacity_meyerhof_hanna(inp: BearingInput) -> BearingResult:
    """Capacidad portante multicapa real según Meyerhof & Hanna (1978).

    Construye un ``SoilProfile`` completo con todas las capas de ``inp.layers``
    y el nivel freático ``inp.water_table``, y evalúa ``multi_layer_bearing_capacity``
    (incluyendo punzonamiento de capa competente sobre estrato débil dentro de
    la profundidad de influencia ``2·B``).
    """
    from foundationcalc.analysis.multi_layer_bc import multi_layer_bearing_capacity
    from foundationcalc.core.geometry import RectangularFoundation
    from foundationcalc.core.soil import SoilLayer, SoilProfile, SoilType

    B = min(inp.L_x, inp.L_y)
    L = max(inp.L_x, inp.L_y)
    foundation = RectangularFoundation(
        length=L * 1000.0,
        width=B * 1000.0,
        thickness=300.0,
        embedment_depth=inp.depth * 1000.0,
    )
    profile_layers: list[SoilLayer] = []
    for idx, lyr in enumerate(inp.layers):
        is_cohesive = lyr.phi <= 1e-6 and (lyr.c > 0.0 or lyr.qu > 0.0)
        cu_val = (0.5 * lyr.qu) if lyr.qu > 0.0 else (lyr.c if is_cohesive else None)
        profile_layers.append(
            SoilLayer(
                name=f"Layer_{idx + 1}",
                thickness=lyr.thickness,
                soil_type=SoilType.COHESIVE if is_cohesive else SoilType.COHESIONLESS,
                unit_weight=lyr.gamma,
                saturated_unit_weight=max(lyr.gamma, 18.0),
                friction_angle=lyr.phi,
                cohesion=lyr.c,
                undrained_shear_strength=cu_val,
            )
        )
    profile = SoilProfile(layers=profile_layers, water_table_depth=inp.water_table)
    res = multi_layer_bearing_capacity(
        foundation=foundation,
        profile=profile,
        founding_depth_m=inp.depth,
    )
    qu = res.q_ult_kPa
    if inp.seismic_kh > 0:
        qu *= (1.0 - inp.seismic_kh / 0.5) if inp.seismic_kh < 0.5 else 0.5
    FS = 3.0 if inp.seismic_kh == 0 else 2.5
    qa = qu / FS
    notes = [
        f"Caso gobernante: {res.governing_case} (estrato: {res.governing_layer})",
        f"Estratos en zona de influencia (2B): {', '.join(res.layers_in_influence)}",
        f"B/L = {B / L:.2f}, FS = {FS}, qa = {qa:.1f} kPa",
    ]
    if res.punching_q_ult is not None:
        notes.append(
            f"Punzonamiento Meyerhof-Hanna: q_punch = {res.punching_q_ult:.1f} kPa "
            f"(estrato superior = {res.bottom_strong_q_ult:.1f} kPa, inferior = {res.weak_layer_q_ult:.1f} kPa)"
        )
    return BearingResult(
        qu_kPa=qu,
        qa_kPa=qa,
        FS=FS,
        method="meyerhof_hanna",
        notes=notes,
    )


def bearing_capacity_multilayer(inp: BearingInput) -> BearingResult:
    """Capacidad portante considerando estratificación.

    Si ``inp.method == "meyerhof_hanna"``, delega en ``bearing_capacity_meyerhof_hanna``
    (modelo multicapa de Meyerhof & Hanna 1978). Para otros valores de ``method``,
    mantiene la formulación histórica deprecada.
    """
    if inp.method == "meyerhof_hanna":
        return bearing_capacity_meyerhof_hanna(inp)

    warnings.warn(
        "foundationcalc.services.bearing.bearing_capacity_multilayer está deprecada "
        "como calculadora analítica. La implementación canónica de capacidad portante en "
        "este paquete es foundationcalc.analysis.bearing_capacity (EN 1997-1:2004 Anexo D).",
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
    """Delega en la implementación canónica foundationcalc.analysis.bearing_capacity."""
    from foundationcalc.analysis.bearing_capacity import (
        drained_bearing_capacity, BearingCapacityFormula,
    )
    from foundationcalc.core.geometry import RectangularFoundation
    from foundationcalc.core.soil import SoilLayer

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
    "bearing_capacity_meyerhof_hanna",
]
