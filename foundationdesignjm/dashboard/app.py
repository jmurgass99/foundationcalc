"""Streamlit dashboard for FoundationDesignJm.

Provides a one-screen interactive UI for each of the main designers
implemented in the library:

- Retaining wall
- Basement wall
- Tower-crane foundation
- Seismic spread footing (EN 1998-5)
- Mat foundation (Winkler 2D)
- CPT-to-design pipeline
- Reverse design (optimum footing dimensions)
- EC8 design spectrum (with national zone lookup)
- Foundation impedance (SSI springs)

Each page collects the inputs in a form, calls the corresponding
designer and offers a download button for the generated PDF report
when applicable.

Run via:   python -m foundationdesignjm.dashboard
"""

from __future__ import annotations

import os
import tempfile

try:
    import streamlit as st
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "streamlit is required to run the dashboard. "
        "Install with `pip install streamlit`."
    ) from e

from foundationdesignjm._brand import NAME as _BRAND_NAME, TAGLINE as _BRAND_TAGLINE
from foundationdesignjm.codes.eurocode7 import DesignApproach
from foundationdesignjm.codes.eurocode8 import (
    GroundType,
    ImportanceClass,
    SEISMIC_ZONES,
    build_design_spectrum,
    list_zones,
)


# ---------------------------------------------------------------------------
# Page registry
# ---------------------------------------------------------------------------

def _page_retaining_wall():
    from foundationdesignjm.core.material import Concrete
    from foundationdesignjm.core.soil import SoilLayer, SoilType
    from foundationdesignjm.design.retaining_wall import (
        CantileverWallDesigner,
        CantileverWallGeometry,
        RetainingWallLoading,
    )
    from foundationdesignjm.utils.pdf_report import (
        ReportMeta, report_retaining_wall,
    )

    st.header("Cantilever retaining wall")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Geometry")
        H = st.number_input("Stem height H (m)", value=5.0, step=0.5)
        stem_top = st.number_input("Stem top thickness (m)", value=0.30, step=0.05)
        stem_bot = st.number_input("Stem bottom thickness (m)", value=0.45, step=0.05)
        toe = st.number_input("Toe length (m)", value=1.0, step=0.1)
        heel = st.number_input("Heel length (m)", value=2.5, step=0.1)
        base_t = st.number_input("Base thickness (m)", value=0.55, step=0.05)
    with col2:
        st.subheader("Soils and loads")
        phi_fill = st.slider("Backfill phi (deg)", 20, 45, 33)
        gamma_fill = st.number_input("Backfill gamma (kN/m3)", value=19.0)
        phi_found = st.slider("Foundation phi (deg)", 20, 45, 36)
        gamma_found = st.number_input("Foundation gamma (kN/m3)", value=20.0)
        surcharge = st.number_input("Surcharge q (kN/m2)", value=10.0)
        water_h = st.number_input("Water height (m)", value=0.0, step=0.5)
        da_label = st.selectbox("Design Approach", ["DA1-C1", "DA1-C2", "DA2", "DA3"], index=2)
        da_map = {"DA1-C1": DesignApproach.DA1_C1, "DA1-C2": DesignApproach.DA1_C2,
                  "DA2": DesignApproach.DA2, "DA3": DesignApproach.DA3}

    if st.button("Run check", key="rw_run"):
        geo = CantileverWallGeometry(
            H=H, stem_top=stem_top, stem_bottom=stem_bot,
            toe=toe, heel=heel, base_thickness=base_t,
            embedment_front=0.8,
        )
        backfill = SoilLayer(name="fill", thickness=10,
                            soil_type=SoilType.COHESIONLESS,
                            friction_angle=phi_fill, unit_weight=gamma_fill)
        foundation = SoilLayer(name="found", thickness=10,
                              soil_type=SoilType.COHESIONLESS,
                              friction_angle=phi_found, unit_weight=gamma_found)
        load = RetainingWallLoading(
            backfill=backfill, foundation_soil=foundation,
            surcharge_q=surcharge, water_height=water_h,
            use_coulomb=True, delta_over_phi=2 / 3,
        )
        des = CantileverWallDesigner(
            geo, load, Concrete(fck=30), design_approach=da_map[da_label],
        )
        res = des.check()

        c1, c2, c3 = st.columns(3)
        c1.metric("Bearing utilization", f"{res.bearing_utilization * 100:.1f} %",
                 delta="OK" if res.bearing_utilization <= 1.0 else "FAIL")
        c2.metric("Sliding utilization", f"{res.sliding_utilization * 100:.1f} %",
                 delta="OK" if res.sliding_utilization <= 1.0 else "FAIL")
        c3.metric("Overturning utilization", f"{res.overturning_utilization * 100:.1f} %",
                 delta="OK" if res.overturning_utilization <= 1.0 else "FAIL")

        st.subheader("Structural critical sections (kN.m/m and kN/m per m run)")
        st.dataframe({
            "Section": ["Stem base", "Heel", "Toe"],
            "M [kN.m/m]": [res.M_stem_base, res.M_heel, res.M_toe],
            "V [kN/m]": [res.V_stem_base, res.V_heel, res.V_toe],
        })

        # PDF report
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = report_retaining_wall(
                des, res, tmp.name,
                meta=ReportMeta(project="Retaining wall design",
                                engineer="Dashboard", client="Demo"),
            )
        with open(path, "rb") as fh:
            st.download_button("Download PDF report", fh.read(),
                              file_name="retaining_wall_report.pdf",
                              mime="application/pdf")


