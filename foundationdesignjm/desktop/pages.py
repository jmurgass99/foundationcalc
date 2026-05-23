"""Tkinter page implementations for the FoundationDesignJm desktop app."""

from __future__ import annotations

import math
import os
import tempfile
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import matplotlib
matplotlib.use("TkAgg")
import numpy as np
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk,
)
from matplotlib.figure import Figure

from .widgets import LabeledCombobox, LabeledEntry, ScrolledOutput


# ---------------------------------------------------------------------------
# Base page
# ---------------------------------------------------------------------------

class BasePage(ttk.Frame):
    """Common layout: form (left) + plot/output (right) + actions (bottom)."""

    title: str = "Page"

    def __init__(self, master: tk.Misc):
        super().__init__(master, padding=10)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left: scrollable form area
        self.form_frame = ttk.LabelFrame(self, text="Inputs", padding=10)
        self.form_frame.grid(row=0, column=0, sticky="ns", padx=(0, 8))

        # Right: vertical stack with plot on top, output below
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=2)
        right.columnconfigure(0, weight=1)

        self.plot_frame = ttk.LabelFrame(right, text="Plot")
        self.plot_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.output_frame = ttk.LabelFrame(right, text="Output", padding=4)
        self.output_frame.grid(row=1, column=0, sticky="nsew")
        self.output = ScrolledOutput(self.output_frame, height=10)
        self.output.pack(fill="both", expand=True)

        # Matplotlib canvas
        self.fig = Figure(figsize=(6, 4), dpi=90)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(fill="x")

        # Bottom: actions
        actions = ttk.Frame(self)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.run_button = ttk.Button(actions, text="Run", command=self._run_safely)
        self.run_button.pack(side="left", padx=4)
        self.export_button = ttk.Button(actions, text="Save plot…",
                                        command=self._save_plot)
        self.export_button.pack(side="left", padx=4)

    # ------------------------------------------------------------------
    def _run_safely(self) -> None:
        self.output.clear()
        self.fig.clear()
        try:
            self.run()
        except Exception as e:                                # noqa: BLE001
            self.output.writeln("ERROR: " + str(e), tag="fail")
            self.output.writeln(traceback.format_exc(), tag="muted")
        self.canvas.draw()

    def _save_plot(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
        )
        if path:
            self.fig.savefig(path, dpi=150, bbox_inches="tight")
            messagebox.showinfo("Saved", f"Plot written to:\n{path}")

    def run(self) -> None:                                    # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Custom footing design page
# ---------------------------------------------------------------------------

