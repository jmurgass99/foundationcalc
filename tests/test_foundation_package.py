"""packages/FoundationDesignJm/tests/test_foundation_package.py
=============================================================
Pruebas de Carril B: Entregables de Cimentación (Armado, DXF, Memoria, Cantidades y Zapatas Combinadas).
"""
from __future__ import annotations

import math
from pathlib import Path
import tempfile
import pytest

from foundationdesignjm.core.material import Concrete, ReinforcingSteel
from foundationdesignjm.design.reinforcement import (
    anchorage_length_ec2,
    design_footing_flexure_both_ways,
    select_footing_rebar,
)
from foundationdesignjm.integration.dxf_armado import ArmadoZapataDXF, export_armado_zapata
from foundationdesignjm.integration.foundation_chain import (
    FoundationPackageResult,
    foundation_package,
)
from jmstructural_common.model import Reaction


def test_anchorage_length_ec2():
    """Verifica el cálculo de anclaje básico y de diseño según EC2 §8.4.3/§8.4.4."""
    # Para C30/37 (fck=30 MPa, fctm=0.30*30^(2/3) ≈ 2.896 MPa, fctd = 0.7*2.896/1.5 ≈ 1.352 MPa)
    # fbd = 2.25 * 1.0 * 1.0 * 1.352 ≈ 3.041 MPa
    # fyd = 500 / 1.15 = 434.78 MPa
    # Phi = 16 mm -> l_b_rqd = (16/4) * (434.78 / 3.041) ≈ 571.9 mm
    l_b_rqd, l_bd = anchorage_length_ec2(
        phi_mm=16.0,
        fck_MPa=30.0,
        fyk_MPa=500.0,
        alpha_hook=False,
    )
    assert 550.0 < l_b_rqd < 600.0
    assert l_bd >= l_b_rqd

    # Con gancho (alpha1 = 0.7)
    _, l_bd_hook = anchorage_length_ec2(
        phi_mm=16.0,
        fck_MPa=30.0,
        fyk_MPa=500.0,
        alpha_hook=True,
    )
    assert l_bd_hook < l_bd
    assert math.isclose(l_bd_hook, 0.7 * l_b_rqd, rel_tol=1e-2)


def test_select_footing_rebar():
    """Verifica la selección de armadura cumpliendo espaciamientos normativos."""
    # 1200 mm2 en un ancho de 1500 mm, canto 500 mm
    phi, spacing, n_bars = select_footing_rebar(
        As_prov_mm2=1200.0,
        width_mm=1500.0,
        thickness_mm=500.0,
        preferred_phi_mm=16.0,
        cover_mm=50.0,
    )
    assert phi in [10.0, 12.0, 16.0, 20.0, 25.0, 32.0]
    assert spacing <= min(2.5 * 500.0, 250.0)
    assert spacing >= 100.0
    assert n_bars >= 3
    area_total = n_bars * (math.pi * phi ** 2) / 4.0
    assert area_total >= 1200.0 * 0.95


def test_design_footing_flexure_both_ways():
    """Verifica el dimensionado a flexión en ambas direcciones de una zapata."""
    details = design_footing_flexure_both_ways(
        B_m=1.80,
        L_m=2.00,
        h_m=0.55,
        N_Ed_kN=600.0,
        cx_m=0.40,
        cy_m=0.40,
        concrete=Concrete(fck=30),
        steel=ReinforcingSteel(fyk=500),
    )
    assert "X" in details and "Y" in details
    det_x = details["X"]
    det_y = details["Y"]

    assert det_x.M_Ed_kNm > 0
    assert det_y.M_Ed_kNm > 0
    assert det_x.As_prov_mm2 >= det_x.As_min_mm2
    assert det_y.As_prov_mm2 >= det_y.As_min_mm2
    assert det_x.n_bars >= 3
    assert det_y.n_bars >= 3
    assert det_x.l_bd_mm > 0
    assert det_x.l_avail_mm > 0


def test_dxf_armado_zapata_ezdxf_roundtrip(tmp_path: Path):
    """Verifica que el DXF generado se pueda leer y contenga capas y entidades correctas."""
    import ezdxf

    arm = ArmadoZapataDXF(
        B_m=1.60,
        L_m=1.60,
        H_m=0.50,
        n_x=8,
        n_y=8,
        db_x_mm=16.0,
        db_y_mm=16.0,
        s_x_mm=200.0,
        s_y_mm=200.0,
        column_cx_m=0.40,
        column_cy_m=0.40,
        cover_mm=50.0,
        footing_name="ZAPATA_TEST_C1",
    )

    dxf_file = tmp_path / "test_zapata_c1.dxf"
    ok = export_armado_zapata(arm, dxf_file)
    assert ok is True
    assert dxf_file.exists()

    # Lazo lector con ezdxf
    doc = ezdxf.readfile(str(dxf_file))
    msp = doc.modelspace()

    # Capas esperadas
    layer_names = {layer.dxf.name for layer in doc.layers}
    for expected in ["PLANTA", "COLUMNA", "REBAR_X", "REBAR_Y", "TEXTOS"]:
        assert expected in layer_names

    # Contorno de zapata y columna (polilíneas)
    polylines = msp.query("LWPOLYLINE")
    assert len(polylines) >= 2

    # Barras de armado (líneas)
    lines_x = [e for e in msp.query("LINE") if e.dxf.layer == "REBAR_X"]
    lines_y = [e for e in msp.query("LINE") if e.dxf.layer == "REBAR_Y"]
    assert len(lines_x) == 8
    assert len(lines_y) == 8

    # Rótulo de textos
    texts = msp.query("TEXT")
    assert len(texts) >= 2


