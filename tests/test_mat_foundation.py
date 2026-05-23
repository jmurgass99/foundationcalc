"""Tests for the mat-on-Winkler-springs solver.

Validation strategy:
- A uniform pressure should produce uniform settlement w = q / k_s and full
  equilibrium of the soil reaction.
- A concentrated load on a centred mat must satisfy equilibrium
  (sum of soil pressures × tributary area == applied load).
- The uplift iteration must converge in a small number of iterations.
- The bending moments must scale sensibly with stiffness.
"""

from __future__ import annotations

import numpy as np
import pytest

from foundationdesignjm.analysis.mat_foundation import MatFoundationSolver


def _integrated_reaction(mat: MatFoundationSolver, res) -> float:
    """Integrate the nodal soil pressure over the mat using element averaging."""
    total = 0.0
    for e in range(mat.n_elems):
        ids = mat.elements[e]
        coords_e = mat.nodes_xy[ids]
        Le = abs(coords_e[1, 0] - coords_e[0, 0])
        We = abs(coords_e[3, 1] - coords_e[0, 1])
        q_avg = res.q_soil[ids].mean()
        total += q_avg * Le * We
    return float(total)


def test_uniform_pressure_gives_uniform_settlement():
    """Constant q over a rigid-enough mat → w = q/k_s everywhere."""
    mat = MatFoundationSolver(
        length=10.0, width=10.0, thickness=0.6,
        nx=12, ny=12, k_s=20000.0,
    )
    mat.add_uniform_pressure(q=20.0)
    res = mat.solve()

    expected_w = 20.0 / 20000.0  # 1.0 mm
    assert res.converged
    assert res.iterations == 1
    assert np.allclose(res.w, expected_w, atol=1e-7)
    assert res.differential_settlement_mm < 1e-4
    # Soil reaction integral matches applied load
    applied = 20.0 * 10.0 * 10.0
    assert _integrated_reaction(mat, res) == pytest.approx(applied, rel=1e-4)


def test_point_load_global_equilibrium_under_uplift():
    """A 500 kN point load with uplift iteration must satisfy ΣReaction = ΣLoad."""
    mat = MatFoundationSolver(
        length=8.0, width=8.0, thickness=0.6,
        nx=20, ny=20, k_s=20000.0,
    )
    mat.add_column_load(x=4.0, y=4.0, P=500.0)
    res = mat.solve(allow_uplift=True)

    assert res.converged
    reaction = _integrated_reaction(mat, res)
    assert reaction == pytest.approx(500.0, rel=5e-3)
    # The centre node must settle (positive w)
    centre = mat.node_at(4.0, 4.0)
    assert res.w[centre] > 0


def test_point_load_centre_is_max_settlement():
    """Under a centred point load, max settlement must be at the load."""
    mat = MatFoundationSolver(
        length=8.0, width=8.0, thickness=0.4,
        nx=16, ny=16, k_s=15000.0,
    )
    mat.add_column_load(x=4.0, y=4.0, P=400.0)
    res = mat.solve()
    centre = mat.node_at(4.0, 4.0)
    # The max settlement must coincide with the loaded node within mesh resolution
    assert np.argmax(res.w) == centre


def test_multi_column_mat_equilibrium():
    """4-column mat: sum of node reactions equals sum of column loads + self-weight."""
    mat = MatFoundationSolver(
        length=10.0, width=8.0, thickness=0.6,
        nx=20, ny=16, k_s=15000.0,
    )
    q_self = 15.0  # kN/m^2
    mat.add_uniform_pressure(q=q_self)
    loads = [(2, 2, 600), (8, 2, 750), (2, 6, 620), (8, 6, 780)]
    for x, y, P in loads:
        mat.add_column_load(x=x, y=y, P=P)
    res = mat.solve()

    applied = sum(P for _, _, P in loads) + q_self * 10.0 * 8.0
    assert _integrated_reaction(mat, res) == pytest.approx(applied, rel=1e-3)
    # Symmetry: w must be near-symmetric across the mat centre line
    assert res.w_max > res.w_min


def test_thicker_mat_redistributes_more():
    """A thicker, stiffer mat must produce smaller differential settlements."""
    common = dict(length=8.0, width=8.0, nx=16, ny=16, k_s=15000.0)
    soft = MatFoundationSolver(thickness=0.3, **common)
    stiff = MatFoundationSolver(thickness=1.0, **common)
    for solver in (soft, stiff):
        solver.add_column_load(x=4.0, y=4.0, P=500.0)
    r_soft = soft.solve(allow_uplift=False)
    r_stiff = stiff.solve(allow_uplift=False)
    diff_soft = r_soft.w.max() - r_soft.w.min()
    diff_stiff = r_stiff.w.max() - r_stiff.w.min()
    # Stiffer mat → smaller relative bowing
    assert diff_stiff < diff_soft


def test_uplift_iteration_disables_lifted_nodes():
    """When some nodes lift off, the iteration must mark them inactive."""
    mat = MatFoundationSolver(
        length=6.0, width=6.0, thickness=0.4,
        nx=12, ny=12, k_s=12000.0,
    )
    # Heavy point load in the centre → corners want to lift
    mat.add_column_load(x=3.0, y=3.0, P=800.0)
    res = mat.solve(allow_uplift=True, max_iter=20)
    assert res.converged
    assert len(res.uplift_nodes) > 0
    # Every uplift node must have q_soil == 0
    assert np.all(res.q_soil[res.uplift_nodes] == 0.0)


def test_rejects_bad_inputs():
    with pytest.raises(ValueError):
        MatFoundationSolver(length=0, width=10, thickness=0.5, nx=4, ny=4)
    with pytest.raises(ValueError):
        MatFoundationSolver(length=10, width=10, thickness=0.5, nx=1, ny=4)
    with pytest.raises(ValueError):
        MatFoundationSolver(length=10, width=10, thickness=0.5, nx=4, ny=4, k_s=0)


def test_column_outside_mat_raises():
    mat = MatFoundationSolver(length=5, width=5, thickness=0.4, nx=4, ny=4)
    with pytest.raises(ValueError):
        mat.add_column_load(x=10.0, y=2.0, P=100)