class CustomFootingPage(BasePage):
    title = "Custom footing design"

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        f = self.form_frame
        self.N = LabeledEntry(f, "N (axial)", "620", "kN")
        self.V = LabeledEntry(f, "V (shear)", "70", "kN")
        self.M = LabeledEntry(f, "M (moment)", "320", "kN.m")
        self.B = LabeledEntry(f, "B (width)", "3500", "mm")
        self.L = LabeledEntry(f, "L (length)", "3500", "mm")
        self.H = LabeledEntry(f, "h (thickness)", "750", "mm")
        self.col_a = LabeledEntry(f, "Column side a", "400", "mm")
        self.embed = LabeledEntry(f, "Embedment D", "1000", "mm")
        self.phi = LabeledEntry(f, "Soil phi'", "32", "deg")
        self.gamma = LabeledEntry(f, "Soil gamma", "19", "kN/m3")
        self.E_soil = LabeledEntry(f, "Soil E", "30", "MPa")
        self.fck = LabeledEntry(f, "Concrete fck", "30", "MPa")
        self.fyk = LabeledEntry(f, "Steel fyk", "500", "MPa")
        self.cover = LabeledEntry(f, "Cover", "70", "mm")
        for i, w in enumerate([self.N, self.V, self.M, self.B, self.L, self.H,
                              self.col_a, self.embed, self.phi, self.gamma,
                              self.E_soil, self.fck, self.fyk, self.cover]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.analysis.bearing_capacity import (
            BearingCapacityFormula, drained_bearing_capacity,
        )
        from foundationdesignjm.analysis.stability import (
            overturning_check, sliding_resistance_drained,
        )
        from foundationdesignjm.codes.eurocode7 import (
            DesignApproach, LimitState, get_partial_factors,
        )
        from foundationdesignjm.core.geometry import Column, RectangularFoundation
        from foundationdesignjm.core.material import Concrete, ReinforcingSteel
        from foundationdesignjm.core.soil import SoilLayer, SoilType
        from foundationdesignjm.design.punching_shear import punching_shear_check
        from foundationdesignjm.design.reinforcement import (
            critical_section_offset, flexural_reinforcement,
        )

        N_k = self.N.get_float(620)
        V_k = self.V.get_float(70)
        M_k = self.M.get_float(320)
        B = self.B.get_float(3500)
        L = self.L.get_float(3500)
        H = self.H.get_float(750)
        a = self.col_a.get_float(400)
        emb = self.embed.get_float(1000)

        concrete = Concrete(name=f"C{int(self.fck.get_float(30))}",
                           fck=self.fck.get_float(30))
        steel = ReinforcingSteel(fyk=self.fyk.get_float(500))
        soil = SoilLayer(
            name="soil", thickness=10,
            soil_type=SoilType.COHESIONLESS,
            friction_angle=self.phi.get_float(32),
            cohesion=0.0,
            unit_weight=self.gamma.get_float(19),
            youngs_modulus=self.E_soil.get_float(30),
        )
        fdn = RectangularFoundation(length=L, width=B, thickness=H, embedment_depth=emb)
        col = Column(length=a, width=a, pos_x=L/2, pos_y=B/2)

        pf = get_partial_factors(DesignApproach.DA2, LimitState.GEO)
        gG, gQ = pf.actions.gamma_G_unfav, pf.actions.gamma_Q_unfav
        N_d = gG * N_k
        V_d = gQ * V_k
        M_d = gQ * M_k
        W_d = gG * fdn.area * (H/1000) * 25

        M_at_base = M_d + V_d * (H/1000)
        N_total_d = N_d + W_d
        e_x = M_at_base / N_total_d

        bc = drained_bearing_capacity(
            foundation=fdn, soil=soil, e_x=e_x, e_y=0.0,
            H_load=V_d, V_load=N_total_d,
            gamma_Rv=pf.resistance.gamma_Rv,
            gamma_phi=pf.soil.gamma_phi,
            gamma_c=pf.soil.gamma_c,
            gamma_gamma=pf.soil.gamma_gamma,
            formula=BearingCapacityFormula.CHEN_EC7,
        )
        q_Ed = N_total_d / bc.A_eff
        q_Rd = bc.q_ult / pf.resistance.gamma_Rv

        sl = sliding_resistance_drained(
            N_Ed=N_total_d, soil=soil, A_eff=bc.A_eff, H_Ed=V_d,
            delta_factor=1.0,
            gamma_phi=pf.soil.gamma_phi, gamma_c=pf.soil.gamma_c,
            gamma_Rh=pf.resistance.gamma_Rh,
        )
        overturn = overturning_check(
            M_dst_d=abs(M_at_base), M_stb_d=N_total_d * (B/2000),
            V_d=N_total_d, B=B/1000,
        )

        # Flexural design (long direction)
        sigma_max = N_total_d / (B/1000 * L/1000) + 6 * abs(M_at_base) / ((B/1000) * (L/1000)**2)
        sigma_min = N_total_d / (B/1000 * L/1000) - 6 * abs(M_at_base) / ((B/1000) * (L/1000)**2)
        s1_mm = critical_section_offset(a)
        cant_len = (L/2 - a/2 + s1_mm) / 1000
        sigma_slope = (sigma_max - sigma_min) / (L/1000)
        sigma_crit = (sigma_max + sigma_min)/2 + sigma_slope * (a/2 - s1_mm)/1000
        M_per_m = (sigma_crit * cant_len**2 / 2.0
                  + (sigma_max - sigma_crit) * cant_len**2 / 3.0)
        M_per_m -= (H/1000) * 25 * cant_len**2 / 2.0
        cover = self.cover.get_float(70)
        d_eff = H - cover - 8
        flex = flexural_reinforcement(
            M_Ed_kNm=M_per_m, b_mm=1000, d_mm=d_eff,
            concrete=concrete, steel=steel,
        )
        rho = flex.As_provided / (1000 * d_eff)
        punch = punching_shear_check(
            foundation=fdn, column=col,
            N_sd_kN=N_total_d, fck_MPa=concrete.fck,
            rho_x=rho, rho_y=rho, d_eff_m=d_eff/1000,
        )

        # ---------- Output ----------
        out = self.output
        out.writeln("==== ULS CHECKS (DA-2) ====", tag="title")
        out.writeln(f"  e = M/N at base = {e_x*1000:.0f} mm  "
                   f"(B/6 = {B/6:.0f} mm) → "
                   f"{'middle-third' if abs(e_x) <= B/6/1000 else 'partial uplift'}",
                   tag="muted")
        for label, val, util in [
            ("Bearing", f"q_Ed={q_Ed:.0f} q_Rd={q_Rd:.0f} kPa", q_Ed/q_Rd),
            ("Sliding", f"H_Ed={V_d:.0f} H_Rd={sl.H_Rd:.0f} kN", sl.utilization),
            ("Overturning", f"M_dst={abs(M_at_base):.0f} M_stb={N_total_d*(B/2000):.0f} kNm",
             overturn.utilization),
            ("Punching", f"tau_sd={punch.tau_sd:.0f} tau_Rd={punch.tau_rd:.0f} kPa",
             punch.utilization),
        ]:
            tag = "ok" if util <= 1.0 else "fail"
            out.writeln(f"  {label:<13} util = {util*100:>5.1f}%  ({val})", tag=tag)
        out.writeln()
        out.writeln("==== FLEXURAL DESIGN (long direction) ====", tag="title")
        out.writeln(f"  M_Ed (per m)       = {M_per_m:.1f} kN.m/m")
        out.writeln(f"  d_eff              = {d_eff:.0f} mm")
        out.writeln(f"  As_required (EC2)  = {flex.As_required:.0f} mm²/m")
        out.writeln(f"  As_min            = {flex.As_min:.0f} mm²/m")
        out.writeln(f"  As_provided        = {flex.As_provided:.0f} mm²/m")
        As_total = flex.As_provided * (B/1000)
        out.writeln(f"  Total As across {B/1000:.1f} m = {As_total:.0f} mm²")
        out.writeln()
        out.writeln("  Bar options:", tag="title")
        for dia, A in [(16, 201), (20, 314), (25, 491)]:
            n = math.ceil(As_total / A)
            s = (B - 2*cover) / (n - 1) if n > 1 else 0
            out.writeln(f"    {n:>2} ϕ{dia:>2} mm  @ {s:>3.0f} mm c/c   "
                       f"As = {n*A} mm²")

        # ---------- Plot ----------
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        # Plan view: footing rectangle, column, soil-pressure trapezoid
        ax.set_aspect("equal")
        # Footing
        ax.add_patch(matplotlib.patches.Rectangle(
            (-L/2000, -B/2000), L/1000, B/1000,
            facecolor="#dde3eb", edgecolor="black",
        ))
        # Column
        ax.add_patch(matplotlib.patches.Rectangle(
            (-a/2000, -a/2000), a/1000, a/1000,
            facecolor="#999", edgecolor="black",
        ))
        # Pressure heatmap on the footing
        xs = np.linspace(-L/2000, L/2000, 40)
        ys = np.linspace(-B/2000, B/2000, 40)
        X, Y = np.meshgrid(xs, ys)
        sigma_grid = N_total_d/(B/1000 * L/1000) + 12*abs(M_at_base)*X/((B/1000) * (L/1000)**3)
        c = ax.pcolormesh(X, Y, sigma_grid, alpha=0.4, cmap="YlOrRd", shading="auto")
        self.fig.colorbar(c, ax=ax, label="σ (kPa)")
        ax.set_title(f"Pressure under footing  e = {e_x*1000:.0f} mm")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# CPT-to-design page
# ---------------------------------------------------------------------------

class CptPipelinePage(BasePage):
    title = "CPT-to-design pipeline"

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        f = self.form_frame
        self.B = LabeledEntry(f, "B (mm)", "2500")
        self.L = LabeledEntry(f, "L (mm)", "2500")
        self.H = LabeledEntry(f, "h (mm)", "500")
        self.D = LabeledEntry(f, "Founding depth (m)", "1.5")
        self.q = LabeledEntry(f, "q (kPa)", "180")
        self.wt = LabeledEntry(f, "Water table (m)", "2.5")
        self.sls = LabeledEntry(f, "SLS limit (mm)", "50")
        self.cpt_text = tk.Text(f, height=10, width=34, font=("Consolas", 9))
        self.cpt_text.insert("1.0",
            "depth,qc,fs,u2\n"
            "0.5,6.0,40,0\n1,6.0,40,0\n2,6.0,40,0\n3,6.0,40,0\n"
            "4,1.2,60,60\n5,1.2,60,60\n6,1.2,60,60\n7,1.2,60,60\n"
            "8,18,80,0\n10,18,80,0\n12,18,80,0\n15,18,80,0\n")
        for i, w in enumerate([self.B, self.L, self.H, self.D, self.q,
                              self.wt, self.sls]):
            w.grid(row=i, column=0, sticky="w", pady=1)
        ttk.Label(f, text="CPT data (CSV):",
                 anchor="w").grid(row=8, column=0, sticky="w", pady=(8, 2))
        self.cpt_text.grid(row=9, column=0, sticky="we", pady=2)

    def run(self) -> None:
        from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
        from foundationdesignjm.analysis.cpt_to_design import (
            design_footing_from_cpt,
        )
        from foundationdesignjm.codes.eurocode7 import DesignApproach
        from foundationdesignjm.core.geometry import RectangularFoundation

        readings = []
        for line in self.cpt_text.get("1.0", "end").strip().splitlines()[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                d = float(parts[0]); qc = float(parts[1]); fs = float(parts[2])
                u2 = float(parts[3]) if len(parts) > 3 else 0.0
                readings.append(CPTReading(depth=d, q_c_MPa=qc, f_s_kPa=fs, u_2_kPa=u2))
        cpt = CPTProfile(readings=readings, water_table_depth_m=self.wt.get_float(2.5))
        pad = RectangularFoundation(
            length=self.L.get_float(2500), width=self.B.get_float(2500),
            thickness=self.H.get_float(500),
            embedment_depth=self.D.get_float(1.5)*1000,
        )
        res = design_footing_from_cpt(
            cpt, pad,
            founding_depth_m=self.D.get_float(1.5),
            q_applied_kPa=self.q.get_float(180),
            design_approach=DesignApproach.DA2,
            settlement_limit_mm=self.sls.get_float(50),
        )

        out = self.output
        out.writeln("==== AUTO-DERIVED SOIL PROFILE ====", tag="title")
        for L_ in res.profile.layers:
            params = []
            if L_.friction_angle and L_.friction_angle > 0:
                params.append(f"phi={L_.friction_angle:.1f}deg")
            if L_.undrained_shear_strength:
                params.append(f"c_u={L_.undrained_shear_strength:.0f} kPa")
            if L_.youngs_modulus:
                params.append(f"E={L_.youngs_modulus:.0f} MPa")
            out.writeln(f"  {L_.name:<26}  {L_.soil_type.value:<14}  "
                       f"t={L_.thickness:.2f}m  {', '.join(params)}")

        out.writeln()
        out.writeln("==== ULS BEARING ====", tag="title")
        out.writeln(f"  Governing: {res.bearing.governing_case} → {res.bearing.governing_layer}")
        out.writeln(f"  q_Ed = {res.q_applied_kPa:.1f} kPa, q_Rd = {res.q_Rd_kPa:.1f} kPa")
        out.writeln(f"  Utilization = {res.bearing_utilization*100:.1f}%",
                   tag="ok" if res.bearing_ok else "fail")
        out.writeln(f"  Failure mode (Vesic): {res.failure_mode.mode.value}  "
                   f"I_r = {res.failure_mode.I_r:.0f}, I_rc = {res.failure_mode.I_rc:.0f}")

        out.writeln()
        out.writeln("==== SLS SETTLEMENT ====", tag="title")
        out.writeln(f"  Immediate: {res.settlement.s_immediate_mm:.1f} mm")
        out.writeln(f"  Consolidation: {res.settlement.s_consolidation_mm:.1f} mm")
        out.writeln(f"  Total: {res.settlement.s_total_mm:.1f} mm  "
                   f"(limit {res.settlement_limit_mm:.0f} mm)",
                   tag="ok" if res.settlement_ok else "fail")

        # ---------- Plot: CPT log + sub-layer stress increment ----------
        self.fig.clear()
        ax1 = self.fig.add_subplot(1, 2, 1)
        depths = [r.depth for r in cpt.readings]
        qc = [r.q_c_MPa for r in cpt.readings]
        ax1.plot(qc, depths, "b-", marker="o", lw=1.4)
        ax1.invert_yaxis()
        ax1.set_xlabel("q_c [MPa]")
        ax1.set_ylabel("Depth [m]")
        ax1.set_title("CPT log")
        ax1.grid(True, alpha=0.3)
        ax1.axhline(self.wt.get_float(2.5), color="cyan", lw=1, ls="--",
                   label="WT")
        ax1.legend(fontsize=8)

        ax2 = self.fig.add_subplot(1, 2, 2)
        sub = res.settlement.sublayers
        if sub:
            z_mid = [0.5*(s["z_top"]+s["z_bot"]) for s in sub]
            dsig = [s["delta_sigma_kPa"] for s in sub]
            ax2.barh(z_mid, dsig, height=0.4, color="#1f497d")
            ax2.set_xlabel("Δσ_z [kPa]")
            ax2.set_ylabel("Depth [m]")
            ax2.invert_yaxis()
            ax2.set_title("Stress increment")
            ax2.grid(True, alpha=0.3, axis="x")
        self.fig.tight_layout()


# ---------------------------------------------------------------------------
# Retaining wall page
# ---------------------------------------------------------------------------

class RetainingWallPage(BasePage):
    title = "Retaining wall"

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        f = self.form_frame
        self.H = LabeledEntry(f, "Stem H (m)", "5.0")
        self.stem_top = LabeledEntry(f, "Stem top (m)", "0.30")
        self.stem_bot = LabeledEntry(f, "Stem bottom (m)", "0.45")
        self.toe = LabeledEntry(f, "Toe (m)", "1.0")
        self.heel = LabeledEntry(f, "Heel (m)", "2.5")
        self.base_t = LabeledEntry(f, "Base thickness (m)", "0.55")
        self.phi_f = LabeledEntry(f, "Backfill phi (deg)", "33")
        self.gamma_f = LabeledEntry(f, "Backfill gamma", "19")
        self.phi_g = LabeledEntry(f, "Foundation phi", "36")
        self.gamma_g = LabeledEntry(f, "Foundation gamma", "20")
        self.q = LabeledEntry(f, "Surcharge (kPa)", "10")
        self.hw = LabeledEntry(f, "Water height (m)", "0")
        self.da = LabeledCombobox(f, "Design Approach",
                                 ["DA1-C1", "DA1-C2", "DA2", "DA3"],
                                 default="DA2")
        for i, w in enumerate([self.H, self.stem_top, self.stem_bot,
                              self.toe, self.heel, self.base_t,
                              self.phi_f, self.gamma_f, self.phi_g, self.gamma_g,
                              self.q, self.hw, self.da]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.codes.eurocode7 import DesignApproach
        from foundationdesignjm.core.material import Concrete
        from foundationdesignjm.core.soil import SoilLayer, SoilType
        from foundationdesignjm.design.retaining_wall import (
            CantileverWallDesigner, CantileverWallGeometry, RetainingWallLoading,
        )

        geo = CantileverWallGeometry(
            H=self.H.get_float(5),
            stem_top=self.stem_top.get_float(0.30),
            stem_bottom=self.stem_bot.get_float(0.45),
            toe=self.toe.get_float(1.0),
            heel=self.heel.get_float(2.5),
            base_thickness=self.base_t.get_float(0.55),
            embedment_front=0.8,
        )
        backfill = SoilLayer(name="fill", thickness=10,
                            soil_type=SoilType.COHESIONLESS,
                            friction_angle=self.phi_f.get_float(33),
                            unit_weight=self.gamma_f.get_float(19))
        foundation = SoilLayer(name="found", thickness=10,
                              soil_type=SoilType.COHESIONLESS,
                              friction_angle=self.phi_g.get_float(36),
                              unit_weight=self.gamma_g.get_float(20))
        load = RetainingWallLoading(
            backfill=backfill, foundation_soil=foundation,
            surcharge_q=self.q.get_float(10),
            water_height=self.hw.get_float(0),
            use_coulomb=True, delta_over_phi=2/3,
        )
        da_map = {"DA1-C1": DesignApproach.DA1_C1, "DA1-C2": DesignApproach.DA1_C2,
                 "DA2": DesignApproach.DA2, "DA3": DesignApproach.DA3}
        des = CantileverWallDesigner(geo, load, Concrete(fck=30),
                                     design_approach=da_map[self.da.get()])
        res = des.check()

        out = self.output
        out.writeln(f"==== ULS ({res.design_approach}) ====", tag="title")
        out.writeln(f"  B = {geo.B:.2f} m   e_x = {res.actions.e_x:+.3f} m   "
                   f"middle-third: {res.middle_third}")
        for label, util in [
            ("Bearing", res.bearing_utilization),
            ("Sliding", res.sliding_utilization),
            ("Overturning", res.overturning_utilization),
        ]:
            out.writeln(f"  {label:<13} util = {util*100:>5.1f}%",
                       tag="ok" if util <= 1.0 else "fail")
        out.writeln()
        out.writeln("==== STRUCTURAL FORCES (per m run) ====", tag="title")
        out.writeln(f"  Stem base: M = {res.M_stem_base:>6.1f} kN.m/m   "
                   f"V = {res.V_stem_base:>6.1f} kN/m")
        out.writeln(f"  Heel     : M = {res.M_heel:>6.1f} kN.m/m   "
                   f"V = {res.V_heel:>6.1f} kN/m")
        out.writeln(f"  Toe      : M = {res.M_toe:>6.1f} kN.m/m   "
                   f"V = {res.V_toe:>6.1f} kN/m")

        # Plot: wall geometry
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_aspect("equal")
        toe = geo.toe; sb = geo.stem_bottom; heel_l = geo.heel
        Hs = geo.H; t = geo.base_thickness
        ax.fill([0, geo.B, geo.B, 0], [0, 0, t, t], color="#cccccc", edgecolor="black")
        x0 = toe
        x1 = toe + sb
        ax.fill([x0, x1, x1 - (sb - geo.stem_top),
                x0 + (sb - geo.stem_top)/2],
               [t, t, t + Hs, t + Hs], color="#bbbbbb", edgecolor="black")
        ax.annotate("", xy=(geo.B + 0.3, t + Hs/2), xytext=(geo.B, t + Hs/2),
                   arrowprops=dict(arrowstyle="->", color="red"))
        ax.text(geo.B + 0.3, t + Hs/2 + 0.1,
                f"H={res.actions.H_d:.0f} kN/m", color="red", fontsize=8)
        ax.set_xlim(-0.5, geo.B + 2)
        ax.set_ylim(-0.5, t + Hs + 0.5)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title(f"Wall geometry  (B = {geo.B:.2f} m)")
        ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# EC8 spectrum page
# ---------------------------------------------------------------------------

class EC8SpectrumPage(BasePage):
    title = "EC8 design spectrum"

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        from foundationdesignjm.codes.eurocode8 import SEISMIC_ZONES, list_zones
        f = self.form_frame
        countries = list(SEISMIC_ZONES.keys())
        self.country = LabeledCombobox(f, "Country", countries, default="ES")
        self.region_var = tk.StringVar(value="Granada")
        ttk.Label(f, text="Region", width=22, anchor="w").grid(row=1, column=0,
                                                              sticky="w")
        self.region_combo = ttk.Combobox(f, textvariable=self.region_var,
                                        values=list_zones("ES"),
                                        state="readonly", width=18)
        self.region_combo.grid(row=1, column=0, sticky="w", padx=(165, 0))
        self.country.combo.bind("<<ComboboxSelected>>", self._on_country_change)
        self.ground = LabeledCombobox(f, "Ground type",
                                     ["A", "B", "C", "D", "E"], default="C")
        self.importance = LabeledCombobox(f, "Importance",
                                         ["I", "II", "III", "IV"], default="II")
        self.q = LabeledEntry(f, "Behaviour q", "3.0")
        for i, w in enumerate([self.country, self.ground, self.importance, self.q]):
            row = i if i == 0 else i + 1
            w.grid(row=row, column=0, sticky="w", pady=1)

    def _on_country_change(self, _evt) -> None:
        from foundationdesignjm.codes.eurocode8 import list_zones
        zones = list_zones(self.country.get())
        self.region_combo["values"] = zones
        if zones:
            self.region_var.set(zones[0])

    def run(self) -> None:
        from foundationdesignjm.codes.eurocode8 import (
            GroundType, ImportanceClass, build_design_spectrum,
        )

        ds = build_design_spectrum(
            country=self.country.get(),
            region=self.region_var.get(),
            ground_type=GroundType(self.ground.get()),
            importance_class=ImportanceClass(self.importance.get()),
            behaviour_factor_q=self.q.get_float(3.0),
        )
        out = self.output
        out.writeln(f"==== EC8-1 SPECTRUM ====", tag="title")
        out.writeln(f"  Site: {ds.country} / {ds.region}")
        out.writeln(f"  Ground type {ds.ground_type.value},  spectrum type {ds.spectrum_type.value}")
        out.writeln(f"  a_gR = {ds.a_gR_g:.3f} g,  gamma_I = {ds.gamma_I},  "
                   f"a_g = {ds.a_g_g:.3f}")
        out.writeln(f"  S = {ds.spectrum_params.S},  T_B = {ds.spectrum_params.T_B} s,  "
                   f"T_C = {ds.spectrum_params.T_C} s,  T_D = {ds.spectrum_params.T_D} s")
        out.writeln()
        out.writeln("   T (s)   S_e/g    S_d/g", tag="title")
        for T in [0.0, 0.1, 0.2, 0.4, 0.6, 1.0, 1.5, 2.0, 3.0]:
            out.writeln(f"   {T:>4.2f}   {ds.S_e(T):>6.4f}   {ds.S_d(T):>6.4f}")

        # Plot
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        T = np.linspace(0.01, 4.0, 200)
        Se = np.array([ds.S_e(t) for t in T])
        Sd = np.array([ds.S_d(t) for t in T])
        ax.plot(T, Se, "b-", lw=1.6, label="S_e (elastic)")
        ax.plot(T, Sd, "r-", lw=1.6, label=f"S_d (design, q={ds.behaviour_factor_q})")
        ax.set_xlabel("Period T [s]")
        ax.set_ylabel("S / g")
        ax.set_title(f"EC8 spectrum  {ds.region}  (a_gR = {ds.a_gR_g:.3f} g)")
        ax.legend()
        ax.grid(True, alpha=0.3)


__all__ = [
    "BasePage",
    "CustomFootingPage",
    "CptPipelinePage",
    "RetainingWallPage",
    "EC8SpectrumPage",
]
