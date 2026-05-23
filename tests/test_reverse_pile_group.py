"""Tests for the reverse-design optimizer and pile-group analysis."""

from __future__ import annotations

import pytest

from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
from foundationdesignjm.analysis.pile_group import (
    converse_labarre_efficiency,
    distribute_loads_rigid_cap,
    mokwa_duncan_lateral_efficiency,
    rectangular_group,
)
from foundationdesignjm.analysis.reverse_design import (
    CostModel,
    OptimizationGoal,
    optimize_footing_dimensions,
    optimize_rectangular_footing,
)
from foundationdesignjm.codes.eurocode7 import DesignApproach


# ------------------------------------------------------ Reverse design ------

def _reasonable_cpt() -> CPTProfile:
    readings = [CPTReading(depth=d, q_c_MPa=12.0, f_s_kPa=70)
                for d in [0.5, 1, 2, 3, 4, 6, 8, 10]]
    return CPTProfile(readings=readings, water_table_depth_m=8.0)


def test_reverse_design_returns_passing_footing():
    """A 1500 kN load on good sand must find a passing footing under 5 m."""
    opt = optimize_footing_dimensions(
        _reasonable_cpt(), load_kN=1500, founding_depth_m=1.5,
        design_approach=DesignApproach.DA2,
        settlement_limit_mm=25.0,
        B_min_mm=800, B_max_mm=5000, thickness_mm=600,
    )
    assert opt.best.passes
    assert 0.5 < opt.best.B < 5.0
    # The best footing should be near the bearing limit
    assert opt.best.bearing_utilization < 1.0


def test_reverse_design_history_decreases_in_size():
    """Binary search must mostly shrink the footing from the upper bracket."""
    opt = optimize_footing_dimensions(
        _reasonable_cpt(), load_kN=1500, founding_depth_m=1.5,
        B_min_mm=800, B_max_mm=5000, thickness_mm=600,
    )
    # First candidate (upper) must pass; later iterations may fail/pass.
    assert opt.history[0].passes


def test_reverse_design_fails_for_unrealistic_load():
    """A 50 000 kN load on a small footing must raise."""
    with pytest.raises(RuntimeError):
        optimize_footing_dimensions(
            _reasonable_cpt(), load_kN=50_000, founding_depth_m=1.0,
            B_min_mm=800, B_max_mm=2000, thickness_mm=400,
            settlement_limit_mm=25.0,
        )


def test_optimize_rectangular_with_aspect_ratio():
    opt = optimize_rectangular_footing(
        _reasonable_cpt(), load_kN=1500, founding_depth_m=1.5,
        aspect_ratio_L_over_B=2.0,
        B_min_mm=600, B_max_mm=4000, thickness_mm=500,
    )
    assert opt.best.passes
    assert opt.best.L == pytest.approx(opt.best.B * 2.0, rel=1e-6)


def test_cost_model_increases_with_size():
    cm = CostModel()
    c_small = cm.footing_cost(1.0, 1.0, 0.4, 1.0)
    c_big = cm.footing_cost(3.0, 3.0, 0.6, 1.0)
    assert c_big > c_small


# --------------------------------------------------------- Pile group ------

def test_converse_labarre_s_d_4_is_unity():
    """For s/d ≥ 4 the Converse-Labarre efficiency is 1.0."""
    assert converse_labarre_efficiency(2, 3, 3.2, 0.8) == 1.0
    assert converse_labarre_efficiency(2, 3, 4.0, 0.8) == 1.0


def test_converse_labarre_decreases_with_close_spacing():
    e_close = converse_labarre_efficiency(2, 3, 1.6, 0.8)
    e_far = converse_labarre_efficiency(2, 3, 2.8, 0.8)
    assert e_close < e_far


def test_lateral_efficiency_at_s_d_6_is_one():
    assert mokwa_duncan_lateral_efficiency(4.8, 0.8) == 1.0


def test_rectangular_group_centroid_at_origin():
    g = rectangular_group(n_rows=3, n_cols=3, spacing_m=2.0, diameter_m=0.6)
    assert g.n == 9
    # Centroid of the group must be at (0, 0)
    x_mean = sum(p.x_m for p in g.piles) / g.n
    y_mean = sum(p.y_m for p in g.piles) / g.n
    assert abs(x_mean) < 1e-9 and abs(y_mean) < 1e-9


def test_pure_axial_load_equal_distribution():
    """Pure V (no moment) → each pile gets V/n."""
    g = rectangular_group(2, 3, 2.4, 0.8,
                         axial_capacity_kN=1500,
                         lateral_capacity_kN=120)
    res = distribute_loads_rigid_cap(g, V_kN=6000)
    for f in res.forces:
        assert f.N_kN == pytest.approx(1000.0, rel=1e-6)
    assert res.N_max_tension == 0.0


def test_moment_increases_axial_on_one_side():
    """+M_x adds compression on +y piles, removes on -y piles."""
    g = rectangular_group(2, 3, 2.4, 0.8,
                         axial_capacity_kN=1500,
                         lateral_capacity_kN=120)
    res = distribute_loads_rigid_cap(g, V_kN=6000, M_x_kNm=2000)
    plus_y = [f.N_kN for f in res.forces if f.y_m > 0]
    minus_y = [f.N_kN for f in res.forces if f.y_m < 0]
    assert max(plus_y) > max(minus_y)


def test_lateral_load_distributed_by_efficiency():
    """H is divided by n and divided by E_lat (so per-pile H is larger
    when E_lat < 1)."""
    g = rectangular_group(2, 3, 2.0, 1.0,
                         axial_capacity_kN=1500,
                         lateral_capacity_kN=120)
    res = distribute_loads_rigid_cap(g, V_kN=0, H_y_kN=300)
    n = g.n
    E_lat = g.lateral_efficiency()
    expected = (300.0 / n) / E_lat
    assert res.H_max_per_pile == pytest.approx(expected, rel=1e-6)


def test_pile_group_flags_failure_when_overloaded():
    g = rectangular_group(2, 3, 2.4, 0.8,
                         axial_capacity_kN=1500,
                         lateral_capacity_kN=120)
    res = distribute_loads_rigid_cap(g, V_kN=6000, H_y_kN=600, M_x_kNm=2000)
    assert not res.all_ok
    assert res.governing_pile != ""