def _page_basement_wall():
    from foundationdesignjm.design.basement_wall import (
        BasementWallDesigner, BasementWallGeometry, BasementWallLoading,
        PressureDiagram, SupportConfig,
    )
    from foundationdesignjm.utils.pdf_report import (
        ReportMeta, report_basement_wall,
    )

    st.header("Basement wall")
    col1, col2 = st.columns(2)
    with col1:
        H = st.number_input("Height (m)", value=3.5, step=0.5)
        t = st.number_input("Thickness (m)", value=0.30, step=0.05)
        e1 = st.number_input("e top (m)", value=0.05, step=0.01)
        e2 = st.number_input("e base (m)", value=0.10, step=0.01)
    with col2:
        phi = st.slider("phi (deg)", 20, 40, 30)
        gamma = st.number_input("gamma (kN/m3)", value=19.0)
        q = st.number_input("Surcharge (kN/m2)", value=10.0)
        Nmax = st.number_input("N_max (kN/m)", value=200.0)
        support_label = st.selectbox("Support", ["propped_cantilever", "cantilever", "pinned_pinned"])
        diagram_label = st.selectbox("Pressure", ["triangular", "rectangular"])

    if st.button("Run", key="bw_run"):
        geo = BasementWallGeometry(height=H, thickness=t,
                                  eccentricity_top=e1, eccentricity_base=e2)
        load = BasementWallLoading(
            phi_deg=phi, gamma_soil=gamma, surcharge_q=q,
            N_min_kN_per_m=0, N_max_kN_per_m=Nmax,
        )
        des = BasementWallDesigner(
            geo, load,
            support=SupportConfig(support_label),
            pressure=PressureDiagram(diagram_label),
        )
        res = des.solve()
        c1, c2, c3 = st.columns(3)
        c1.metric("M outer max", f"{res.M_outer_max_kNm:.1f} kN.m/m")
        c2.metric("M inner max", f"{res.M_inner_max_kNm:.1f} kN.m/m")
        c3.metric("V max", f"{res.V_max_kN:.1f} kN/m")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            report_basement_wall(des, res, tmp.name,
                                meta=ReportMeta(project="Basement wall",
                                                engineer="Dashboard"))
            tmp.flush()
        with open(tmp.name, "rb") as fh:
            st.download_button("Download PDF", fh.read(),
                              file_name="basement_wall.pdf",
                              mime="application/pdf")


