"""Bridge FoundationDesignJm -> DXFStructuralJm para exportar armado de zapatas/pilotes."""
from __future__ import annotations

import warnings
from dataclasses import dataclass


@dataclass(frozen=True)
class ArmadoZapataDXF:
    B_m: float
    L_m: float
    H_m: float
    n_x: int
    n_y: int
    db_x_mm: float
    db_y_mm: float


def export_armado_zapata(arm: ArmadoZapataDXF, path: str) -> bool:
    """Exporta DXF del armado usando DXFStructuralJm si esta disponible."""
    try:
        from dxfstructuraljm import write_dxf
    except ImportError:
        warnings.warn("DXFStructuralJm no instalado - escritura DXF omitida", RuntimeWarning)
        return False
    entities = [
        {"type": "RECT", "x": 0, "y": 0, "w": arm.B_m, "h": arm.L_m, "layer": "PLANTA"},
    ]
    for i in range(arm.n_x):
        x = (i + 0.5) * arm.B_m / arm.n_x
        entities.append({"type": "LINE", "x1": x, "y1": 0, "x2": x, "y2": arm.L_m, "layer": "REBAR_X"})
    for j in range(arm.n_y):
        y = (j + 0.5) * arm.L_m / arm.n_y
        entities.append({"type": "LINE", "x1": 0, "y1": y, "x2": arm.B_m, "y2": y, "layer": "REBAR_Y"})
    try:
        write_dxf(entities, path)
    except Exception as e:  # pragma: no cover
        warnings.warn(f"write_dxf fallo: {e}")
        return False
    return True


__all__ = ["ArmadoZapataDXF", "export_armado_zapata"]
