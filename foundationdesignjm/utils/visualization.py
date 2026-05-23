"""Plotly visualisation helpers for mat-foundation results.

Three field plots are provided:
- `plot_mat_deflection` — settlement contour (mm, +down).
- `plot_mat_pressure`   — soil contact pressure (kPa).
- `plot_mat_moments`    — element-centroid M_xx / M_yy heatmaps for armadura.

Each function returns a `plotly.graph_objects.Figure` so the caller can
`.show()` it, `.write_html(...)` it, or compose dashboards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..analysis.mat_foundation import MatFoundationSolver, MatResult


def _ensure_plotly():
    try:
        import plotly.graph_objects as go  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "plotly is required for visualization. Install with `pip install plotly`."
        ) from e


def _nodal_field_to_grid(solver, values_node):
    """Reshape a nodal field into a 2D grid (ny+1, nx+1) for contour plotting."""
    import numpy as np
    return np.asarray(values_node).reshape(solver.ny + 1, solver.nx + 1)


def _element_field_to_grid(solver, values_elem):
    """Reshape an element-centroid field into a 2D grid (ny, nx)."""
    import numpy as np
    return np.asarray(values_elem).reshape(solver.ny, solver.nx)


def plot_mat_deflection(
    solver: "MatFoundationSolver",
    result: "MatResult",
    title: str = "Settlement [mm]",
):
    """Contour plot of vertical settlement (+down) in mm."""
    _ensure_plotly()
    import numpy as np
    import plotly.graph_objects as go

    xs = np.linspace(0, solver.length, solver.nx + 1)
    ys = np.linspace(0, solver.width, solver.ny + 1)
    z = _nodal_field_to_grid(solver, result.w) * 1000.0

    fig = go.Figure(go.Contour(
        x=xs, y=ys, z=z,
        colorscale="RdBu_r",
        colorbar=dict(title="w [mm]"),
        contours=dict(showlabels=True),
        line=dict(width=0.5),
    ))
    _add_columns(fig, solver)
    fig.update_layout(
        title=title,
        xaxis_title="x [m]", yaxis_title="y [m]",
        yaxis=dict(scaleanchor="x", scaleratio=1),
    )
    return fig


def plot_mat_pressure(
    solver: "MatFoundationSolver",
    result: "MatResult",
    title: str = "Soil contact pressure [kPa]",
):
    """Contour plot of soil pressure (uplift areas appear as 0)."""
    _ensure_plotly()
    import numpy as np
    import plotly.graph_objects as go

    xs = np.linspace(0, solver.length, solver.nx + 1)
    ys = np.linspace(0, solver.width, solver.ny + 1)
    z = _nodal_field_to_grid(solver, result.q_soil)

    fig = go.Figure(go.Contour(
        x=xs, y=ys, z=z,
        colorscale="YlOrRd",
        colorbar=dict(title="q [kPa]"),
        contours=dict(showlabels=True),
        line=dict(width=0.5),
    ))
    _add_columns(fig, solver)
    fig.update_layout(
        title=title,
        xaxis_title="x [m]", yaxis_title="y [m]",
        yaxis=dict(scaleanchor="x", scaleratio=1),
    )
    return fig


def plot_mat_moments(
    solver: "MatFoundationSolver",
    result: "MatResult",
    direction: Literal["xx", "yy", "xy"] = "xx",
    title: str = None,
):
    """Element-centroid bending moment heatmap [kN.m/m]."""
    _ensure_plotly()
    import numpy as np
    import plotly.graph_objects as go

    if direction == "xx":
        vals, label = result.M_xx, "M_xx"
    elif direction == "yy":
        vals, label = result.M_yy, "M_yy"
    else:
        vals, label = result.M_xy, "M_xy"

    dx = solver.length / solver.nx
    dy = solver.width / solver.ny
    xs = np.linspace(dx / 2, solver.length - dx / 2, solver.nx)
    ys = np.linspace(dy / 2, solver.width - dy / 2, solver.ny)
    z = _element_field_to_grid(solver, vals)

    fig = go.Figure(go.Heatmap(
        x=xs, y=ys, z=z,
        colorscale="RdBu_r",
        zmid=0,
        colorbar=dict(title=f"{label} [kN.m/m]"),
    ))
    _add_columns(fig, solver)
    fig.update_layout(
        title=title or f"Bending moment {label} [kN.m/m]",
        xaxis_title="x [m]", yaxis_title="y [m]",
        yaxis=dict(scaleanchor="x", scaleratio=1),
    )
    return fig


def _add_columns(fig, solver):
    """Overlay the column positions as black dots labelled with the load."""
    import plotly.graph_objects as go

    xs = [c.x for c in solver._column_loads]
    ys = [c.y for c in solver._column_loads]
    labels = [c.name or f"{c.P:.0f} kN" for c in solver._column_loads]
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers+text",
        marker=dict(color="black", size=10, symbol="square"),
        text=labels,
        textposition="top center",
        showlegend=False,
        hovertemplate="x=%{x:.2f} m<br>y=%{y:.2f} m<br>%{text}<extra></extra>",
    ))