def _page_cpt_pipeline():
    from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
    from foundationdesignjm.analysis.cpt_to_design import design_footing_from_cpt
    from foundationdesignjm.core.geometry import RectangularFoundation
    from foundationdesignjm.utils.pdf_report import (
        ReportMeta, report_cpt_to_design,
    )

    st.header("CPT-to-design pipeline")

    st.subheader("Footing")
    c1, c2, c3 = st.columns(3)
    with c1:
        B = st.number_input("B (mm)", value=2500, step=100)
    with c2:
        L = st.number_input("L (mm)", value=2500, step=100)
    with c3:
        t = st.number_input("Thickness (mm)", value=500, step=50)
    D = st.number_input("Founding depth (m)", value=1.5, step=0.1)
    q = st.number_input("Applied pressure (kPa)", value=180.0, step=10.0)

    st.subheader("CPT data (one row per depth)")
    sample = (
        "depth_m,q_c_MPa,f_s_kPa,u_2_kPa\n"
        "0.5,6.0,40,0\n1,6.0,40,0\n2,6.0,40,0\n3,6.0,40,0\n"
        "4,1.2,60,60\n5,1.2,60,60\n6,1.2,60,60\n7,1.2,60,60\n"
        "8,18,80,0\n10,18,80,0\n12,18,80,0\n15,18,80,0\n"
    )
    raw = st.text_area("CSV (depth,q_c,f_s,u_2)", value=sample, height=200)
    wt = st.number_input("Water table depth (m)", value=2.5, step=0.5)

    if st.button("Design", key="cpt_run"):
        readings = []
        for line in raw.strip().splitlines()[1:]:
            d, qc, fs, u2 = (float(x) for x in line.split(","))
            readings.append(CPTReading(depth=d, q_c_MPa=qc, f_s_kPa=fs, u_2_kPa=u2))
        cpt = CPTProfile(readings=readings, water_table_depth_m=wt)
        pad = RectangularFoundation(length=L, width=B, thickness=t,
                                    embedment_depth=D * 1000)
        res = design_footing_from_cpt(
            cpt, pad, founding_depth_m=D, q_applied_kPa=q,
            design_approach=DesignApproach.DA2,
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Bearing util", f"{res.bearing_utilization * 100:.1f} %",
                 delta="OK" if res.bearing_ok else "FAIL")
        c2.metric("Settlement", f"{res.settlement.s_total_mm:.1f} mm",
                 delta="OK" if res.settlement_ok else f">{res.settlement_limit_mm:.0f}")
        c3.metric("Failure mode", res.failure_mode.mode.value)

        st.subheader("Auto-derived soil profile")
        rows = []
        for L_ in res.profile.layers:
            rows.append({
                "Layer": L_.name, "Type": L_.soil_type.value,
                "Thickness (m)": L_.thickness,
                "phi (deg)": L_.friction_angle,
                "c_u (kPa)": L_.undrained_shear_strength,
                "E (MPa)": L_.youngs_modulus,
            })
        st.dataframe(rows)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            report_cpt_to_design(cpt, pad, res, tmp.name,
                                meta=ReportMeta(project="CPT design",
                                                engineer="Dashboard"))
        with open(tmp.name, "rb") as fh:
            st.download_button("Download PDF", fh.read(),
                              file_name="cpt_design.pdf",
                              mime="application/pdf")


