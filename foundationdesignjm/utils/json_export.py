"""Export `MatResult` to a self-describing JSON for downstream processing."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..analysis.mat_foundation import MatFoundationSolver, MatResult


def export_mat_to_json(
    solver: "MatFoundationSolver",
    result: "MatResult",
    output_path: str,
) -> str:
    """Dump mesh, loads and results to a single JSON file.

    Schema:
        meta: dimensions, mesh size, material, k_s, units
        mesh: node coordinates and element connectivity
        loads: column loads and uniform pressure
        results: w, theta_x, theta_y, q_soil at every node; M_xx, M_yy,
                 M_xy at every element centroid; uplift_nodes list.
    """
    output_path = os.path.abspath(output_path)
    payload = {
        "meta": {
            "length_m": solver.length,
            "width_m": solver.width,
            "thickness_m": solver.thickness,
            "nx": solver.nx,
            "ny": solver.ny,
            "E_concrete_kN_m2": solver.E,
            "nu_concrete": solver.nu,
            "k_s_kN_m3": solver.k_s,
            "units": {
                "length": "m",
                "force": "kN",
                "stress": "kN/m^2",
                "rotation": "rad",
            },
        },
        "mesh": {
            "nodes_xy": solver.nodes_xy.tolist(),
            "elements": solver.elements.tolist(),
        },
        "loads": {
            "uniform_pressure_kN_m2": solver._uniform_pressure,
            "columns": [
                {
                    "x_m": c.x, "y_m": c.y,
                    "P_kN": c.P, "Mx_kNm": c.Mx, "My_kNm": c.My,
                    "name": c.name,
                }
                for c in solver._column_loads
            ],
        },
        "results": {
            "iterations": result.iterations,
            "converged": result.converged,
            "w_mm": (result.w * 1000.0).tolist(),
            "theta_x_rad": result.theta_x.tolist(),
            "theta_y_rad": result.theta_y.tolist(),
            "q_soil_kN_m2": result.q_soil.tolist(),
            "M_xx_kNm_per_m": result.M_xx.tolist(),
            "M_yy_kNm_per_m": result.M_yy.tolist(),
            "M_xy_kNm_per_m": result.M_xy.tolist(),
            "uplift_nodes": [int(n) for n in result.uplift_nodes],
            "w_max_mm": result.w_max * 1000.0,
            "w_min_mm": result.w_min * 1000.0,
            "differential_settlement_mm": result.differential_settlement_mm,
        },
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return output_path