def test_foundation_package_complete(tmp_path: Path):
    """Verifica la generación completa del paquete de entregables (planos, memoria, cubicaciones)."""
    reactions = [
        Reaction(node_id="C1", case="COMB1", fx_kN=10.0, fy_kN=5.0, fz_kN=450.0, mx_kNm=20.0, my_kNm=15.0),
        Reaction(node_id="C2", case="COMB1", fx_kN=-8.0, fy_kN=4.0, fz_kN=600.0, mx_kNm=25.0, my_kNm=18.0),
        Reaction(node_id="C3", case="COMB1", fx_kN=12.0, fy_kN=-6.0, fz_kN=750.0, mx_kNm=30.0, my_kNm=22.0),
        Reaction(node_id="C4", case="COMB1", fx_kN=-5.0, fy_kN=-5.0, fz_kN=350.0, mx_kNm=15.0, my_kNm=10.0),
    ]
    coords = {
        "C1": (0.0, 0.0),
        "C2": (6.0, 0.0),
        "C3": (6.0, 6.0),
        "C4": (0.0, 6.0),
    }
    soil = {
        "allowable_bearing_kPa": 250.0,
        "subgrade_modulus_ks_kN_m3": 40000.0,
        "min_size_m": 1.20,
    }

    pkg: FoundationPackageResult = foundation_package(
        etabs_or_reactions=reactions,
        soil_params=soil,
        footing_thickness_m=0.50,
        concrete_fck_MPa=30.0,
        steel_fyk_MPa=500.0,
        column_dimensions=(0.40, 0.40),
        column_coordinates=coords,
        output_dir=tmp_path,
        project_name="EDIFICIO DEPORTIVO JM",
        engineer_name="ING. JESUS MURGA",
    )

    # Verificaciones del paquete
    assert len(pkg.design_summary) == 4
    assert len(pkg.flexure_reinforcement) == 4
    assert len(pkg.punching_checks) == 4
    assert len(pkg.winkler_springs) == 4
    assert len(pkg.dxf_paths) == 4
    for dxf_p in pkg.dxf_paths:
        assert Path(dxf_p).exists()

    # Cantidades y cubicaciones
    assert pkg.total_concrete_m3 > 0.0
    assert pkg.total_steel_kg > 0.0
    assert pkg.total_formwork_m2 > 0.0
    assert pkg.quantities["steel_ratio_kg_m3"] > 20.0

    # Memoria de cálculo en Markdown
    assert (tmp_path / "memoria_cimentaciones.md").exists()
    assert "# MEMORIA DE CÁLCULO DE CIMENTACIONES" in pkg.memoria_markdown
    assert "EDIFICIO DEPORTIVO JM" in pkg.memoria_markdown
    assert "Eurocódigo 2" in pkg.memoria_markdown
    assert "| `C1` |" in pkg.memoria_markdown
    assert "| `C2` |" in pkg.memoria_markdown
    assert "| `C3` |" in pkg.memoria_markdown
    assert "| `C4` |" in pkg.memoria_markdown


def test_foundation_package_detects_combined_footing(tmp_path: Path):
    """Verifica que dos columnas muy cercanas activen el diseño de zapata combinada."""
    reactions = [
        Reaction(node_id="C1", case="COMB1", fx_kN=0.0, fy_kN=0.0, fz_kN=500.0, mx_kNm=0.0, my_kNm=0.0),
        Reaction(node_id="C2", case="COMB1", fx_kN=0.0, fy_kN=0.0, fz_kN=500.0, mx_kNm=0.0, my_kNm=0.0),
    ]
    # Distancia entre centros de columnas de solo 1.2 m (las zapatas de 1.5m solaparán)
    coords = {
        "C1": (0.0, 0.0),
        "C2": (1.20, 0.0),
    }
    soil = {
        "allowable_bearing_kPa": 200.0,
        "min_size_m": 1.20,
    }

    pkg: FoundationPackageResult = foundation_package(
        etabs_or_reactions=reactions,
        soil_params=soil,
        footing_thickness_m=0.60,
        column_dimensions=(0.40, 0.40),
        column_coordinates=coords,
        output_dir=tmp_path,
    )

    assert len(pkg.combined_footings) >= 1
    comb = pkg.combined_footings[0]
    assert comb.L_m > 1.20
    assert comb.As_top_mm2 > 0 or comb.As_bot_mm2 > 0
    assert "Zapatas Combinadas por Solape" in pkg.memoria_markdown
