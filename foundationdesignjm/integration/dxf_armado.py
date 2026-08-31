"""Bridge FoundationDesignJm -> DXFStructuralJm / ezdxf para exportar armado de zapatas.

Genera planos en formato DXF con capas estandarizadas:
- PLANTA: Contorno exterior de la zapata.
- COLUMNA: Sección del arranque de columna centrado.
- REBAR_X: Armadura inferior en dirección X (malla).
- REBAR_Y: Armadura inferior en dirección Y (malla).
- COTAS: Líneas y textos de acotado.
- TEXTOS: Rótulos identificadores y especificación de armado.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import warnings
from typing import Optional


@dataclass(frozen=True)
class ArmadoZapataDXF:
    """Datos geométricos y de armado para generación de plano DXF."""

    B_m: float
    L_m: float
    H_m: float
    n_x: int
    n_y: int
    db_x_mm: float
    db_y_mm: float
    s_x_mm: float = 150.0
    s_y_mm: float = 150.0
    column_cx_m: float = 0.40
    column_cy_m: float = 0.40
    cover_mm: float = 50.0
    footing_name: str = "ZAPATA"


def export_armado_zapata(arm: ArmadoZapataDXF, path: str | Path) -> bool:
    """Exporta el plano de despiece y armado de la zapata a un archivo DXF estándar.

    Utiliza `ezdxf` (con fallback a `dxfstructuraljm.DXFDocument`).
    """
    path_obj = Path(path)
    try:
        import ezdxf
    except ImportError:
        try:
            from dxfstructuraljm import DXFDocument  # noqa: F401
            import ezdxf
        except ImportError:
            warnings.warn("ezdxf / DXFStructuralJm no instalado - escritura DXF omitida", RuntimeWarning)
            return False

    try:
        doc = ezdxf.new("R2010", setup=True)
        msp = doc.modelspace()

        # Definir capas con colores ACI/CAD
        # 1: Red, 2: Yellow, 3: Green, 4: Cyan, 5: Blue, 7: White
        layers = {
            "PLANTA": 7,
            "COLUMNA": 4,
            "REBAR_X": 1,
            "REBAR_Y": 5,
            "COTAS": 2,
            "TEXTOS": 3,
        }
        for lname, color in layers.items():
            if lname not in doc.layers:
                doc.layers.add(lname, color=color)

        B_mm = arm.B_m * 1000.0
        L_mm = arm.L_m * 1000.0
        H_mm = arm.H_m * 1000.0
        c_mm = arm.cover_mm

        # 1. Contorno de la zapata (Capa PLANTA)
        # Centrado en (0,0)
        x_min, x_max = -L_mm / 2.0, L_mm / 2.0
        y_min, y_max = -B_mm / 2.0, B_mm / 2.0

        footing_pts = [
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max),
            (x_min, y_min),
        ]
        msp.add_lwpolyline(footing_pts, close=True, dxfattribs={"layer": "PLANTA"})

        # 2. Arranque de columna (Capa COLUMNA)
        col_x = (arm.column_cx_m * 1000.0) / 2.0
        col_y = (arm.column_cy_m * 1000.0) / 2.0
        col_pts = [
            (-col_x, -col_y),
            (col_x, -col_y),
            (col_x, col_y),
            (-col_x, col_y),
            (-col_x, -col_y),
        ]
        msp.add_lwpolyline(col_pts, close=True, dxfattribs={"layer": "COLUMNA"})

        # 3. Armadura en X (barras longitudinales paralelas a L, repartidas en B)
        # Recorrido de y desde (y_min + c) hasta (y_max - c)
        if arm.n_x > 1:
            dy_rebar = (B_mm - 2.0 * c_mm) / (arm.n_x - 1)
            for i in range(arm.n_x):
                y_bar = y_min + c_mm + i * dy_rebar
                msp.add_line(
                    (x_min + c_mm, y_bar),
                    (x_max - c_mm, y_bar),
                    dxfattribs={"layer": "REBAR_X"},
                )
        elif arm.n_x == 1:
            msp.add_line((x_min + c_mm, 0.0), (x_max - c_mm, 0.0), dxfattribs={"layer": "REBAR_X"})

        # 4. Armadura en Y (barras transversales paralelas a B, repartidas en L)
        # Recorrido de x desde (x_min + c) hasta (x_max - c)
        if arm.n_y > 1:
            dx_rebar = (L_mm - 2.0 * c_mm) / (arm.n_y - 1)
            for j in range(arm.n_y):
                x_bar = x_min + c_mm + j * dx_rebar
                msp.add_line(
                    (x_bar, y_min + c_mm),
                    (x_bar, y_max - c_mm),
                    dxfattribs={"layer": "REBAR_Y"},
                )
        elif arm.n_y == 1:
            msp.add_line((0.0, y_min + c_mm), (0.0, y_max - c_mm), dxfattribs={"layer": "REBAR_Y"})

        # 5. Rótulo descriptivo (Capa TEXTOS)
        info_title = f"{arm.footing_name} - {arm.B_m:.2f}x{arm.L_m:.2f}x{arm.H_m:.2f}m"
        info_rebar = f"Armado: {arm.n_x}Ø{int(arm.db_x_mm)} (X) + {arm.n_y}Ø{int(arm.db_y_mm)} (Y)"

        msp.add_text(
            info_title,
            dxfattribs={"layer": "TEXTOS", "height": 60.0},
        ).set_placement((x_min, y_max + 120.0))

        msp.add_text(
            info_rebar,
            dxfattribs={"layer": "TEXTOS", "height": 45.0},
        ).set_placement((x_min, y_max + 50.0))

        # 6. Guardar archivo
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(str(path_obj))
        return True
    except Exception as e:
        warnings.warn(f"Error exportando DXF de zapata: {e}", RuntimeWarning)
        return False


__all__ = ["ArmadoZapataDXF", "export_armado_zapata"]
