"""Tests para bridge FoundationDesignJm -> GeoJm."""
import sys
from pathlib import Path

# Permitir importar geojm si vive en el workspace adyacente
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "GeoJm"))

import pytest

from foundationdesignjm.integration.geojm_bridge import (
    get_mander_material,
    get_pile_group_efficiency,
    get_py_matlock,
    get_py_reese,
    get_py_springs_from_geojm,
    get_mander_concrete_from_geojm,
    PileLayerData,
    PYSpring,
    ManderConfinedConcrete,
)


@pytest.mark.skipif(
    "geojm" not in sys.modules and not Path(
        sys.path[0]
    ).joinpath("geojm").exists(),
    reason="GeoJm no disponible en este entorno",
)
class TestBridge:
    def test_py_matlock_bridge(self):
        result = get_py_matlock(z_m=3, D_m=0.8, su_kPa=50)
        if result is None:
            pytest.skip("GeoJm no instalado")
        p, y = result
        assert len(p) == len(y)
        assert p[0] == 0

    def test_py_reese_bridge(self):
        result = get_py_reese(z_m=2, D_m=0.6, phi_deg=32)
        if result is None:
            pytest.skip("GeoJm no instalado")
        p, y = result
        assert p[0] == 0

    def test_pile_group_efficiency(self):
        eff = get_pile_group_efficiency(s_over_D=3, rows=3)
        if eff is None:
            pytest.skip("GeoJm no instalado")
        assert 0 < eff.global_efficiency <= 1

    def test_mander_material(self):
        mat = get_mander_material(fc=28, fyh=420, rho_x=0.012, rho_y=0.012,
                                   b_core_mm=420, h_core_mm=420, s_mm=100)
        if mat is None:
            pytest.skip("GeoJm no instalado")
        assert mat.K_confinement > 1.0


# ---- FD-001: Tests for get_py_springs_from_geojm / get_mander_concrete ----

class TestPYSpringsFromGeoJm:
    """Tests for get_py_springs_from_geojm -- always works via fallback."""

    def test_clay_layers_returns_springs(self):
        layers = [
            PileLayerData(z_top_m=0, z_bot_m=5, soil_type="clay",
                          su_kPa=50, gamma_eff=9.0),
            PileLayerData(z_top_m=5, z_bot_m=15, soil_type="clay",
                          su_kPa=80, gamma_eff=10.0),
        ]
        springs = get_py_springs_from_geojm(layers, D_m=0.6, n_springs=10)
        assert len(springs) == 10
        assert all(isinstance(s, PYSpring) for s in springs)
        assert all(s.soil_type == "clay" for s in springs)
        assert springs[0].depth_m < springs[-1].depth_m

    def test_sand_layers_returns_springs(self):
        layers = [
            PileLayerData(z_top_m=0, z_bot_m=12, soil_type="sand",
                          phi_deg=32, gamma_eff=10.0),
        ]
        springs = get_py_springs_from_geojm(layers, D_m=0.8, n_springs=8)
        assert len(springs) == 8
        assert all(s.soil_type == "sand" for s in springs)

    def test_stiffness_increases_with_depth(self):
        layers = [
            PileLayerData(z_top_m=0, z_bot_m=20, soil_type="clay",
                          su_kPa=60, gamma_eff=9.0),
        ]
        springs = get_py_springs_from_geojm(layers, D_m=0.6, n_springs=10)
        # Stiffness should generally increase with depth
        assert springs[-1].k_kN_m2 >= springs[0].k_kN_m2

    def test_empty_pile_data(self):
        assert get_py_springs_from_geojm([], D_m=0.6) == []

    def test_mixed_clay_sand_layers(self):
        layers = [
            PileLayerData(z_top_m=0, z_bot_m=5, soil_type="clay",
                          su_kPa=40, gamma_eff=9.0),
            PileLayerData(z_top_m=5, z_bot_m=15, soil_type="sand",
                          phi_deg=30, gamma_eff=10.0),
        ]
        springs = get_py_springs_from_geojm(layers, D_m=0.6, n_springs=10)
        assert len(springs) == 10
        clay_count = sum(1 for s in springs if s.soil_type == "clay")
        sand_count = sum(1 for s in springs if s.soil_type == "sand")
        assert clay_count > 0
        assert sand_count > 0

    def test_p_ult_positive(self):
        layers = [
            PileLayerData(z_top_m=0, z_bot_m=10, soil_type="clay",
                          su_kPa=50, gamma_eff=9.0),
        ]
        springs = get_py_springs_from_geojm(layers, D_m=0.6, n_springs=5)
        for s in springs:
            assert s.p_ult_kN_m >= 0


class TestManderConcreteFromGeoJm:
    """Tests for get_mander_concrete_from_geojm -- fallback always works."""

    def test_returns_mander_tuple(self):
        result = get_mander_concrete_from_geojm(
            fc=28, fyh=420, rho_s=0.02,
            b_core_mm=400, h_core_mm=400, s_mm=100,
        )
        assert isinstance(result, ManderConfinedConcrete)
        assert result.fcc > 28       # confined > unconfined
        assert result.eps_cc > 0.002  # greater than unconfined strain
        assert result.eps_cu > result.eps_cc

    def test_higher_rho_gives_more_confinement(self):
        r_low = get_mander_concrete_from_geojm(fc=30, fyh=420, rho_s=0.005)
        r_high = get_mander_concrete_from_geojm(fc=30, fyh=420, rho_s=0.04)
        assert r_high.fcc > r_low.fcc
        assert r_high.eps_cu > r_low.eps_cu

    def test_values_propagate_correctly(self):
        result = get_mander_concrete_from_geojm(
            fc=25, fyh=300, rho_s=0.01,
        )
        # fcc must be between fc and ~2*fc for reasonable rho_s
        assert 25 < result.fcc < 60
        assert 0.002 < result.eps_cc < 0.02
        assert 0.004 < result.eps_cu < 0.10
