"""Tests for the layered soil profile model."""

import math
import pytest

from foundationcalc.core.soil import (
    SoilLayer,
    SoilProfile,
    SoilType,
    homogeneous_clay,
    homogeneous_sand,
)


def test_homogeneous_sand_K0():
    sand = homogeneous_sand(phi=30.0)
    layer = sand.layers[0]
    assert layer.K0() == pytest.approx(0.5)
    assert layer.Ka_rankine() == pytest.approx(math.tan(math.radians(30.0)) ** 2, rel=1e-9)


def test_stresses_no_water_table():
    profile = SoilProfile(
        layers=[
            SoilLayer(name="L1", thickness=2.0, friction_angle=30.0, unit_weight=18.0),
            SoilLayer(name="L2", thickness=3.0, friction_angle=35.0, unit_weight=20.0),
        ]
    )
    # At z=2: σ = 18·2 = 36 kPa
    assert profile.total_stress_at(2.0) == pytest.approx(36.0)
    # At z=4: σ = 36 + 20·2 = 76 kPa
    assert profile.total_stress_at(4.0) == pytest.approx(76.0)
    assert profile.pore_pressure_at(4.0) == 0.0
    assert profile.effective_stress_at(4.0) == pytest.approx(76.0)


def test_pore_pressure_below_WT():
    profile = SoilProfile(
        layers=[
            SoilLayer(
                name="sand", thickness=10.0, friction_angle=32.0,
                unit_weight=18.0, saturated_unit_weight=20.0,
            ),
        ],
        water_table_depth=2.0,
    )
    # Total stress at z=5 = 18·2 + 20·3 = 96
    assert profile.total_stress_at(5.0) == pytest.approx(96.0, rel=1e-6)
    # u = 9.81 · 3 = 29.43
    assert profile.pore_pressure_at(5.0) == pytest.approx(29.43, rel=1e-3)
    # σ' = 96 − 29.43 = 66.57
    assert profile.effective_stress_at(5.0) == pytest.approx(66.57, rel=1e-3)


def test_layer_at_depth():
    profile = SoilProfile(
        layers=[
            SoilLayer(name="A", thickness=2.0, friction_angle=30.0, unit_weight=18.0),
            SoilLayer(name="B", thickness=3.0, friction_angle=35.0, unit_weight=20.0),
        ]
    )
    assert profile.layer_at(1.0).name == "A"
    assert profile.layer_at(3.0).name == "B"
    assert profile.layer_at(10.0).name == "B"  # extends to infinity


def test_clay_undrained():
    clay = homogeneous_clay(cu=50.0)
    assert clay.layers[0].undrained_shear_strength == 50.0
    assert clay.layers[0].soil_type == SoilType.COHESIVE
