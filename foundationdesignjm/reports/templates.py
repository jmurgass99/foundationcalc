"""Prebuilt report templates for common FastSAP outputs.

Each function consumes the typed result of an existing FastSAP analysis
(drift audit, section analysis, audit findings) and produces a complete
PDF on disk. All templates use :class:`Report` under the hood.
"""
from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from .pdf_builder import Report


# ---------------------------------------------------------------------------
# Section design report (consumes Phase 2 SectionAnalysis)
# ---------------------------------------------------------------------------

def build_section_report(analysis, path: str,
                          *,
                          section_name: str = "Section",
                          project: str = "",
                          author: str = "") -> str:
    """Render a one-pager with all geometric/mechanical section properties."""
    p = analysis.props
    rep = Report(
        title="Section Properties",
        subtitle=section_name,
        project=project, author=author,
    )
    rep.add_section("Geometry")
    rep.add_kv_table([
        ("Area A",                   f"{p.A:.4g}"),
        ("Centroid (cx, cy)",        f"({p.cx:.4g}, {p.cy:.4g})"),
        ("Bounding box x",           f"[{p.x_min:.4g}, {p.x_max:.4g}]"),
        ("Bounding box y",           f"[{p.y_min:.4g}, {p.y_max:.4g}]"),
    ])
    rep.add_section("Bending properties (centroidal axes)")
    rep.add_kv_table([
        ("Ix",                       p.Ix),
        ("Iy",                       p.Iy),
        ("Ixy",                      p.Ixy),
        ("rx",                       p.rx),
        ("ry",                       p.ry),
        ("Sx (min)",                 p.Sx),
        ("Sy (min)",                 p.Sy),
        ("Zx",                       p.Zx),
        ("Zy",                       p.Zy),
    ])
    rep.add_section("Principal axes")
    rep.add_kv_table([
        ("I1 (major)",               p.I1),
        ("I2 (minor)",               p.I2),
        ("θ from X (deg)",           f"{p.theta_principal_deg:.4g}"),
    ])
    rep.add_section("Torsion")
    rep.add_kv_table([
        ("J",                        analysis.torsion.J),
        ("Method",                   analysis.torsion.method),
        ("Notes",                    analysis.torsion.warning or "—"),
    ])
    return rep.save(path)


# ---------------------------------------------------------------------------
# Drift report (consumes a pandas DataFrame from extractor + audit)
# ---------------------------------------------------------------------------

def build_drift_report(drift_df: pd.DataFrame, path: str,
                        *,
                        project: str = "",
                        author: str = "",
                        code_name: str = "EC8",
                        limit_ratio: float = 0.0050) -> str:
    """Render a story-by-story drift compliance table.

    The DataFrame must contain columns ``story``, ``h_story_m``,
    ``drift_ratio`` (Δ/h) and optionally ``utilization`` (drift/limit).
    """
    rep = Report(
        title="Drift Compliance Report",
        subtitle=f"Code: {code_name} — limit Δ/h = {limit_ratio:g}",
        project=project, author=author,
    )
    rep.add_section("Summary")
    if "drift_ratio" in drift_df.columns:
        worst = drift_df["drift_ratio"].abs().max()
        rep.add_kv_table([
            ("Worst drift ratio",   f"{worst:.4g}"),
            ("Limit",               f"{limit_ratio:g}"),
            ("Status",              "OK" if worst <= limit_ratio else "OVER LIMIT"),
        ])
    rep.add_section("Story-by-story")
    rep.add_dataframe(drift_df, caption="Drift ratios per story.")
    return rep.save(path)


# ---------------------------------------------------------------------------
# Generic audit report (consumes a list of AuditFinding-like records)
# ---------------------------------------------------------------------------

def build_audit_report(findings: Iterable[Any], path: str,
                        *,
                        project: str = "",
                        author: str = "",
                        title: str = "Structural Audit") -> str:
    """Render an audit-findings PDF.

    `findings` is any iterable of objects with the attributes
    ``rule_id``, ``severity``, ``object_name``, ``message`` (the
    :class:`fastsap.audit.AuditFinding` dataclass).
    """
    rows = []
    for f in findings:
        rows.append({
            "rule": getattr(f, "rule_id", getattr(f, "id", "?")),
            "severity": getattr(f, "severity", "?"),
            "object": getattr(f, "object_name", ""),
            "message": getattr(f, "message", str(f)),
        })
    df = pd.DataFrame(rows)
    rep = Report(title=title, project=project, author=author)
    rep.add_section("Findings")
    if df.empty:
        rep.add_paragraph("No findings recorded.")
    else:
        n_err = (df["severity"] == "ERROR").sum() if "severity" in df else 0
        n_warn = (df["severity"] == "WARN").sum() if "severity" in df else 0
        rep.add_kv_table([("Total", len(df)),
                          ("ERROR", int(n_err)),
                          ("WARN", int(n_warn))])
        rep.add_dataframe(df)
    return rep.save(path)


# ---------------------------------------------------------------------------
# Steel-design report (consumes Phase 4 AISC results)
# ---------------------------------------------------------------------------

