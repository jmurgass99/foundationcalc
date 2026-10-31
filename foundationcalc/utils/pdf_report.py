"""Multi-page engineering PDF reports using only matplotlib.

The `PdfReportBuilder` class builds a complete A4 PDF using
`matplotlib.backends.backend_pdf.PdfPages`. It exposes high-level
primitives suitable for foundation-design reports:

- `cover_page(title, subtitle, ...)` — front page.
- `section(title, body_lines)`        — paragraph block.
- `table(headers, rows, title)`        — tabular data.
- `figure(fig, caption)`               — a matplotlib figure plus a caption.
- `verdict_box(label, value, ok)`      — coloured pass/fail badge.

Then `save()` flushes the file. Each page is rendered on an A4 sheet
with engineering-style header and footer (project, date, page X / N).

The companion helpers
- `report_retaining_wall`, `report_basement_wall`,
- `report_crane`, `report_mat_foundation`, `report_seismic_footing`
build complete reports for each designer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List, Optional, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")  # headless

from .._brand import NAME as _BRAND_NAME, SLUG as _BRAND_SLUG, TAGLINE as _BRAND_TAGLINE
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure


# A4 portrait dimensions in inches (matplotlib uses inches)
A4_WIDTH_IN = 8.27
A4_HEIGHT_IN = 11.69


@dataclass
class ReportMeta:
    project: str = "Foundation design"
    subtitle: str = ""
    engineer: str = ""
    client: str = ""
    date: str = field(default_factory=lambda: date.today().isoformat())
    job_code: str = ""
    units: str = "kN, m, kPa"


class PdfReportBuilder:
    """Compose an A4 PDF page by page using only matplotlib."""

    def __init__(self, output_path: str, meta: ReportMeta):
        self.output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)
        self.meta = meta
        self._pdf = PdfPages(self.output_path)
        self._page_no = 0
        self._page_buffer: List[Figure] = []

    # ------------------------------------------------------------------
    # Page primitives
    # ------------------------------------------------------------------
    def _new_page(self) -> Figure:
        self._page_no += 1
        fig = plt.figure(figsize=(A4_WIDTH_IN, A4_HEIGHT_IN))
        # Header band
        fig.text(0.07, 0.965, self.meta.project, fontsize=10, weight="bold")
        fig.text(0.93, 0.965, f"Page {self._page_no}", fontsize=9, ha="right")
        fig.add_artist(plt.Line2D([0.07, 0.93], [0.955, 0.955],
                                  transform=fig.transFigure, color="#1f497d", linewidth=1.2))
        # Footer band
        footer = f"{self.meta.engineer or _BRAND_NAME}  |  {self.meta.date}"
        if self.meta.job_code:
            footer = f"{self.meta.job_code}  |  " + footer
        fig.text(0.07, 0.035, footer, fontsize=8, color="#555555")
        fig.text(0.93, 0.035, f"Generated with {_BRAND_SLUG}",
                 fontsize=8, color="#555555", ha="right")
        fig.add_artist(plt.Line2D([0.07, 0.93], [0.05, 0.05],
                                  transform=fig.transFigure, color="#1f497d", linewidth=0.8))
        return fig

    def _close_page(self, fig: Figure) -> None:
        self._pdf.savefig(fig)
        plt.close(fig)

    # ------------------------------------------------------------------
    # High-level primitives
    # ------------------------------------------------------------------
    def cover_page(self, title: str, subtitle: str = "", extra_lines: Optional[Sequence[str]] = None) -> None:
        fig = self._new_page()
        fig.text(0.5, 0.78, title, ha="center", fontsize=22, weight="bold")
        if subtitle:
            fig.text(0.5, 0.72, subtitle, ha="center", fontsize=14, style="italic", color="#1f497d")

        # Meta box
        meta_lines = [
            f"Project:  {self.meta.project}",
            f"Client:   {self.meta.client}",
            f"Engineer: {self.meta.engineer}",
            f"Date:     {self.meta.date}",
            f"Job:      {self.meta.job_code}",
            f"Units:    {self.meta.units}",
        ]
        for i, line in enumerate(meta_lines):
            fig.text(0.20, 0.55 - 0.04 * i, line, fontsize=12, family="monospace")

        if extra_lines:
            for i, line in enumerate(extra_lines):
                fig.text(0.20, 0.28 - 0.035 * i, line, fontsize=10)

        fig.text(0.5, 0.10, f"{_BRAND_NAME}  -  {_BRAND_TAGLINE}",
                 ha="center", fontsize=9, color="#888888")
        self._close_page(fig)

    def section(
        self,
        title: str,
        body_lines: Optional[Sequence[str]] = None,
        title_y: float = 0.92,
    ) -> Figure:
        """Open a section page. Body lines are written below the title.

        Returns the open page so the caller can place additional artists
        (e.g. a figure axes) on it before another section/figure call.
        """
        fig = self._new_page()
        fig.text(0.07, title_y, title, fontsize=15, weight="bold", color="#1f497d")
        if body_lines:
            for i, line in enumerate(body_lines):
                fig.text(0.07, title_y - 0.03 - 0.025 * i, line, fontsize=10)
        return fig

    def add_text(self, fig: Figure, x: float, y: float, text: str, **kwargs) -> None:
        fig.text(x, y, text, **kwargs)

    def add_table(
        self,
        fig: Figure,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        x: float = 0.07, y: float = 0.50, width: float = 0.86, row_height: float = 0.04,
        col_widths: Optional[Sequence[float]] = None,
    ) -> None:
        """Add a simple table on the page at (x, y).

        col_widths must sum to ~1.0 (fractions of `width`).
        """
        n_cols = len(headers)
        if col_widths is None:
            col_widths = [1.0 / n_cols] * n_cols
        # Header band
        head_y = y
        x_left = x
        # Build x positions
        x_positions = [x_left]
        for w in col_widths:
            x_positions.append(x_positions[-1] + w * width)

        # Header background
        fig.patches.append(plt.Rectangle((x_left, head_y - row_height * 0.7),
                                         width, row_height,
                                         transform=fig.transFigure,
                                         facecolor="#1f497d", edgecolor="none"))
        for i, h in enumerate(headers):
            xc = (x_positions[i] + x_positions[i + 1]) / 2
            fig.text(xc, head_y - row_height * 0.25, str(h),
                     ha="center", va="center", fontsize=9, color="white", weight="bold")
        # Rows
        for r_idx, row in enumerate(rows):
            y_row = head_y - row_height * (r_idx + 1)
            bg = "#f5f5f5" if r_idx % 2 == 0 else "#ffffff"
            fig.patches.append(plt.Rectangle((x_left, y_row - row_height * 0.7),
                                             width, row_height,
                                             transform=fig.transFigure,
                                             facecolor=bg, edgecolor="#dddddd", linewidth=0.4))
            for i, cell in enumerate(row):
                xc = (x_positions[i] + x_positions[i + 1]) / 2
                fig.text(xc, y_row - row_height * 0.25, str(cell),
                         ha="center", va="center", fontsize=9, color="#222222")

    def add_verdict(self, fig: Figure, x: float, y: float, label: str, ok: bool,
                    width: float = 0.22, height: float = 0.05) -> None:
        color = "#1b8a3a" if ok else "#b00020"
        fig.patches.append(plt.Rectangle((x, y - height / 2), width, height,
                                         transform=fig.transFigure,
                                         facecolor=color, edgecolor="none", alpha=0.85))
        fig.text(x + width / 2, y, ("OK   " if ok else "FAIL ") + label,
                 ha="center", va="center", fontsize=11, color="white", weight="bold")

    def add_figure(
        self,
        fig: Figure,
        rect: Tuple[float, float, float, float],
        plotter,
        caption: Optional[str] = None,
    ) -> None:
        """Embed a matplotlib plot in the current page within `rect = (x, y, w, h)`.

        `plotter` is a callable that receives a matplotlib Axes and draws on it.
        """
        ax = fig.add_axes(list(rect))
        plotter(ax)
        if caption:
            fig.text(rect[0] + rect[2] / 2, rect[1] - 0.025, caption,
                     ha="center", fontsize=9, style="italic")

    def close_page(self, fig: Figure) -> None:
        """Finalise the page and write to PDF."""
        self._close_page(fig)

    def save(self) -> str:
        """Flush and close the PDF file. Returns the absolute path."""
        self._pdf.close()
        return self.output_path


# ---------------------------------------------------------------------------
# Report templates — one per designer
# ---------------------------------------------------------------------------

def _fmt(x: float, ndp: int = 2) -> str:
    return f"{x:,.{ndp}f}".replace(",", " ") if abs(x) >= 1000 else f"{x:.{ndp}f}"


def report_retaining_wall(
    designer,
    result,
    output_path: str,
    meta: Optional[ReportMeta] = None,
) -> str:
    """Generate a complete retaining-wall design report PDF."""
    if meta is None:
        meta = ReportMeta(project="Cantilever retaining wall design")
    builder = PdfReportBuilder(output_path, meta)

    g = designer.geo
    builder.cover_page(
        "Cantilever retaining wall",
        f"H = {g.H} m,  B = {g.B} m,  base = {g.base_thickness} m",
        extra_lines=[
            f"Backfill: phi = {designer.load.backfill.friction_angle} deg, "
            f"gamma = {designer.load.backfill.unit_weight} kN/m3",
            f"Surcharge:  q = {designer.load.surcharge_q} kN/m2",
            f"Water:      H_w = {designer.load.water_height} m",
            f"Method: Coulomb"
            if designer.load.use_coulomb
            else "Method: Rankine",
            f"Design approach: {result.design_approach}",
        ],
    )

    # ----- ULS summary page ---------------------------------------------------
    fig = builder.section(
        "1. Ultimate-limit-state checks",
        [
            f"Total vertical action  V_d = {_fmt(result.actions.V_d)} kN/m",
            f"Total horizontal H_d = {_fmt(result.actions.H_d)} kN/m",
            f"Eccentricity e_x = {_fmt(result.actions.e_x, 3)} m  "
            f"(B/6 = {_fmt(g.B / 6.0, 3)} m)",
            f"Middle-third: {'YES' if result.middle_third else 'NO'}",
        ],
        title_y=0.92,
    )

    headers = ["Check", "E_d", "R_d", "Utilization", "Status"]
    rows = [
        ["Bearing", _fmt(result.bearing_q_Ed),
         _fmt(result.bearing_q_Rd),
         f"{result.bearing_utilization * 100:.1f} %",
         "OK" if result.bearing_utilization <= 1.0 else "FAIL"],
        ["Sliding", _fmt(result.sliding_H_Ed),
         _fmt(result.sliding_H_Rd),
         f"{result.sliding_utilization * 100:.1f} %",
         "OK" if result.sliding_utilization <= 1.0 else "FAIL"],
        ["Overturning", _fmt(result.actions.M_dst),
         _fmt(result.actions.M_stb),
         f"{result.overturning_utilization * 100:.1f} %",
         "OK" if result.overturning_utilization <= 1.0 else "FAIL"],
    ]
    builder.add_table(fig, headers, rows, x=0.07, y=0.78, width=0.86)

    builder.add_verdict(fig, x=0.39, y=0.55, label="Overall ULS", ok=result.all_ok)

    # Geometry sketch
    def _sketch(ax):
        ax.set_aspect("equal")
        toe, sb, heel = g.toe, g.stem_bottom, g.heel
        H, t = g.H, g.base_thickness
        # base slab
        ax.fill([0, g.B, g.B, 0], [0, 0, t, t], color="#cccccc")
        # stem (taper)
        x0 = toe
        x1 = toe + sb
        ax.fill([x0, x1, x1 - (sb - g.stem_top), x0 + (sb - g.stem_top) / 2],
                [t, t, t + H, t + H], color="#bbbbbb")
        # backfill arrow
        ax.annotate("", xy=(g.B + 0.3, t + H / 2), xytext=(g.B, t + H / 2),
                    arrowprops=dict(arrowstyle="->", color="#b00020"))
        ax.text(g.B + 0.3, t + H / 2, "active thrust", fontsize=8, color="#b00020")
        ax.set_xlim(-0.5, g.B + 1.5)
        ax.set_ylim(-0.5, t + H + 0.5)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title("Wall geometry")
        ax.grid(True, alpha=0.3)

    builder.add_figure(fig, rect=(0.10, 0.10, 0.80, 0.35), plotter=_sketch,
                       caption="Wall cross-section (per metre run)")
    builder.close_page(fig)

    # ----- Structural sections ----------------------------------------------
    fig = builder.section(
        "2. Structural critical-section forces (per m run)",
        [
            "Bending moments and shears for EC2 design of the stem, heel and toe.",
        ],
        title_y=0.92,
    )
    rows = [
        ["Stem base", f"M = {_fmt(result.M_stem_base)} kN.m/m",
         f"V = {_fmt(result.V_stem_base)} kN/m"],
        ["Heel", f"M = {_fmt(result.M_heel)} kN.m/m",
         f"V = {_fmt(result.V_heel)} kN/m"],
        ["Toe", f"M = {_fmt(result.M_toe)} kN.m/m",
         f"V = {_fmt(result.V_toe)} kN/m"],
    ]
    builder.add_table(
        fig, ["Section", "Bending", "Shear"], rows,
        x=0.07, y=0.78, width=0.86, col_widths=[0.30, 0.35, 0.35],
    )

    # Moment/shear bar plot
    def _bars(ax):
        labels = ["Stem", "Heel", "Toe"]
        Ms = [result.M_stem_base, result.M_heel, result.M_toe]
        ax.bar(labels, Ms, color=["#1f497d", "#1b8a3a", "#b00020"])
        ax.set_ylabel("M [kN.m/m]")
        ax.set_title("Critical-section bending")
        ax.grid(True, axis="y", alpha=0.3)
        for i, v in enumerate(Ms):
            ax.text(i, v, _fmt(v), ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8)

    builder.add_figure(fig, rect=(0.10, 0.18, 0.80, 0.45), plotter=_bars,
                       caption="Critical-section moments for stem / heel / toe")
    builder.close_page(fig)
    return builder.save()


def report_basement_wall(
    designer,
    result,
    output_path: str,
    meta: Optional[ReportMeta] = None,
) -> str:
    if meta is None:
        meta = ReportMeta(project="Basement wall design")
    builder = PdfReportBuilder(output_path, meta)

    g = designer.geo
    load = designer.load
    builder.cover_page(
        "Basement wall",
        f"H = {g.height} m,  t = {g.thickness} m,  {designer.support.value}",
        extra_lines=[
            f"Backfill: phi = {load.phi_deg} deg, gamma = {load.gamma_soil} kN/m3",
            f"Surcharge q = {load.surcharge_q} kN/m2,  water H_w = {load.water_height} m",
            f"N_min = {load.N_min_kN_per_m} kN/m,  N_max = {load.N_max_kN_per_m} kN/m",
            f"Pressure diagram: {designer.pressure.value}",
            f"K_0 = {result.K0:.3f}",
        ],
    )

    fig = builder.section(
        "1. Pressure diagram and reactions",
        [
            f"q_top  = {_fmt(result.q_top_kPa)} kPa,    "
            f"q_base = {_fmt(result.q_base_kPa)} kPa",
            f"Reaction at top   T_top  = {_fmt(result.R_top_kN_per_m)} kN/m",
            f"Reaction at base  T_base = {_fmt(result.R_base_kN_per_m)} kN/m",
            f"Maximum shear     V_max  = {_fmt(result.V_max_kN)} kN/m",
        ],
        title_y=0.92,
    )

    # Plot pressure diagram + bending diagram
    def _pressure(ax):
        # q(z) varies linearly from q_top at z=0 to q_base at z=H
        zs = result.z
        H = g.height
        qs = [result.q_top_kPa + (result.q_base_kPa - result.q_top_kPa) * z / H
              for z in zs]
        ax.barh(zs, qs, height=H / len(zs) * 0.95, color="#1f497d", alpha=0.6)
        ax.set_xlabel("Pressure [kPa]")
        ax.set_ylabel("Depth z from top [m]")
        ax.set_title("Lateral pressure")
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)

    def _moments(ax):
        ax.plot(result.M_envelope_outer, result.z, "r-", lw=1.6, label="Outer face")
        ax.plot(result.M_envelope_inner, result.z, "b-", lw=1.6, label="Inner face")
        ax.axvline(0, color="black", lw=0.6)
        ax.fill_betweenx(result.z, result.M_envelope_outer, 0, color="r", alpha=0.15)
        ax.fill_betweenx(result.z, result.M_envelope_inner, 0, color="b", alpha=0.15)
        ax.set_xlabel("M [kN.m/m]")
        ax.set_ylabel("Depth z [m]")
        ax.set_title("Bending envelope")
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=8)

    builder.add_figure(fig, rect=(0.10, 0.45, 0.36, 0.40), plotter=_pressure)
    builder.add_figure(fig, rect=(0.55, 0.45, 0.36, 0.40), plotter=_moments)

    builder.add_table(
        fig,
        ["Section", "M [kNm/m]", "z [m]"],
        [
            ["M_inner max (sagging)", _fmt(result.M_inner_max_kNm),
             _fmt(result.z_of_M_inner_max_m, 2)],
            ["M_outer max (hogging)", _fmt(result.M_outer_max_kNm),
             _fmt(result.z_of_M_outer_max_m, 2)],
            ["2nd-order at base", _fmt(result.second_order_M_base_kNm), f"{g.height:.2f}"],
        ],
        x=0.07, y=0.36, width=0.86,
    )
    builder.close_page(fig)
    return builder.save()


def report_crane(
    results: Iterable,
    output_path: str,
    meta: Optional[ReportMeta] = None,
) -> str:
    if meta is None:
        meta = ReportMeta(project="Tower-crane foundation design")
    builder = PdfReportBuilder(output_path, meta)
    builder.cover_page(
        "Tower-crane foundation",
        "Bearing / sliding / overturning checks per Eurocode 7",
    )

    fig = builder.section(
        "ULS envelope by load case and design approach",
        [
            "Each row is a (load case x DA) combination. Maximum",
            "utilization across rows governs the design.",
        ],
    )
    results_list = list(results)
    rows = []
    for r in results_list:
        rows.append([
            r.load_case, r.design_approach,
            f"{r.bearing_utilization*100:>5.1f} %",
            f"{r.sliding_utilization*100:>5.1f} %",
            f"{r.overturning_utilization*100:>5.1f} %",
            r.regime,
            "OK" if r.all_ok else "FAIL",
        ])
    builder.add_table(
        fig,
        ["Load case", "DA", "Bearing", "Sliding", "Overturning", "Regime", "Status"],
        rows,
        x=0.04, y=0.78, width=0.92,
        col_widths=[0.18, 0.10, 0.13, 0.13, 0.16, 0.18, 0.12],
    )
    all_ok = all(r.all_ok for r in results_list)
    builder.add_verdict(fig, x=0.39, y=0.30, label="Overall ULS", ok=all_ok)
    builder.close_page(fig)
    return builder.save()


def report_mat_foundation(
    solver,
    result,
    output_path: str,
    meta: Optional[ReportMeta] = None,
) -> str:
    if meta is None:
        meta = ReportMeta(project="Mat / raft foundation analysis")
    builder = PdfReportBuilder(output_path, meta)
    builder.cover_page(
        "Mat foundation",
        f"{solver.length} x {solver.width} m, t = {solver.thickness} m",
        extra_lines=[
            f"Mesh: {solver.nx} x {solver.ny} elements ({solver.n_nodes} nodes)",
            f"k_s = {solver.k_s} kN/m3,  E = {solver.E/1e6:.0f} GPa",
            f"Iterations: {result.iterations}, "
            f"uplift nodes: {len(result.uplift_nodes)}",
        ],
    )

    # Settlement contour
    fig = builder.section("1. Settlement contour", title_y=0.92)
    import numpy as np

    def _settle(ax):
        xs = np.linspace(0, solver.length, solver.nx + 1)
        ys = np.linspace(0, solver.width, solver.ny + 1)
        z = (result.w * 1000.0).reshape(solver.ny + 1, solver.nx + 1)
        c = ax.contourf(xs, ys, z, levels=20, cmap="RdBu_r")
        plt.colorbar(c, ax=ax, label="w [mm]")
        # Overlay columns
        for cl in solver._column_loads:
            ax.scatter(cl.x, cl.y, c="black", s=40, marker="s")
            ax.text(cl.x, cl.y + 0.15, cl.name or f"{cl.P:.0f}", fontsize=8,
                    ha="center")
        ax.set_aspect("equal")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title("Settlement [mm]")

    builder.add_figure(fig, rect=(0.10, 0.30, 0.80, 0.55), plotter=_settle)

    # Add summary table at the top
    builder.add_table(
        fig,
        ["Quantity", "Value"],
        [
            ["w_max [mm]", _fmt(result.w_max * 1000)],
            ["w_min [mm]", _fmt(result.w_min * 1000)],
            ["Differential [mm]", _fmt(result.differential_settlement_mm)],
            ["M_xx max [kN.m/m]", _fmt(float(result.M_xx.max()))],
            ["M_yy max [kN.m/m]", _fmt(float(result.M_yy.max()))],
            ["Iterations", str(result.iterations)],
        ],
        x=0.20, y=0.86, width=0.60,
    )
    builder.close_page(fig)

    # Soil pressure contour
    fig = builder.section("2. Soil contact pressure", title_y=0.92)

    def _pressure(ax):
        xs = np.linspace(0, solver.length, solver.nx + 1)
        ys = np.linspace(0, solver.width, solver.ny + 1)
        q = result.q_soil.reshape(solver.ny + 1, solver.nx + 1)
        c = ax.contourf(xs, ys, q, levels=20, cmap="YlOrRd")
        plt.colorbar(c, ax=ax, label="q [kPa]")
        for cl in solver._column_loads:
            ax.scatter(cl.x, cl.y, c="black", s=40, marker="s")
        ax.set_aspect("equal")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title("Soil pressure [kPa]")

    builder.add_figure(fig, rect=(0.10, 0.30, 0.80, 0.55), plotter=_pressure)
    builder.close_page(fig)
    return builder.save()


def report_seismic_footing(
    result,
    output_path: str,
    meta: Optional[ReportMeta] = None,
) -> str:
    if meta is None:
        meta = ReportMeta(project="Seismic footing check (EN 1998-5)")
    builder = PdfReportBuilder(output_path, meta)
    builder.cover_page(
        "Spread footing - seismic check",
        f"Design approach: {result.design_approach}",
        extra_lines=[
            f"N = {_fmt(result.N_d)} kN,  H = {_fmt(result.H_d)} kN,  M = {_fmt(result.M_d)} kN.m",
            f"Eccentricities: e_x = {_fmt(result.e_x, 3)} m,  e_y = {_fmt(result.e_y, 3)} m",
            f"Regime: {result.regime}",
        ],
    )
    fig = builder.section("ULS checks", title_y=0.92)
    rows = [
        ["Bearing", _fmt(result.bearing_q_Ed), _fmt(result.bearing_q_Rd),
         f"{result.bearing_utilization * 100:.1f} %",
         "OK" if result.bearing_utilization <= 1.0 else "FAIL"],
        ["Sliding", _fmt(result.sliding_H_Ed), _fmt(result.sliding_H_Rd),
         f"{result.sliding_utilization * 100:.1f} %",
         "OK" if result.sliding_utilization <= 1.0 else "FAIL"],
        ["Overturning", _fmt(result.overturning_M_dst), _fmt(result.overturning_M_stb),
         f"{result.overturning_utilization * 100:.1f} %",
         "OK" if result.overturning_utilization <= 1.0 else "FAIL"],
    ]
    builder.add_table(fig, ["Check", "E_d", "R_d", "Utilization", "Status"], rows,
                      x=0.07, y=0.78, width=0.86)
    builder.add_verdict(fig, x=0.39, y=0.50, label="Overall seismic ULS",
                        ok=result.all_ok)
    builder.close_page(fig)
    return builder.save()


def report_cpt_to_design(
    cpt,
    foundation,
    result,
    output_path: str,
    meta: Optional[ReportMeta] = None,
) -> str:
    """Generate a full end-to-end report for a CPT-to-design pipeline.

    Pages:
      1. Cover with project, footing, applied pressure.
      2. CPT log (q_c, f_s, R_f vs depth) + auto-stratification table.
      3. Bearing capacity (multi-layer summary) + failure mode.
      4. Settlement breakdown per sub-layer + verdict.
    """
    if meta is None:
        meta = ReportMeta(project="CPT-based footing design")
    builder = PdfReportBuilder(output_path, meta)
    import numpy as np

    # ----- Cover -------------------------------------------------------
    builder.cover_page(
        "End-to-end footing design from CPT",
        f"Footing {foundation.width_m} x {foundation.length_m} m  "
        f"@ D = {result.profile.layers[0].thickness:.1f} m+",
        extra_lines=[
            f"CPT log:       {len(cpt.readings)} readings, depth "
            f"{cpt.readings[0].depth} to {cpt.readings[-1].depth} m",
            f"Water table:   {cpt.water_table_depth_m} m below surface",
            f"Applied q_Ed:  {result.q_applied_kPa:.1f} kPa",
            f"Design app.:   {result.design_approach}",
            f"Verdict:       Bearing {'OK' if result.bearing_ok else 'FAIL'}  /  "
            f"Settlement {'OK' if result.settlement_ok else 'EXCEEDS'}",
        ],
    )

    # ----- CPT log + stratification -----------------------------------
    fig = builder.section(
        "1. CPT log and derived stratification", title_y=0.92,
    )
    depths = [r.depth for r in cpt.readings]
    qc = [r.q_c_MPa for r in cpt.readings]
    fs = [r.f_s_kPa for r in cpt.readings]

    def _qc_plot(ax):
        ax.plot(qc, depths, "b-", lw=1.4)
        ax.set_xlabel("q_c [MPa]")
        ax.set_ylabel("Depth [m]")
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)
        ax.set_title("Cone resistance")
        # Water table line
        ax.axhline(cpt.water_table_depth_m, color="cyan", lw=1.2,
                   linestyle="--", label="WT")
        ax.legend(fontsize=8)

    def _fs_plot(ax):
        ax.plot(fs, depths, "g-", lw=1.4)
        ax.set_xlabel("f_s [kPa]")
        ax.set_ylabel("Depth [m]")
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)
        ax.set_title("Sleeve friction")

    builder.add_figure(fig, rect=(0.07, 0.40, 0.40, 0.45), plotter=_qc_plot)
    builder.add_figure(fig, rect=(0.55, 0.40, 0.40, 0.45), plotter=_fs_plot)

    # Stratification table
    rows = []
    for L in result.profile.layers:
        params = []
        if L.friction_angle and L.friction_angle > 0:
            params.append(f"phi={L.friction_angle:.1f}deg")
        if L.undrained_shear_strength:
            params.append(f"c_u={L.undrained_shear_strength:.0f} kPa")
        if L.youngs_modulus:
            params.append(f"E={L.youngs_modulus:.0f} MPa")
        rows.append([
            L.name, L.soil_type.value, f"{L.thickness:.2f}",
            ", ".join(params),
        ])
    builder.add_table(
        fig,
        ["Layer", "Type", "Thickness [m]", "Derived parameters"],
        rows,
        x=0.07, y=0.30, width=0.86,
        col_widths=[0.27, 0.18, 0.15, 0.40],
    )
    builder.close_page(fig)

    # ----- Bearing capacity -------------------------------------------
    fig = builder.section(
        "2. Bearing capacity (multi-layer + failure mode)",
        [
            f"Governing case:  {result.bearing.governing_case}",
            f"Governing layer: {result.bearing.governing_layer}",
            f"Layers in influence zone (2B): "
            + ", ".join(result.bearing.layers_in_influence),
        ],
        title_y=0.92,
    )

    rows = [
        ["q_applied (E_d)", _fmt(result.q_applied_kPa) + " kPa"],
        ["q_ult (characteristic)", _fmt(result.bearing.q_ult_kPa) + " kPa"],
        ["q_Rd (with gamma_Rv + Vesic)", _fmt(result.q_Rd_kPa) + " kPa"],
        ["Utilization", f"{result.bearing_utilization * 100:.1f} %"],
        ["Status", "OK" if result.bearing_ok else "FAIL"],
    ]
    builder.add_table(
        fig, ["Quantity", "Value"], rows,
        x=0.20, y=0.75, width=0.60, col_widths=[0.6, 0.4],
    )

    # Failure mode summary
    fm_rows = [
        ["Mode", result.failure_mode.mode.value],
        ["I_r (rigidity index)", _fmt(result.failure_mode.I_r, 1)],
        ["I_rc (critical)", _fmt(result.failure_mode.I_rc, 1)],
        ["zeta_q (reduction)", _fmt(result.failure_mode.zeta_q, 3)],
        ["zeta_c", _fmt(result.failure_mode.zeta_c, 3)],
        ["zeta_gamma", _fmt(result.failure_mode.zeta_gamma, 3)],
    ]
    builder.add_table(
        fig, ["Vesic (1973)", "Value"], fm_rows,
        x=0.20, y=0.45, width=0.60, col_widths=[0.6, 0.4],
    )
    builder.add_verdict(
        fig, x=0.39, y=0.15,
        label="Bearing ULS",
        ok=result.bearing_ok,
    )
    builder.close_page(fig)

    # ----- Settlement -------------------------------------------------
    fig = builder.section(
        "3. Settlement (Boussinesq + Terzaghi)",
        [
            f"Immediate (elastic): {result.settlement.s_immediate_mm:.1f} mm",
            f"Consolidation:       {result.settlement.s_consolidation_mm:.1f} mm",
            f"TOTAL:               {result.settlement.s_total_mm:.1f} mm   "
            f"(SLS limit {result.settlement_limit_mm:.0f} mm)",
        ],
        title_y=0.92,
    )

    # Plot stress increment and settlement per sub-layer
    sub = result.settlement.sublayers
    if sub:
        z_mid = [0.5 * (s["z_top"] + s["z_bot"]) for s in sub]
        dsig = [s["delta_sigma_kPa"] for s in sub]
        ss = [s["s_immediate_mm"] + s["s_consolidation_mm"] for s in sub]

        def _stress(ax):
            ax.barh(z_mid, dsig, height=0.4, color="#1f497d")
            ax.set_xlabel("Delta sigma_z [kPa]")
            ax.set_ylabel("Depth [m]")
            ax.invert_yaxis()
            ax.set_title("Stress increment (Boussinesq)")
            ax.grid(True, axis="x", alpha=0.3)

        def _settle(ax):
            ax.barh(z_mid, ss, height=0.4, color="#b00020")
            ax.set_xlabel("Sub-layer settlement [mm]")
            ax.set_ylabel("Depth [m]")
            ax.invert_yaxis()
            ax.set_title("Settlement by sub-layer")
            ax.grid(True, axis="x", alpha=0.3)

        builder.add_figure(fig, rect=(0.07, 0.30, 0.40, 0.50), plotter=_stress)
        builder.add_figure(fig, rect=(0.55, 0.30, 0.40, 0.50), plotter=_settle)

    builder.add_verdict(
        fig, x=0.39, y=0.10,
        label="Settlement SLS",
        ok=result.settlement_ok,
    )
    builder.close_page(fig)

    return builder.save()


__all__ = [
    "ReportMeta",
    "PdfReportBuilder",
    "report_retaining_wall",
    "report_basement_wall",
    "report_crane",
    "report_mat_foundation",
    "report_seismic_footing",
    "report_cpt_to_design",
]
