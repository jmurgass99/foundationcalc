"""Example: mat / raft foundation analysis on Winkler springs.

Geometry (loosely inspired by the FOUNDATION ASSIGNMENT 4 problem):
- 12 x 10 m rectangular raft, 0.7 m thick
- 6 columns in a 3 x 2 grid carrying gravity loads (kN)
- Self-weight included as a uniform downwards pressure

The solver detects which corner/edge nodes lift off and removes those
springs iteratively. The output prints settlements at every column and the
peak bending moments — those are the values used for armadura design.

Run with:   python -m examples.mat_foundation_example
"""

from __future__ import annotations

from foundationdesignjm.analysis.mat_foundation import MatFoundationSolver


def build_solver() -> MatFoundationSolver:
    mat = MatFoundationSolver(
        length=12.0,
        width=10.0,
        thickness=0.7,
        nx=24,
        ny=20,
        E_concrete=33e6,    # kN/m^2 (C30/37 ≈ 33 GPa)
        nu_concrete=0.20,
        k_s=25000.0,        # kN/m^3 (medium-dense sand / firm clay)
    )
    # Self-weight of the raft: 25 kN/m^3 × 0.7 m = 17.5 kN/m^2
    mat.add_uniform_pressure(q=17.5)

    # 6 column loads (kN)
    columns = [
        # x [m], y [m], P [kN], name
        (2.0,  2.0,  900,  "P1"),
        (6.0,  2.0, 1100,  "P2"),
        (10.0, 2.0,  950,  "P3"),
        (2.0,  8.0,  920,  "P4"),
        (6.0,  8.0, 1150,  "P5"),
        (10.0, 8.0,  980,  "P6"),
    ]
    for x, y, P, name in columns:
        mat.add_column_load(x=x, y=y, P=P, name=name)
    return mat, columns


def main() -> None:
    mat, columns = build_solver()
    print("=" * 78)
    print(f"FoundationDesignJm - Mat foundation 12.0 x 10.0 x 0.70 m")
    print("=" * 78)
    print(f"Mesh: {mat.nx} x {mat.ny} elements ({mat.n_nodes} nodes, "
          f"{mat.n_dofs} DOFs)")
    print(f"k_s = {mat.k_s} kN/m3,  E = {mat.E/1e6:.0f} GPa")
    print()

    res = mat.solve(allow_uplift=True)
    print(f"Iterations: {res.iterations}   converged: {res.converged}   "
          f"uplift nodes: {len(res.uplift_nodes)}")
    print()
    print("Settlements at column points (positive = downwards):")
    print(f"{'Col':<6}{'x [m]':>8}{'y [m]':>8}{'P [kN]':>10}"
          f"{'w [mm]':>10}{'q_soil [kPa]':>14}")
    for x, y, P, name in columns:
        nid = mat.node_at(x, y)
        print(f"{name:<6}{x:>8.2f}{y:>8.2f}{P:>10.0f}"
              f"{res.w[nid]*1000:>10.2f}{res.q_soil[nid]:>14.2f}")

    print()
    print("Global settlement summary:")
    print(f"  w_max = {res.w_max*1000:.2f} mm")
    print(f"  w_min = {res.w_min*1000:.2f} mm")
    print(f"  differential = {res.differential_settlement_mm:.2f} mm")
    print()
    print("Soil pressure summary (active springs):")
    active_q = res.q_soil[res.q_soil > 0]
    print(f"  q_soil mean = {active_q.mean():.2f} kPa")
    print(f"  q_soil max  = {active_q.max():.2f} kPa")
    print()
    print("Element-centroid bending moments [kN.m/m]:")
    print(f"  M_xx  min = {res.M_xx.min():.1f}   max = {res.M_xx.max():.1f}")
    print(f"  M_yy  min = {res.M_yy.min():.1f}   max = {res.M_yy.max():.1f}")
    print(f"  M_xy  min = {res.M_xy.min():.1f}   max = {res.M_xy.max():.1f}")

    # Quick equilibrium check
    applied = sum(P for _, _, P, _ in columns) + 17.5 * 12.0 * 10.0
    reaction = 0.0
    for e in range(mat.n_elems):
        ids = mat.elements[e]
        coords_e = mat.nodes_xy[ids]
        Le = abs(coords_e[1, 0] - coords_e[0, 0])
        We = abs(coords_e[3, 1] - coords_e[0, 1])
        reaction += res.q_soil[ids].mean() * Le * We
    print()
    print(f"Global equilibrium check: applied = {applied:.1f} kN, "
          f"reaction = {reaction:.1f} kN  (error = "
          f"{(reaction - applied) / applied * 100:.2f} %)")

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------
    from foundationdesignjm.utils import (
        export_mat_to_json,
        export_mat_to_safe,
    )
    safe_path = export_mat_to_safe(
        mat, "out/mat_example.s2k", fck_MPa=30, model_name="MatExample",
    )
    json_path = export_mat_to_json(mat, res, "out/mat_example.json")
    print()
    print("Exports:")
    print(f"  SAFE  -> {safe_path}")
    print(f"  JSON  -> {json_path}")
    print("  (open the .s2k in CSI SAFE as the starting point for the model)")


if __name__ == "__main__":
    main()