def build_steel_design_report(*,
                               shape,
                               flexure,
                               shear,
                               column=None,
                               interaction=None,
                               Fy: float,
                               path: str,
                               project: str = "",
                               author: str = "") -> str:
    """Render an AISC 360 design summary for a single member.

    Inputs are the typed results returned by :pyfunc:`design_beam_flexure`,
    :pyfunc:`design_beam_shear`, :pyfunc:`design_column` and
    :pyfunc:`interaction_H1`. Pass ``column`` and ``interaction`` only
    when the member also has axial demand.
    """
    rep = Report(
        title="Steel Member Design",
        subtitle=f"{shape.name} — AISC 360-22 LRFD",
        project=project, author=author,
    )
    rep.add_section("Section properties")
    rep.add_kv_table([
        ("Name",          shape.name),
        ("A",             shape.A),
        ("d",             shape.d),
        ("bf, tf",        f"{shape.bf} × {shape.tf}"),
        ("tw",            shape.tw),
        ("Ix, Iy",        f"{shape.Ix:.3e}, {shape.Iy:.3e}"),
        ("Zx, Sx",        f"{shape.Zx:.3e}, {shape.Sx:.3e}"),
        ("rx, ry",        f"{shape.rx:.3g}, {shape.ry:.3g}"),
        ("J, Cw",         f"{shape.J:.3e}, {shape.Cw:.3e}"),
        ("Fy",            Fy),
    ])

    rep.add_section("Flexure (§F2)")
    rep.add_kv_table([
        ("Mp",            flexure.Mp),
        ("Mn",            flexure.Mn),
        ("φMn",           flexure.phi_Mn),
        ("Lp",            flexure.Lp),
        ("Lr",            flexure.Lr),
        ("Regime",        flexure.regime),
        ("Utilization",   flexure.utilization),
        ("Status",        "OK" if (flexure.ok or flexure.ok is None) else "NG"),
    ])

    rep.add_section("Shear (§G2)")
    rep.add_kv_table([
        ("Vn",            shear.Vn),
        ("φVn",           shear.phi_Vn),
        ("Cv1",           shear.Cv1),
        ("Utilization",   shear.utilization),
        ("Status",        "OK" if (shear.ok or shear.ok is None) else "NG"),
    ])

    if column is not None:
        rep.add_section("Compression (§E3)")
        rep.add_kv_table([
            ("Pn",            column.Pn),
            ("φPn",           column.phi_Pn),
            ("Fcr",           column.Fcr),
            ("Fe",            column.Fe),
            ("KL/r",          column.KL_over_r),
            ("Regime",        column.regime),
            ("Utilization",   column.utilization),
            ("Status",        "OK" if (column.ok or column.ok is None) else "NG"),
        ])

    if interaction is not None:
        rep.add_section("Combined axial + bending (§H1)")
        rep.add_kv_table([
            ("Formula",       interaction.formula),
            ("Interaction",   interaction.interaction),
            ("Status",        "OK" if interaction.ok else "NG"),
        ])
    return rep.save(path)


# ---------------------------------------------------------------------------
# Loss-assessment report (consumes Phase 6 FEMA P-58 LossResult)
# ---------------------------------------------------------------------------

def build_loss_report(loss, path: str, *,
                       project: str = "",
                       author: str = "",
                       hazard_label: str = "") -> str:
    """Render a FEMA P-58 loss-assessment summary."""
    rep = Report(
        title="Seismic Loss Assessment",
        subtitle=f"FEMA P-58 (minimal) — {hazard_label}" if hazard_label
                 else "FEMA P-58 (minimal)",
        project=project, author=author,
    )
    rep.add_section("Summary")
    rep.add_kv_table([
        ("Expected cost",            loss.expected_cost),
        ("Expected downtime (days)", loss.expected_downtime_days),
        ("# realisations",           loss.n_realisations),
    ])
    if loss.cost_realisations:
        rep.add_kv_table([
            ("p50",                  loss.percentile(50)),
            ("p90",                  loss.percentile(90)),
            ("p10",                  loss.percentile(10)),
        ])
    if loss.cost_by_group:
        rep.add_section("Cost by component group")
        rows = [(k, v) for k, v in sorted(loss.cost_by_group.items(),
                                           key=lambda t: -t[1])]
        rep.add_kv_table(rows)
    return rep.save(path)



# ---------------------------------------------------------------------------
# Modal report (consumes a DataFrame of modes)
# ---------------------------------------------------------------------------


def build_modal_report(modal_df, path: str,
                       *,
                       project: str = "",
                       author: str = "",
                       mass_target: float = 0.90) -> str:
    """Render a modal-analysis summary PDF.

    Expected columns: mode, T, f, mass_x, mass_y (mass as fraction 0-1).
    """
    rep = Report(
        title="Modal Analysis Report",
        subtitle="Mass participation target: {:.0f}%".format(mass_target * 100),
        project=project, author=author,
    )
    rep.add_section("Summary")
    cols = set(modal_df.columns) if hasattr(modal_df, "columns") else set()
    if {"mass_x", "mass_y"}.issubset(cols):
        mx = float(modal_df["mass_x"].sum())
        my = float(modal_df["mass_y"].sum())
        rep.add_kv_table([
            ("# modes",            len(modal_df)),
            ("Accumulated mass X", "{:.1f}%".format(mx * 100)),
            ("Accumulated mass Y", "{:.1f}%".format(my * 100)),
            ("Meets target",       "Yes" if (mx >= mass_target and my >= mass_target)
                                   else "No"),
        ])
    if "T" in cols and len(modal_df) > 0:
        T1 = float(modal_df["T"].iloc[0])
        rep.add_kv_table([("T1 (fundamental period)", "{:.4f} s".format(T1))])
    rep.add_section("Mode table")
    rows = []
    for _, row in modal_df.iterrows():
        mode = int(row.get("mode", 0))
        T = float(row.get("T", 0.0))
        f = float(row.get("f", 0.0))
        mx = float(row.get("mass_x", 0.0))
        my = float(row.get("mass_y", 0.0))
        rows.append((
            "Mode {}".format(mode),
            "T={:.4f}s  f={:.3f}Hz  Ux={:.1%}  Uy={:.1%}".format(T, f, mx, my),
        ))
    rep.add_kv_table(rows)
    return rep.save(path)
