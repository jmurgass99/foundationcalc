"""
dxf_export.py — Export footing designs to DXF structural drawings.
"""
import sys
import os

def export_footing_dxf(L_m: float, B_m: float, h_m: float, rebar_bottom_x_dia: float, rebar_bottom_y_dia: float, spacing_m: float, filepath: str):
    """
    Exports an isolated footing design to DXF using DXFStructuralJm.
    """
    dxf_dir = r"C:\Users\jesus\OneDrive\Escritorio\NEW CODES\STRUCTURAL\APIS\EN PROYECTO\DXFStructuralJm"
    if dxf_dir not in sys.path:
        sys.path.append(dxf_dir)
        
    try:
        from dxfstructuraljm import FoundationPlan
        
        # We need a list of footings (L_x, L_y, h, x, y, id)
        footings = [
            (L_m * 1000, B_m * 1000, h_m * 1000, 0.0, 0.0, "Z-1")
        ]
        
        plan = FoundationPlan(footings)
        plan.draw(filepath)
        return True
    except ImportError as e:
        print(f"Error importing DXFStructuralJm: {e}")
        return False
