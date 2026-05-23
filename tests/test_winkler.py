"""Tests headless de Winkler / Gazetas y export FastSAP."""
from __future__ import annotations

import pytest

from foundationdesignjm.analysis.winkler import (
    FootingGeometry,
    SoilLayer,
    WinklerStiffness,
    _equivalent_layer,
    gazetas_stiffness,
)


def test_soil_layer_G_and_E():
    s = SoilLayer(thickness=5.0, Vs=200.0, rho=1800.0, nu=0.3)
    assert s.G == pytest.approx(1800 * 200 ** 2)
    assert s.E == pytest.approx(2 * s.G * 1.3)


def test_equivalent_layer_single():
    s = SoilLayer(thickness=10.0, Vs=200.0)
    eq = _equivalent_layer([s], depth_influence=8.0)
    assert eq.Vs == pytest.approx(200.0, rel=0.01)


def test_equivalent_layer_two():
    s1 = SoilLayer(thickness=2.0, Vs=150.0, rho=1800)
    s2 = SoilLayer(thickness=10.0, Vs=300.0, rho=2000)
    eq = _equivalent_layer([s1, s2], depth_influence=6.0)
    assert 150 < eq.Vs < 300


def test_gazetas_square_footing():
    soil = SoilLayer(thickness=10.0, Vs=250.0, rho=1900.0, nu=0.3)
    foot = FootingGeometry(L=3.0, B=3.0)
    k = gazetas_stiffness(foot, soil)
    assert k.Kz > 0 and k.Kx > 0 and k.Ky > 0
    assert k.Kx == pytest.approx(k.Ky, rel=0.05)


def test_gazetas_rectangular_footing():
    soil = SoilLayer(thickness=10.0, Vs=250.0)
    foot = FootingGeometry(L=4.0, B=2.0)
    k = gazetas_stiffness(foot, soil)
    assert k.Krx != pytest.approx(k.Kry)


def test_winkler_as_tuple_order():
    k = WinklerStiffness(Kx=1e7, Ky=2e7, Kz=3e7, Krx=4e7, Kry=5e7, Krz=6e7)
    assert k.as_tuple() == (1e7, 2e7, 3e7, 4e7, 5e7, 6e7)


def test_stratified_soil_uses_average():
    layers = [
        SoilLayer(thickness=1.0, Vs=120.0, rho=1700),
        SoilLayer(thickness=4.0, Vs=300.0, rho=2000),
    ]
    foot = FootingGeometry(L=2.0, B=2.0)
    k = gazetas_stiffness(foot, layers)
    k_soft = gazetas_stiffness(foot, layers[0])
    k_stiff = gazetas_stiffness(foot, layers[1])
    assert k_soft.Kz < k.Kz < k_stiff.Kz


def test_higher_Vs_higher_K():
    foot = FootingGeometry(L=3.0, B=2.0)
    k1 = gazetas_stiffness(foot, SoilLayer(thickness=10, Vs=150))
    k2 = gazetas_stiffness(foot, SoilLayer(thickness=10, Vs=400))
    assert k2.Kz > k1.Kz
    assert k2.Krx > k1.Krx


def test_export_winkler_springs_with_mock():
    """Test del puente usando un cliente fake estilo SAP OAPI."""
    pytest.importorskip("fastsap")
    from types import SimpleNamespace

    calls = []

    class _PointObj:
        @staticmethod
        def SetSpring(name, k, item_type=0, is_local=False, replace=True):
            calls.append((name, tuple(k)))
            return 0

    class _SapModel:
        PointObj = _PointObj

        @staticmethod
        def GetModelIsLocked():
            return False

        @staticmethod
        def SetModelIsLocked(v):
            return 0

    fake = SimpleNamespace(SapModel=_SapModel)

    from foundationdesignjm.integration.fastsap_bridge import (
        FastSAPFoundationPipeline,
    )

    pipe = FastSAPFoundationPipeline(sap_client=fake)
    res = pipe.export_winkler_springs({
        "J1": WinklerStiffness(1e7, 1e7, 2e7, 5e6, 5e6, 1e6),
        "J2": WinklerStiffness(2e7, 2e7, 4e7, 0, 0, 0),
    })
    assert res["n_applied"] == 2 and res["n_failed"] == 0
    assert len(calls) == 2
    # Orden de llamada == orden del dict (Python 3.7+)
    assert calls[0][1] == (1e7, 1e7, 2e7, 5e6, 5e6, 1e6)