def _page_reverse_design():
    from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
    from foundationdesignjm.analysis.reverse_design import (
        OptimizationGoal, optimize_footing_dimensions,
    )

    st.header("Reverse design (optimum footing dimensions)")
    load = st.number_input("Vertical load (kN)", value=1500.0, step=50.0)
    D = st.number_input("Founding depth (m)", value=1.5)
    limit = st.number_input("Settlement limit (mm)", value=50.0)
    B_min = st.number_input("B_min (mm)", value=800, step=100)
    B_max = st.number_input("B_max (mm)", value=6000, step=200)
    t = st.number_input("Thickness (mm)", value=600, step=50)

    sample = "0.5,6.0,40\n1,6.0,40\n2,6.0,40\n3,6.0,40\n4,1.2,60\n6,1.2,60\n8,18,80\n12,18,80\n"
    raw = st.text_area("CPT data (depth,q_c,f_s)", value=sample, height=180)
    wt = st.number_input("Water table (m)", value=2.5)

    if st.button("Optimize", key="opt_run"):
        readings = []
        for line in raw.strip().splitlines():
            d, qc, fs = (float(x) for x in line.split(","))
            readings.append(CPTReading(depth=d, q_c_MPa=qc, f_s_kPa=fs))
        cpt = CPTProfile(readings=readings, water_table_depth_m=wt)
        opt = optimize_footing_dimensions(
            cpt, load_kN=load, founding_depth_m=D,
            design_approach=DesignApproach.DA2,
            settlement_limit_mm=limit,
            B_min_mm=B_min, B_max_mm=B_max, thickness_mm=t,
            goal=OptimizationGoal.MIN_AREA,
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Optimum B = L", f"{opt.best.B * 1000:.0f} mm")
        c2.metric("Bearing util", f"{opt.best.bearing_utilization * 100:.1f} %")
        c3.metric("Settlement", f"{opt.best.settlement_mm:.1f} mm")
        c4.metric("Cost (EUR)", f"{opt.best.cost_eur:,.0f}")
        st.subheader("Iteration history")
        st.dataframe([
            {"iter": i, "B (m)": c.B,
             "util (%)": round(c.bearing_utilization * 100, 1),
             "s (mm)": round(c.settlement_mm, 2),
             "cost (EUR)": round(c.cost_eur, 0),
             "passes": c.passes}
            for i, c in enumerate(opt.history)
        ])


def _page_ec8_spectrum():
    import numpy as np

    st.header("EC8 design response spectrum")
    country = st.selectbox("Country", list(SEISMIC_ZONES.keys()), index=0)
    region = st.selectbox("Region", list_zones(country))
    ground = st.selectbox("Ground type", [g.value for g in GroundType])
    imp = st.selectbox("Importance class", [c.value for c in ImportanceClass], index=1)
    q = st.number_input("Behaviour factor q", value=1.0, min_value=1.0, step=0.5)

    if st.button("Compute spectrum", key="ec8_run"):
        ds = build_design_spectrum(
            country, region, GroundType(ground),
            ImportanceClass(imp), behaviour_factor_q=q,
        )
        T = np.linspace(0.01, 4.0, 200)
        S_e = np.array([ds.S_e(t) for t in T])
        S_d = np.array([ds.S_d(t) for t in T])
        c1, c2, c3 = st.columns(3)
        c1.metric("a_gR (g)", f"{ds.a_gR_g:.3f}")
        c2.metric("γ_I", f"{ds.gamma_I}")
        c3.metric("Spectrum type", ds.spectrum_type.value)
        st.line_chart({"T [s]": T.tolist(),
                      "S_e / g (elastic)": S_e.tolist(),
                      "S_d / g (design)": S_d.tolist()},
                      x="T [s]")


def _page_foundation_impedance():
    from foundationdesignjm.dynamics import rectangular_footing_impedance

    st.header("Foundation impedance (Gazetas 1991)")
    c1, c2 = st.columns(2)
    with c1:
        B = st.number_input("Width B (m)", value=3.0, step=0.1)
        L = st.number_input("Length L (m)", value=3.0, step=0.1)
    with c2:
        G = st.number_input("Soil G (MPa)", value=40.0, step=5.0)
        nu = st.number_input("Poisson ratio nu", value=0.30, step=0.05)
        freq = st.number_input("Frequency (Hz)", value=2.0, step=0.5)

    if st.button("Compute impedance", key="ssi_run"):
        imp = rectangular_footing_impedance(B_m=B, L_m=L, G_MPa=G, nu=nu,
                                           frequency_Hz=freq)
        c1, c2, c3 = st.columns(3)
        c1.metric("V_s (m/s)", f"{imp.V_s():.1f}")
        c2.metric("K_vertical", f"{imp.vertical.K_static:,.0f} kN/m")
        c3.metric("K_horizontal", f"{imp.horizontal_x.K_static:,.0f} kN/m")
        st.subheader("Full spring set")
        st.dataframe([
            {"DOF": "vertical",
             "K_static": imp.vertical.K_static, "k_dyn": imp.vertical.k_dyn,
             "c_dyn": imp.vertical.c_dyn, "K_dyn": imp.vertical.K_dyn,
             "C_dyn": imp.vertical.C_dyn},
            {"DOF": "horizontal_x", "K_static": imp.horizontal_x.K_static,
             "k_dyn": imp.horizontal_x.k_dyn, "c_dyn": imp.horizontal_x.c_dyn,
             "K_dyn": imp.horizontal_x.K_dyn, "C_dyn": imp.horizontal_x.C_dyn},
            {"DOF": "horizontal_y", "K_static": imp.horizontal_y.K_static,
             "k_dyn": imp.horizontal_y.k_dyn, "c_dyn": imp.horizontal_y.c_dyn,
             "K_dyn": imp.horizontal_y.K_dyn, "C_dyn": imp.horizontal_y.C_dyn},
            {"DOF": "rocking_x", "K_static": imp.rocking_x.K_static,
             "k_dyn": imp.rocking_x.k_dyn, "c_dyn": imp.rocking_x.c_dyn,
             "K_dyn": imp.rocking_x.K_dyn, "C_dyn": imp.rocking_x.C_dyn},
            {"DOF": "rocking_y", "K_static": imp.rocking_y.K_static,
             "k_dyn": imp.rocking_y.k_dyn, "c_dyn": imp.rocking_y.c_dyn,
             "K_dyn": imp.rocking_y.K_dyn, "C_dyn": imp.rocking_y.C_dyn},
            {"DOF": "torsion", "K_static": imp.torsion.K_static,
             "k_dyn": imp.torsion.k_dyn, "c_dyn": imp.torsion.c_dyn,
             "K_dyn": imp.torsion.K_dyn, "C_dyn": imp.torsion.C_dyn},
        ])


PAGES = {
    "Retaining wall": _page_retaining_wall,
    "Basement wall": _page_basement_wall,
    "CPT-to-design": _page_cpt_pipeline,
    "Reverse design": _page_reverse_design,
    "EC8 spectrum": _page_ec8_spectrum,
    "Foundation impedance": _page_foundation_impedance,
}


def main() -> None:
    st.set_page_config(
        page_title=_BRAND_NAME,
        page_icon=":bricks:",
        layout="wide",
    )
    st.sidebar.title(_BRAND_NAME)
    st.sidebar.markdown(_BRAND_TAGLINE)
    page = st.sidebar.radio("Module", list(PAGES.keys()))
    st.sidebar.divider()
    st.sidebar.caption("Tests: 173+  |  Mods: 18 analysis + 8 design")
    PAGES[page]()


if __name__ == "__main__":
    main()
