"""Minimal DXF export for footings and rebar layouts.

Writes a small subset of DXF R12 by hand — no external dependency.
AutoCAD / BricsCAD / LibreCAD open these files natively.

Supports:
- Rectangular footing outline
- Column outline
- Rebar lines (longitudinal + transverse mats)
- Title text and dimensions

Coordinate system: footing centred on origin, x = long side, y = short.
All units in mm (DXF $INSUNITS = 4 → millimetres).
"""

from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

from .._brand import NAME as _BRAND_NAME


def _w(fh, code: int, value) -> None:
    fh.write(f"{code:>3}\n{value}\n")


def _start_dxf(fh) -> None:
    """DXF R12 minimal header."""
    _w(fh, 999, _BRAND_NAME)
    _w(fh, 0, "SECTION")
    _w(fh, 2, "HEADER")
    _w(fh, 9, "$ACADVER")
    _w(fh, 1, "AC1009")
    _w(fh, 9, "$INSUNITS")
    _w(fh, 70, 4)            # 4 = millimetres
    _w(fh, 0, "ENDSEC")
    _w(fh, 0, "SECTION")
    _w(fh, 2, "TABLES")
    _w(fh, 0, "TABLE")
    _w(fh, 2, "LAYER")
    _w(fh, 70, 5)
    for name, color in [
        ("FOOTING", 7),    # white
        ("COLUMN", 2),     # yellow
        ("REBAR_X", 1),    # red
        ("REBAR_Y", 5),    # blue
        ("DIM", 8),        # grey
        ("TEXT", 7),
    ]:
        _w(fh, 0, "LAYER")
        _w(fh, 2, name)
        _w(fh, 70, 0)
        _w(fh, 62, color)
        _w(fh, 6, "CONTINUOUS")
    _w(fh, 0, "ENDTAB")
    _w(fh, 0, "ENDSEC")
    _w(fh, 0, "SECTION")
    _w(fh, 2, "ENTITIES")


def _end_dxf(fh) -> None:
    _w(fh, 0, "ENDSEC")
    _w(fh, 0, "EOF")


def _line(fh, x1: float, y1: float, x2: float, y2: float, layer: str) -> None:
    _w(fh, 0, "LINE")
    _w(fh, 8, layer)
    _w(fh, 10, f"{x1:.3f}")
    _w(fh, 20, f"{y1:.3f}")
    _w(fh, 30, 0.0)
    _w(fh, 11, f"{x2:.3f}")
    _w(fh, 21, f"{y2:.3f}")
    _w(fh, 31, 0.0)


def _rectangle(fh, x_min: float, y_min: float, x_max: float, y_max: float,
              layer: str) -> None:
    _line(fh, x_min, y_min, x_max, y_min, layer)
    _line(fh, x_max, y_min, x_max, y_max, layer)
    _line(fh, x_max, y_max, x_min, y_max, layer)
    _line(fh, x_min, y_max, x_min, y_min, layer)


def _text(fh, x: float, y: float, height: float, text: str, layer: str = "TEXT") -> None:
    _w(fh, 0, "TEXT")
    _w(fh, 8, layer)
    _w(fh, 10, f"{x:.3f}")
    _w(fh, 20, f"{y:.3f}")
    _w(fh, 30, 0.0)
    _w(fh, 40, f"{height:.3f}")
    _w(fh, 1, text)


def export_footing_dxf(
    output_path: str,
    B_mm: float, L_mm: float,
    column_a_mm: float = 0.0,
    rebar_long_count: int = 0,
    rebar_long_dia_mm: int = 0,
    rebar_trans_count: int = 0,
    rebar_trans_dia_mm: int = 0,
    cover_mm: float = 70,
    title: str = "Footing plan",
) -> str:
    """Export a footing plan + rebar layout to DXF.

    Args:
        B_mm: short-side width (y).
        L_mm: long-side length (x).
        column_a_mm: square-column side (0 = no column drawn).
        rebar_long_count: number of bars in the long direction (along x).
        rebar_long_dia_mm: bar diameter (ϕ) in the long direction.
        rebar_trans_count: number of bars in the short direction (along y).
        rebar_trans_dia_mm: bar diameter in the short direction.
        cover_mm: concrete cover.
        title: title text written below the plan.

    Returns:
        Absolute path of the written DXF file.
    """
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="ascii") as fh:
        _start_dxf(fh)
        x_min, x_max = -L_mm / 2, L_mm / 2
        y_min, y_max = -B_mm / 2, B_mm / 2

        # 1. Footing outline
        _rectangle(fh, x_min, y_min, x_max, y_max, "FOOTING")

        # 2. Column
        if column_a_mm > 0:
            _rectangle(fh, -column_a_mm / 2, -column_a_mm / 2,
                      column_a_mm / 2, column_a_mm / 2, "COLUMN")

        # 3. Longitudinal bars (along x, spaced over B)
        if rebar_long_count > 1:
            inner_top = y_max - cover_mm
            inner_bot = y_min + cover_mm
            spacing = (inner_top - inner_bot) / (rebar_long_count - 1)
            x_bar_min = x_min + cover_mm
            x_bar_max = x_max - cover_mm
            for i in range(rebar_long_count):
                y = inner_bot + i * spacing
                _line(fh, x_bar_min, y, x_bar_max, y, "REBAR_X")

        # 4. Transverse bars (along y, spaced over L)
        if rebar_trans_count > 1:
            inner_left = x_min + cover_mm
            inner_right = x_max - cover_mm
            spacing = (inner_right - inner_left) / (rebar_trans_count - 1)
            y_bar_min = y_min + cover_mm
            y_bar_max = y_max - cover_mm
            for i in range(rebar_trans_count):
                x = inner_left + i * spacing
                _line(fh, x, y_bar_min, x, y_bar_max, "REBAR_Y")

        # 5. Title + dimensions
        _text(fh, x_min, y_min - 200, 80, title, "TEXT")
        _text(fh, x_min, y_min - 320, 60,
             f"B x L = {B_mm:.0f} x {L_mm:.0f} mm  |  cover {cover_mm:.0f} mm",
             "TEXT")
        if rebar_long_count > 0:
            _text(fh, x_min, y_min - 420, 60,
                 f"X: {rebar_long_count} phi {rebar_long_dia_mm} mm   "
                 f"Y: {rebar_trans_count} phi {rebar_trans_dia_mm} mm",
                 "TEXT")
        _end_dxf(fh)
    return output_path


__all__ = ["export_footing_dxf"]
