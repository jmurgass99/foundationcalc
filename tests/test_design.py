"""Tests for design modules (punching, reinforcement, pile caps, strap beams)."""

import math
import pytest

from foundationdesignjm.core.geometry import Column, RectangularFoundation
from foundationdesignjm.core.material import Concrete, ReinforcingSteel
from foundationdesignjm.design.pile_cap import (
    cap_four_piles,
    cap_three_piles,
    cap_two_piles,
    distribute_forces_rigid_cap,
)
from foundationdesignjm.design.punching_shear import punching_shear_check
from foundationdesignjm.design.reinforcement import (
    critical_section_offset,
    flexural_reinforcement,
    reinforcement_distribution_rectangular_footing,
)
from foundationdesignjm.design.strap_beam import (
    GroundType,
    seismic_tie_force,
    strap_for_two_footings,
    tie_beam_minimum_dimensions,
)


C25 = Concrete(name="C25/30", fck=25.0)
B500 = ReinforcingSteel(name="B500S", fyk=500.0)


def test_strut_and_tie_two_piles():
    """Cap on 2 piles, N=1000 kN, v=500 mm, a=400 mm, d=700 mm.

    T_d = 1000·1000·(500 + 0.25·400) / (0.85·700) = 1,008,403 N
    """
    res = cap_two_piles(N_d_kN=1000.0, v_mm=500.0, a_mm=400.0, d_mm=700.0, steel=B500)
    assert res.T_d == pytest.approx(1_008_403.0, rel=0.01)
    # fyd_STM = min(500/1.15, 400) = 400 MPa → As = T/400
    assert res.A_s == pytest.approx(res.T_d / 400.0, rel=0.01)


def test_punching_shear_central_column():
    """Central column 400×400, footing 2500×2500×600, d=540 mm, ρ=0.005."""
    fdn = RectangularFoundation(length=2500.0, width=2500.0, thickness=600.0)
    col = Column(length=400.0, width=400.0, pos_x=1250.0, pos_y=1250.0)
    res = punching_shear_check(
        foundation=fdn,
        column=col,
        N_sd_kN=1500.0,
        fck_MPa=25.0,
        rho_x=0.005,
        rho_y=0.005,
        d_eff_m=0.540,
    )
    assert res.beta == 1.15
    assert res.u1 > 0
    assert res.tau_rd > 0
    assert res.xi == pytest.approx(1.0 + math.sqrt(200 / 540), rel=1e-6)


def test_critical_section_offsets():
    assert critical_section_offset(a_mm=400.0) == pytest.approx(60.0)
    assert critical_section_offset(a_mm=400.0, masonry_wall=True) == pytest.approx(100.0)


def test_flexural_reinforcement_basic():
    """Bending design of a 1 m wide footing strip, d = 540 mm, M = 100 kN·m.

    EC2 lever-arm method gives z ≈ 0.95·d for low ρ; result ≈ 449 mm².
    """
    res = flexural_reinforcement(
        M_Ed_kNm=100.0, b_mm=1000.0, d_mm=540.0, concrete=C25, steel=B500
    )
    # K = 100e6 / (1000·540²·25) = 0.0137 → z ≈ 0.95·d = 513 mm → As ≈ 100e6/(513·435) = 448
    assert res.As_required == pytest.approx(448.0, rel=0.05)
    assert res.As_provided >= res.As_min


def test_reinforcement_distribution_rectangular():
    out = reinforcement_distribution_rectangular_footing(
        As_total=2000.0, a_prime_m=3.0, b_prime_m=2.0, h_m=0.6, a_m=0.4,
    )
    assert out["fraction_central"] == pytest.approx(2 * 2.0 / (3.0 + 2.0))
    assert out["As_central"] + out["As_lateral"] == pytest.approx(2000.0)


def test_pile_cap_3_piles():
    res = cap_three_piles(N_d_kN=1500.0, l_mm=1500.0, a_mm=400.0, d_mm=800.0, steel=B500)
    expected_Td = 0.68 * 1500.0 * 1000.0 / 800.0 * (0.58 * 1500.0 - 0.25 * 400.0)
    assert res.T_d == pytest.approx(expected_Td, rel=0.01)


def test_pile_cap_4_piles_two_directions():
    r1, r2 = cap_four_piles(
        N_d_kN=2000.0, l1_mm=1500.0, l2_mm=1500.0, a1_mm=400.0, a2_mm=400.0, d_mm=900.0, steel=B500,
    )
    assert r1.T_d == pytest.approx(r2.T_d, rel=1e-6)


def test_distribute_forces_rigid_cap_symmetric():
    """4 piles at corners of 2×2 m square, V = 800 kN central, M = 0:
    each pile gets 200 kN.
    """
    positions = [(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)]
    forces = distribute_forces_rigid_cap(800.0, 0.0, 0.0, positions)
    assert forces == [200.0] * 4


def test_distribute_forces_rigid_cap_with_moment():
    """Same 4 piles, M_y = 800 kN·m → piles at +x get an extra 200, those at −x lose 200."""
    positions = [(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)]
    forces = distribute_forces_rigid_cap(800.0, 0.0, 800.0, positions)
    # F_iv = 200 + 800·x_i / Σx² = 200 + 800·x_i / 4 = 200 + 200·x_i
    expected = [400.0, 0.0, 400.0, 0.0]
    assert forces == pytest.approx(expected)


def test_strap_beam_default():
    spec = strap_for_two_footings(N1_kN=500.0, N2_kN=800.0, length_mm=4000.0)
    assert spec.design_axial_kN == pytest.approx(0.03 * (500 + 800))
    assert spec.depth_mm >= 350.0
    assert spec.width_mm == 300.0


def test_seismic_tie_force():
    assert seismic_tie_force(1000.0, 0.20, GroundType.B) == pytest.approx(60.0)
    assert seismic_tie_force(1000.0, 0.20, GroundType.C) == pytest.approx(80.0)
    assert seismic_tie_force(1000.0, 0.20, GroundType.D) == pytest.approx(120.0)


def test_tie_beam_minimum_dimensions():
    assert tie_beam_minimum_dimensions(2) == (250.0, 400.0)
    assert tie_beam_minimum_dimensions(5) == (250.0, 500.0)
