"""Tests for the strengthening module."""

from __future__ import annotations

import pytest

from foundationcalc.design.strengthening import (
    MicropileGeometry,
    MicropileSoilType,
    StructureType,
    UnderpinningPit,
    angular_distortion_check,
    enlarged_footing_pressure,
    mass_concrete_underpinning,
    micropile_capacity,
    micropile_group_capacity,
)


# ----------------------------------------------------------- distortion -----

def test_distortion_ok_below_limit():
    r = angular_distortion_check(
        delta_s_AB_mm=8.0, L_AB_m=6.0,
        structure_type=StructureType.FRAME_WITH_PARTITIONS,
    )
    assert r.beta == pytest.approx(8.0 / 1000.0 / 6.0)
    assert r.beta_limit == pytest.approx(1.0 / 500.0)
    assert r.ok
    assert r.utilization < 1.0


def test_distortion_fails_for_masonry_strict_limit():
    """A distortion of 1/700 fails the unreinforced masonry hogging limit (1/2000)."""
    r = angular_distortion_check(
        delta_s_AB_mm=10.0, L_AB_m=7.0,
        structure_type=StructureType.UNREINFORCED_MASONRY_HOGGING,
    )
    assert not r.ok


def test_distortion_zero_length_raises():
    with pytest.raises(ValueError):
        angular_distortion_check(5.0, 0.0, StructureType.ISOSTATIC)


# ------------------------------------------------------- footing enlargement

def test_enlarged_footing_reduces_pressure():
    r = enlarged_footing_pressure(
        N_kN=900.0, A_old_m2=2.0 * 2.0,
        new_width_m=3.0, new_length_m=3.0,
    )
    assert r.q_old == pytest.approx(900 / 4.0)
    assert r.q_new == pytest.approx(900 / 9.0)
    assert r.reduction_pct > 50.0
    assert r.interface_shear_required > 0


def test_enlarged_smaller_than_old_raises():
    with pytest.raises(ValueError):
        enlarged_footing_pressure(N_kN=900, A_old_m2=9.0, new_width_m=2.0, new_length_m=2.0)


# --------------------------------------------------- mass concrete underpin

def test_underpinning_pressure_and_staging():
    pit = UnderpinningPit(width=0.9, depth_below_old=1.2, along_wall_length=1.0)
    r = mass_concrete_underpinning(
        wall_load_kN_per_m=80.0, wall_length_m=12.0,
        pit=pit, q_allow_kPa=200.0,
    )
    assert r.n_pits == 12
    assert r.N_per_pit == pytest.approx(80.0)
    assert r.q_deepened == pytest.approx(80.0 / (0.9 * 1.0))
    assert r.ok


def test_underpinning_fails_when_overloaded():
    pit = UnderpinningPit(width=0.7, depth_below_old=1.0, along_wall_length=1.0)
    r = mass_concrete_underpinning(
        wall_load_kN_per_m=200.0, wall_length_m=8.0,
        pit=pit, q_allow_kPa=150.0,
    )
    assert not r.ok
    assert r.utilization > 1.0


# --------------------------------------------------------- micropiles

def test_micropile_capacity_sand_lower_bound():
    geo = MicropileGeometry(
        diameter_drilling=0.18, diameter_grouted=0.22,
        length_total=12.0, length_bond=8.0,
    )
    r = micropile_capacity(
        geo, MicropileSoilType.SAND_GRAVEL,
        q_s_kPa=None,           # use the lower bound 80 kPa
        correlation_factor_xi=1.30,
        gamma_R_total=1.50,
        alpha_inj=1.20,
    )
    # Lower bound q_s = 80 kPa, diameter eff = max(0.22, 1.2*0.18) = 0.22 m
    # R_skin_char = pi * 0.22 * 8.0 * 80 = 442 kN
    import math
    expected_char = math.pi * 0.22 * 8.0 * 80.0
    assert r.R_skin_char == pytest.approx(expected_char, rel=1e-3)
    assert r.R_skin_design == pytest.approx(expected_char / (1.30 * 1.50), rel=1e-3)


def test_micropile_capacity_explicit_qs():
    geo = MicropileGeometry(
        diameter_drilling=0.20, diameter_grouted=0.24,
        length_total=10.0, length_bond=6.0,
    )
    r = micropile_capacity(geo, MicropileSoilType.CLAY, q_s_kPa=100.0)
    assert r.q_s_used == 100.0
    assert r.R_total_design > 0


# --------------------------------------------------- micropile groups

def test_group_efficiency_above_3d_is_unity():
    r = micropile_group_capacity(
        n_piles=6, R_per_pile_design_kN=200.0,
        spacing_to_diameter=3.5, N_design_kN=800.0,
    )
    assert r.efficiency_E == 1.0
    assert r.R_group_design == 6 * 200.0


def test_group_efficiency_below_3d_reduces():
    r = micropile_group_capacity(
        n_piles=4, R_per_pile_design_kN=200.0,
        spacing_to_diameter=2.0, N_design_kN=400.0,
    )
    assert r.efficiency_E < 1.0
    assert r.R_group_design < 4 * 200.0


def test_group_rejects_single_pile():
    with pytest.raises(ValueError):
        micropile_group_capacity(1, 200, 3.0, 100)
