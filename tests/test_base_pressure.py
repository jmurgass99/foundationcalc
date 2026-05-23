"""Tests for the base-pressure analysis (Navier, e>L/6 case)."""

import pytest

from foundationdesignjm.analysis.base_pressure import (
    BasePressureAnalysis,
    PressureRegime,
)
from foundationdesignjm.core.geometry import Column, RectangularFoundation
from foundationdesignjm.core.loading import (
    CombinationEntry,
    LoadCombination,
    LoadType,
    PointLoad,
)


def test_centred_axial_only():
    fdn = RectangularFoundation(length=2500.0, width=2500.0, thickness=600.0)
    col = Column(length=400.0, width=400.0, pos_x=1250.0, pos_y=1250.0)
    g = PointLoad(fz=800.0, load_type=LoadType.PERMANENT)
    combo = LoadCombination(name="ULS", entries=[CombinationEntry(load=g, factor=1.35)])
    bpa = BasePressureAnalysis(fdn, col)
    res = bpa.calculate_pressures(combo, include_self_weight=False)
    assert res.regime == PressureRegime.CENTRED
    # 1.35·800/(2.5·2.5) = 172.8 kPa
    assert res.q_max == pytest.approx(172.8, abs=0.5)
    assert res.q_min == pytest.approx(172.8, abs=0.5)


def test_within_core_uniaxial():
    """e_x < L/6 → all four corners in compression."""
    fdn = RectangularFoundation(length=3000.0, width=2000.0, thickness=500.0)
    col = Column(length=400.0, width=400.0, pos_x=1500.0, pos_y=1000.0)
    load = PointLoad(fz=600.0, my=50.0)  # M_y = 50 kN·m → bending about Y → e_x
    combo = LoadCombination(name="x", entries=[CombinationEntry(load=load, factor=1.0)])
    res = BasePressureAnalysis(fdn, col).calculate_pressures(combo, include_self_weight=False)
    L = 3.0
    e_x_expected = 50.0 / 600.0
    assert abs(e_x_expected) <= L / 6.0
    # Navier: q_max = (N/A)(1 + 6e/L)
    base = 600.0 / (3.0 * 2.0)
    expected_qmax = base * (1 + 6 * e_x_expected / L)
    assert res.q_max == pytest.approx(expected_qmax, abs=0.5)


def test_outside_core_uniaxial():
    """e_x > L/6 → triangular contact pressure."""
    fdn = RectangularFoundation(length=2000.0, width=2000.0, thickness=500.0)
    col = Column(length=400.0, width=400.0, pos_x=1000.0, pos_y=1000.0)
    # e_x = M_y / N; choose M_y so e = 0.5 m > L/6 = 0.333
    load = PointLoad(fz=400.0, my=200.0)
    combo = LoadCombination(name="x", entries=[CombinationEntry(load=load, factor=1.0)])
    res = BasePressureAnalysis(fdn, col).calculate_pressures(combo, include_self_weight=False)
    # a' = 3·(L/2 − e) = 3·(1 − 0.5) = 1.5 m; q_max = 2N/(a'·b) = 800/(1.5·2) = 266.7
    assert res.regime in (PressureRegime.OUTSIDE_CORE, PressureRegime.UNIAXIAL_IN_CORE)
    assert res.q_max == pytest.approx(266.7, abs=2.0)
    assert res.q_min == pytest.approx(0.0, abs=1.0)
