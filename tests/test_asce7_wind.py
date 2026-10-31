"""Tests para ASCE 7-22 viento — Procedimiento Direccional."""
from __future__ import annotations

import pytest

from foundationcalc.codes.asce7_wind import (
    Exposure,
    Kz,
    design_wind_pressure,
)


class TestKz:
    def test_monotonic_with_height(self):
        assert Kz(10, Exposure.C) < Kz(50, Exposure.C) < Kz(150, Exposure.C)

    def test_exposure_ordering(self):
        # Exposicion D (costa) > C (campo) > B (urbano) a igual altura
        z = 30.0
        assert Kz(z, Exposure.D) > Kz(z, Exposure.C) > Kz(z, Exposure.B)


class TestDesignPressure:
    def test_components(self):
        r = design_wind_pressure(V=50, z=20, exposure=Exposure.C)
        assert r.qz > 0
        assert r.p_wall_wind > 0       # barlovento positivo
        assert r.p_wall_lee < 0        # sotavento succion
        assert r.p_roof < 0            # cubierta succion

    def test_higher_speed_higher_pressure(self):
        a = design_wind_pressure(V=40, z=20)
        b = design_wind_pressure(V=60, z=20)
        assert b.qz > a.qz
        assert b.p_wall_wind > a.p_wall_wind
