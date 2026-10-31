"""Extra designer pages added to expose the remaining backend modules.

Pages added (all subclass `BasePage`):

- CranePage             — tower-crane foundation (in_service / out_of_service envelope)
- PileLateralPage       — laterally loaded pile (p-y curves)
- PileCapPage           — 2/3/4-pile cap strut-and-tie
- StrapBeamPage         — tie/strap beam between two footings
- StrengtheningPage     — micropile underpinning + angular distortion + enlargement
- SeismicFootingPage    — EN 1998-5 spread footing check
- SptPage               — SPT correlations (φ', c_u, E, D_R) along a borehole
- MultiLayerBcPage      — Meyerhof-Hanna multi-layer bearing capacity
- FailureModePage       — Vesic rigidity-index failure-mode classifier
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List

import numpy as np

from .pages import BasePage
from .widgets import LabeledCombobox, LabeledEntry


# ---------------------------------------------------------------------------
# Tower crane foundation
# ---------------------------------------------------------------------------

class CranePage(BasePage):
    title = "Tower crane foundation"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.B = LabeledEntry(f, "B (pad, m)", "5.0")
        self.L = LabeledEntry(f, "L (pad, m)", "5.0")
        self.H = LabeledEntry(f, "h (pad thickness, m)", "1.2")
        self.emb = LabeledEntry(f, "Embedment (m)", "1.5")
        self.col = LabeledEntry(f, "Mast side (m)", "1.0")
        self.phi = LabeledEntry(f, "Soil phi' (deg)", "32")
        self.gamma = LabeledEntry(f, "Soil gamma (kN/m3)", "19")
        self.fck = LabeledEntry(f, "Concrete fck (MPa)", "30")
        self.dyn = LabeledEntry(f, "Dynamic factor", "1.20")
        self.N_serv = LabeledEntry(f, "Service N (kN)", "1500")
        self.M_serv = LabeledEntry(f, "Service M (kN.m)", "4500")
        self.V_serv = LabeledEntry(f, "Service V (kN)", "120")
        self.N_oos = LabeledEntry(f, "OOS N (kN)", "1100")
        self.M_oos = LabeledEntry(f, "OOS M (kN.m)", "8500")
        self.V_oos = LabeledEntry(f, "OOS V (kN)", "260")
        widgets = [self.B, self.L, self.H, self.emb, self.col, self.phi, self.gamma,
                   self.fck, self.dyn, self.N_serv, self.M_serv, self.V_serv,
                   self.N_oos, self.M_oos, self.V_oos]
        for i, w in enumerate(widgets):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationcalc.analysis.crane import (
            CraneLoadCase, CraneLoadState, design_envelope,
        )
        from foundationcalc.codes.eurocode7 import DesignApproach
        from foundationcalc.core.geometry import Column, RectangularFoundation
        from foundationcalc.core.material import Concrete
        from foundationcalc.core.soil import SoilLayer, SoilType

        B = self.B.get_float(5.0)
        L = self.L.get_float(5.0)
        H = self.H.get_float(1.2)
        emb = self.emb.get_float(1.5)
        a = self.col.get_float(1.0)
        fdn = RectangularFoundation(length=L * 1000, width=B * 1000,
                                    thickness=H * 1000, embedment_depth=emb * 1000)
        col = Column(length=a * 1000, width=a * 1000, pos_x=L * 500, pos_y=B * 500)
        concrete = Concrete(name=f"C{int(self.fck.get_float(30))}",
                            fck=self.fck.get_float(30))
        soil = SoilLayer(name="bearing", thickness=10,
                         soil_type=SoilType.COHESIONLESS,
                         friction_angle=self.phi.get_float(32), cohesion=0.0,
                         unit_weight=self.gamma.get_float(19),
                         youngs_modulus=40.0)
        dyn = self.dyn.get_float(1.20)
        lcs = [
            CraneLoadCase(state=CraneLoadState.SERVICE, name="in-service",
                          N_kN=self.N_serv.get_float(1500),
                          M_x_kNm=self.M_serv.get_float(4500),
                          V_x_kN=self.V_serv.get_float(120),
                          dynamic_factor=dyn),
            CraneLoadCase(state=CraneLoadState.OUT_OF_SERVICE, name="storm",
                          N_kN=self.N_oos.get_float(1100),
                          M_x_kNm=self.M_oos.get_float(8500),
                          V_x_kN=self.V_oos.get_float(260),
                          is_wind_dominant=True),
        ]
        results = design_envelope(
            foundation=fdn, column=col, load_cases=lcs,
            soil=soil, concrete=concrete,
            design_approaches=[DesignApproach.DA2, DesignApproach.DA3],
        )

        o = self.output
        o.writeln("==== TOWER CRANE FOUNDATION ENVELOPE ====", tag="title")
        o.writeln(f"  Pad {B:.1f} x {L:.1f} x {H:.2f} m  (D = {emb:.1f} m)")
        o.writeln("")
        for r in results:
            tag = "ok" if r.all_ok else "fail"
            o.writeln(f"  {r.load_case:>14}  /  {r.design_approach}", tag="title")
            o.writeln(f"     e_x={r.e_x:+.3f} m  regime={r.regime}  "
                      f"uplift={r.uplift}")
            o.writeln(f"     bearing  util = {r.bearing_utilization*100:5.1f}%")
            o.writeln(f"     sliding  util = {r.sliding_utilization*100:5.1f}%")
            o.writeln(f"     overturn util = {r.overturning_utilization*100:5.1f}%",
                      tag=tag)
            o.writeln("")

        # Plot — utilisation per case (bar chart)
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        labels = [f"{r.load_case[:6]}\n{r.design_approach}" for r in results]
        x = np.arange(len(labels))
        bearing = [r.bearing_utilization * 100 for r in results]
        sliding = [r.sliding_utilization * 100 for r in results]
        overturn = [r.overturning_utilization * 100 for r in results]
        w = 0.27
        ax.bar(x - w, bearing, w, label="bearing", color="#1f77b4")
        ax.bar(x, sliding, w, label="sliding", color="#ff7f0e")
        ax.bar(x + w, overturn, w, label="overturning", color="#2ca02c")
        ax.axhline(100, color="red", linestyle="--", lw=1)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel("Utilization (%)")
        ax.set_title("Crane foundation — utilisation envelope")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Pile lateral analysis (p-y)
# ---------------------------------------------------------------------------

class PileLateralPage(BasePage):
    title = "Pile lateral (p-y)"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.L = LabeledEntry(f, "Length (m)", "12.0")
        self.D = LabeledEntry(f, "Diameter (m)", "0.6")
        self.EI = LabeledEntry(f, "EI (kN.m2)", "120000")
        self.H = LabeledEntry(f, "Head shear H (kN)", "60")
        self.M = LabeledEntry(f, "Head moment M (kN.m)", "0")
        self.curve = LabeledCombobox(f, "p-y curve",
                                     ["api_sand", "reese_sand", "api_clay",
                                      "matlock_soft_clay"], default="api_sand")
        self.phi = LabeledEntry(f, "phi (deg, sand)", "32")
        self.cu = LabeledEntry(f, "c_u (kPa, clay)", "60")
        self.gamma = LabeledEntry(f, "gamma' (kN/m3)", "10")
        self.fixed = LabeledCombobox(f, "Head fixity", ["free", "fixed"],
                                     default="free")
        widgets = [self.L, self.D, self.EI, self.H, self.M, self.curve,
                   self.phi, self.cu, self.gamma, self.fixed]
        for i, w in enumerate(widgets):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationcalc.analysis.pile_lateral import (
            PYSoilLayer, PYType, PileLateral, solve_pile_lateral,
        )
        L = self.L.get_float(12.0)
        py_key = self.curve.get()
        layer = PYSoilLayer(
            z_top_m=0.0, z_bot_m=max(L, 0.01),
            py_type=PYType(py_key),
            c_u_kPa=self.cu.get_float(60),
            phi_deg=self.phi.get_float(32),
            gamma_eff_kN_m3=self.gamma.get_float(10),
        )
        pile = PileLateral(
            length_m=L,
            diameter_m=self.D.get_float(0.6),
            EI_kNm2=self.EI.get_float(120000),
            layers=[layer],
            head_load_H_kN=self.H.get_float(60),
            head_moment_M_kNm=self.M.get_float(0),
            fixed_head=(self.fixed.get() == "fixed"),
        )
        res = solve_pile_lateral(pile)
        o = self.output
        o.writeln("==== LATERAL PILE (p-y FD solver) ====", tag="title")
        o.writeln(f"  Head deflection  = {res.y_head_mm:.2f} mm")
        o.writeln(f"  Max bending moment = {res.M_max_kNm:.1f} kN.m")
        o.writeln(f"  Max shear          = {res.V_max_kN:.1f} kN")
        # Plots: deflection / moment / shear vs depth
        self.fig.clear()
        ax1 = self.fig.add_subplot(1, 3, 1)
        ax2 = self.fig.add_subplot(1, 3, 2, sharey=ax1)
        ax3 = self.fig.add_subplot(1, 3, 3, sharey=ax1)
        ax1.plot(res.y_m * 1000, res.z, "b-", lw=1.5)
        ax1.invert_yaxis()
        ax1.set_xlabel("y [mm]")
        ax1.set_ylabel("z [m]")
        ax1.set_title("Deflection")
        ax1.grid(True, alpha=0.3)
        ax2.plot(res.M_kNm, res.z, "r-", lw=1.5)
        ax2.set_xlabel("M [kN.m]")
        ax2.set_title("Moment")
        ax2.grid(True, alpha=0.3)
        ax3.plot(res.V_kN, res.z, "g-", lw=1.5)
        ax3.set_xlabel("V [kN]")
        ax3.set_title("Shear")
        ax3.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Pile cap (strut-and-tie)
# ---------------------------------------------------------------------------

class PileCapPage(BasePage):
    title = "Pile cap (strut-and-tie)"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.kind = LabeledCombobox(f, "Layout", ["2 piles", "3 piles (equil.)",
                                                  "4 piles (rect.)"],
                                    default="2 piles")
        self.N = LabeledEntry(f, "N_Ed (kN)", "3000")
        self.v = LabeledEntry(f, "v (mm)  [2p]", "750")
        self.a = LabeledEntry(f, "Column a (mm)", "400")
        self.d = LabeledEntry(f, "d effective (mm)", "750")
        self.l_eq = LabeledEntry(f, "l side (mm) [3p]", "1800")
        self.l1 = LabeledEntry(f, "l1 (mm) [4p]", "1800")
        self.l2 = LabeledEntry(f, "l2 (mm) [4p]", "1800")
        self.a1 = LabeledEntry(f, "a1 (mm) [4p]", "400")
        self.a2 = LabeledEntry(f, "a2 (mm) [4p]", "400")
        self.fyk = LabeledEntry(f, "Steel fyk", "500")
        for i, w in enumerate([self.kind, self.N, self.v, self.a, self.d,
                               self.l_eq, self.l1, self.l2, self.a1, self.a2,
                               self.fyk]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationcalc.core.material import ReinforcingSteel
        from foundationcalc.design.pile_cap import (
            cap_four_piles, cap_three_piles, cap_two_piles,
            pile_cap_secondary_vertical,
        )
        steel = ReinforcingSteel(fyk=self.fyk.get_float(500))
        N = self.N.get_float(3000)
        d = self.d.get_float(750)
        kind = self.kind.get()
        o = self.output
        o.writeln(f"==== PILE CAP — {kind} ====", tag="title")
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_aspect("equal")

        if kind.startswith("2"):
            v = self.v.get_float(750)
            a = self.a.get_float(400)
            res = cap_two_piles(N, v, a, d, steel)
            o.writeln(f"  T_d = {res.T_d/1000:.0f} kN")
            o.writeln(f"  A_s required = {res.A_s:.0f} mm2")
            o.writeln(f"  Secondary  = {res.secondary_min:.0f} mm2")
            o.writeln("  " + res.note, tag="muted")
            # plan plot — 2 piles
            ax.scatter([-v/1000, v/1000], [0, 0], s=400, c="#1f77b4",
                       edgecolors="black", zorder=5)
            ax.add_patch(self._col_rect(-a/2000, -a/2000, a/1000, a/1000))
            ax.set_xlim(-v/1000 - 0.6, v/1000 + 0.6)
            ax.set_ylim(-0.6, 0.6)
            ax.set_title("2-pile cap (plan)")
        elif kind.startswith("3"):
            l_side = self.l_eq.get_float(1800)
            a = self.a.get_float(400)
            res = cap_three_piles(N, l_side, a, d, steel)
            o.writeln(f"  T_d = {res.T_d/1000:.0f} kN  per tie strip")
            o.writeln(f"  A_s required = {res.A_s:.0f} mm2  per tie")
            o.writeln(f"  Secondary  = {res.secondary_min:.0f} mm2")
            # Equilateral triangle plan
            l_m = l_side / 1000
            cx = [0.0, l_m, 0.5 * l_m]
            cy = [0.0, 0.0, (3 ** 0.5) / 2 * l_m]
            ax.scatter(cx, cy, s=400, c="#1f77b4", edgecolors="black", zorder=5)
            cent = (sum(cx) / 3.0, sum(cy) / 3.0)
            ax.add_patch(self._col_rect(cent[0] - a/2000, cent[1] - a/2000,
                                        a/1000, a/1000))
            ax.set_xlim(-0.4, l_m + 0.4)
            ax.set_ylim(-0.4, (3 ** 0.5) / 2 * l_m + 0.4)
            ax.set_title("3-pile cap (equilateral plan)")
        else:
            l1 = self.l1.get_float(1800)
            l2 = self.l2.get_float(1800)
            a1 = self.a1.get_float(400)
            a2 = self.a2.get_float(400)
            r1, r2 = cap_four_piles(N, l1, l2, a1, a2, d, steel)
            o.writeln(f"  Direction 1: T_d = {r1.T_d/1000:.0f} kN, "
                      f"A_s = {r1.A_s:.0f} mm2")
            o.writeln(f"  Direction 2: T_d = {r2.T_d/1000:.0f} kN, "
                      f"A_s = {r2.A_s:.0f} mm2")
            F_min_N = pile_cap_secondary_vertical(N, n_piles=4)
            o.writeln(f"  Secondary vertical (per pile, n=4): "
                      f"{F_min_N/1000:.1f} kN")
            # 4 piles plan
            x1, y1 = l1 / 2000, l2 / 2000
            ax.scatter([-x1, x1, x1, -x1], [-y1, -y1, y1, y1], s=400,
                       c="#1f77b4", edgecolors="black", zorder=5)
            ax.add_patch(self._col_rect(-a1/2000, -a2/2000, a1/1000, a2/1000))
            ax.set_xlim(-x1 - 0.6, x1 + 0.6)
            ax.set_ylim(-y1 - 0.6, y1 + 0.6)
            ax.set_title("4-pile cap (rectangular plan)")
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")

    @staticmethod
    def _col_rect(x, y, w, h):
        from matplotlib.patches import Rectangle
        return Rectangle((x, y), w, h, facecolor="#cccccc",
                         edgecolor="black", lw=1.2, zorder=3)


# ---------------------------------------------------------------------------
# Strap (tie) beam
# ---------------------------------------------------------------------------

class StrapBeamPage(BasePage):
    title = "Strap / tie beam"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.N1 = LabeledEntry(f, "N1 (kN)", "1200")
        self.N2 = LabeledEntry(f, "N2 (kN)", "1800")
        self.L = LabeledEntry(f, "Length (mm)", "6000")
        self.ecc = LabeledEntry(f, "Eccentricity e (mm)", "400")
        self.q = LabeledEntry(f, "Self weight (kN/m)", "10")
        self.aS = LabeledEntry(f, "alpha*S (EC8)", "0.30")
        self.ground = LabeledCombobox(f, "Ground type",
                                      ["A", "B", "C", "D", "E"], default="B")
        self.storeys = LabeledEntry(f, "Storeys above basem.", "4")
        for i, w in enumerate([self.N1, self.N2, self.L, self.ecc, self.q,
                               self.aS, self.ground, self.storeys]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationcalc.design.strap_beam import (
            GroundType, seismic_tie_force, strap_for_two_footings,
            tie_beam_minimum_dimensions,
        )
        spec = strap_for_two_footings(
            N1_kN=self.N1.get_float(1200),
            N2_kN=self.N2.get_float(1800),
            length_mm=self.L.get_float(6000),
            eccentricity_mm=self.ecc.get_float(400),
            q_self_kNm=self.q.get_float(10),
        )
        N_max = max(self.N1.get_float(1200), self.N2.get_float(1800))
        T_seismic = seismic_tie_force(
            N_max, alpha_S=self.aS.get_float(0.30),
            ground_type=GroundType(self.ground.get()),
        )
        b_min, h_min = tie_beam_minimum_dimensions(self.storeys.get_int(4))
        o = self.output
        o.writeln("==== STRAP / TIE BEAM ====", tag="title")
        o.writeln(f"  b x h proposed = {spec.width_mm:.0f} x {spec.depth_mm:.0f} mm")
        o.writeln(f"  N1, N2  = {self.N1.get_float(1200):.0f},  "
                  f"{self.N2.get_float(1800):.0f} kN")
        o.writeln(f"  T_axial (struct) = {spec.design_axial_kN:.1f} kN")
        o.writeln(f"  V_design  = {spec.design_shear_kN:.1f} kN")
        o.writeln(f"  M_design  = {spec.design_moment_kNm:.1f} kN.m")
        o.writeln(f"  T_seismic (EC8) = +/- {T_seismic:.0f} kN", tag="title")
        o.writeln(f"  Min b x h (EC8) = {b_min:.0f} x {h_min:.0f} mm")
        o.writeln("  " + spec.note, tag="muted")

        # Plot — bending & shear diagram (simple)
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        L_m = self.L.get_float(6000) / 1000.0
        x = np.linspace(0, L_m, 51)
        # parabolic UDL bending + linear from end moments
        q = self.q.get_float(10)
        M_par = q * L_m / 2.0 * x - q * x ** 2 / 2.0
        M_total = M_par + spec.design_moment_kNm  # constant offset for end moment
        ax.plot(x, M_total, "b-", lw=1.6, label="M [kN.m]")
        ax.fill_between(x, M_total, 0, color="b", alpha=0.15)
        ax.set_xlabel("Position along strap [m]")
        ax.set_ylabel("M [kN.m]")
        ax.set_title("Strap beam bending diagram")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)


# ---------------------------------------------------------------------------
# Strengthening (underpinning + angular distortion + enlargement)
# ---------------------------------------------------------------------------

class StrengtheningPage(BasePage):
    title = "Strengthening / underpinning"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        # micropile
        ttk.Label(f, text="--- Micropile ---", foreground="#1f497d",
                  font=("Segoe UI", 9, "bold")).grid(row=0, column=0,
                                                     sticky="w", pady=(0, 2))
        self.dd = LabeledEntry(f, "Drilling dia. (m)", "0.18")
        self.ds = LabeledEntry(f, "Grouted dia. (m)", "0.22")
        self.Ltot = LabeledEntry(f, "Total length (m)", "9.0")
        self.Lbond = LabeledEntry(f, "Bond length (m)", "5.0")
        self.soil = LabeledCombobox(f, "Soil type",
                                    ["sand_gravel", "sand", "clay",
                                     "marl_limestone", "weathered_rock"],
                                    default="sand")
        self.qs = LabeledEntry(f, "q_s (kPa, optional)", "")
        # group
        self.n_piles = LabeledEntry(f, "n (group)", "6")
        self.sd = LabeledEntry(f, "Spacing s/d", "3.0")
        self.N_design = LabeledEntry(f, "N_design (kN)", "1200")
        # angular distortion
        ttk.Label(f, text="--- Distortion ---", foreground="#1f497d",
                  font=("Segoe UI", 9, "bold")).grid(row=10, column=0,
                                                     sticky="w", pady=(8, 2))
        self.delta_s = LabeledEntry(f, "Diff. settl. (mm)", "12")
        self.L_AB = LabeledEntry(f, "L_AB (m)", "6")
        self.struct = LabeledCombobox(f, "Structure",
                                      ["isostatic", "retaining_wall",
                                       "frame_partitions", "precast_panels",
                                       "masonry_sagging", "masonry_hogging"],
                                      default="frame_partitions")
        # enlargement
        ttk.Label(f, text="--- Enlargement ---", foreground="#1f497d",
                  font=("Segoe UI", 9, "bold")).grid(row=15, column=0,
                                                     sticky="w", pady=(8, 2))
        self.N_total = LabeledEntry(f, "N total (kN)", "2000")
        self.A_old = LabeledEntry(f, "A_old (m2)", "2.25")
        self.B_new = LabeledEntry(f, "B_new (m)", "2.5")
        self.L_new = LabeledEntry(f, "L_new (m)", "2.5")

        order = [self.dd, self.ds, self.Ltot, self.Lbond, self.soil, self.qs,
                 self.n_piles, self.sd, self.N_design]
        for i, w in enumerate(order, start=1):
            w.grid(row=i, column=0, sticky="w", pady=1)
        for i, w in enumerate([self.delta_s, self.L_AB, self.struct], start=11):
            w.grid(row=i, column=0, sticky="w", pady=1)
        for i, w in enumerate([self.N_total, self.A_old, self.B_new, self.L_new],
                              start=16):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationcalc.design.strengthening import (
            MicropileGeometry, MicropileSoilType, StructureType,
            angular_distortion_check, enlarged_footing_pressure,
            micropile_capacity, micropile_group_capacity,
        )
        qs_raw = self.qs.get()
        try:
            qs_kPa = float(qs_raw.replace(",", ".")) if qs_raw.strip() else None
        except (ValueError, AttributeError):
            qs_kPa = None
        geom = MicropileGeometry(
            diameter_drilling=self.dd.get_float(0.18),
            diameter_grouted=self.ds.get_float(0.22),
            length_total=self.Ltot.get_float(9.0),
            length_bond=self.Lbond.get_float(5.0),
        )
        m = micropile_capacity(geom, MicropileSoilType(self.soil.get()),
                               q_s_kPa=qs_kPa)
        g = micropile_group_capacity(
            n_piles=self.n_piles.get_int(6),
            R_per_pile_design_kN=m.R_total_design,
            spacing_to_diameter=self.sd.get_float(3.0),
            N_design_kN=self.N_design.get_float(1200),
        )
        ad = angular_distortion_check(
            delta_s_AB_mm=self.delta_s.get_float(12),
            L_AB_m=self.L_AB.get_float(6),
            structure_type=StructureType(self.struct.get()),
        )
        enl = enlarged_footing_pressure(
            N_kN=self.N_total.get_float(2000),
            A_old_m2=self.A_old.get_float(2.25),
            new_width_m=self.B_new.get_float(2.5),
            new_length_m=self.L_new.get_float(2.5),
        )

        o = self.output
        o.writeln("==== MICROPILE (Bustamante-Doix) ====", tag="title")
        o.writeln(f"  q_s used   = {m.q_s_used:.1f} kPa")
        o.writeln(f"  R_skin_ck  = {m.R_skin_char:.0f} kN")
        o.writeln(f"  R_design   = {m.R_total_design:.0f} kN (per micropile)")
        o.writeln(f"  Group: E = {g.efficiency_E:.2f}, "
                  f"R_group = {g.R_group_design:.0f} kN, "
                  f"util = {g.utilization*100:.1f}%",
                  tag="ok" if g.ok else "fail")

        o.writeln("\n==== ANGULAR DISTORTION (CTE-DB-SE-C) ====", tag="title")
        o.writeln(f"  beta = {ad.beta:.4f}   limit = {ad.beta_limit:.4f}")
        o.writeln(f"  util = {ad.utilization*100:.1f}%",
                  tag="ok" if ad.ok else "fail")

        o.writeln("\n==== FOOTING ENLARGEMENT ====", tag="title")
        o.writeln(f"  q_old = {enl.q_old:.1f} kPa  ->  "
                  f"q_new = {enl.q_new:.1f} kPa")
        o.writeln(f"  Pressure reduction = {enl.reduction_pct:.1f} %")
        o.writeln(f"  Interface shear required = "
                  f"{enl.interface_shear_required:.1f} kPa")

        # Plot — Bustamante-Doix capacity vs bond length
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        Lb = np.linspace(1.1, 10.0, 30)
        R = []
        for lb in Lb:
            g2 = MicropileGeometry(
                diameter_drilling=geom.diameter_drilling,
                diameter_grouted=geom.diameter_grouted,
                length_total=geom.length_total,
                length_bond=lb,
            )
            R.append(micropile_capacity(
                g2, MicropileSoilType(self.soil.get()), q_s_kPa=qs_kPa,
            ).R_total_design)
        ax.plot(Lb, R, "b-", lw=1.6)
        ax.axhline(self.N_design.get_float(1200) / max(self.n_piles.get_int(6), 1),
                   color="red", linestyle="--", label="Demand / pile")
        ax.set_xlabel("Bond length L_bond [m]")
        ax.set_ylabel("R_design [kN]")
        ax.set_title("Micropile design capacity vs bond length")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)


# ---------------------------------------------------------------------------
# Seismic footing (EN 1998-5)
# ---------------------------------------------------------------------------

class SeismicFootingPage(BasePage):
    title = "Seismic footing (EN 1998-5)"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.B = LabeledEntry(f, "B (m)", "3.0")
        self.L = LabeledEntry(f, "L (m)", "3.0")
        self.H = LabeledEntry(f, "h (m)", "0.8")
        self.emb = LabeledEntry(f, "D (m)", "1.5")
        self.phi = LabeledEntry(f, "phi' (deg)", "32")
        self.gamma = LabeledEntry(f, "gamma (kN/m3)", "19")
        self.N = LabeledEntry(f, "N seismic (kN)", "900")
        self.H_load = LabeledEntry(f, "V (kN)", "150")
        self.M = LabeledEntry(f, "M (kN.m)", "350")
        self.ag = LabeledEntry(f, "a_g/g", "0.25")
        self.S = LabeledEntry(f, "S (EC8)", "1.20")
        self.r = LabeledEntry(f, "r factor", "1.0")
        self.gamma_I = LabeledEntry(f, "gamma_I", "1.0")
        for i, w in enumerate([self.B, self.L, self.H, self.emb, self.phi,
                               self.gamma, self.N, self.H_load, self.M,
                               self.ag, self.S, self.r, self.gamma_I]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationcalc.analysis.seismic_footing import (
            SeismicAction, seismic_footing_check,
        )
        from foundationcalc.codes.eurocode7 import DesignApproach
        from foundationcalc.core.geometry import Column, RectangularFoundation
        from foundationcalc.core.material import Concrete
        from foundationcalc.core.soil import SoilLayer, SoilType
        B = self.B.get_float(3.0)
        L = self.L.get_float(3.0)
        H = self.H.get_float(0.8)
        emb = self.emb.get_float(1.5)
        fdn = RectangularFoundation(length=L * 1000, width=B * 1000,
                                    thickness=H * 1000, embedment_depth=emb * 1000)
        col = Column(length=400, width=400, pos_x=L * 500, pos_y=B * 500)
        soil = SoilLayer(name="seismic_soil", thickness=10,
                         soil_type=SoilType.COHESIONLESS,
                         friction_angle=self.phi.get_float(32),
                         cohesion=0.0,
                         unit_weight=self.gamma.get_float(19),
                         youngs_modulus=40.0)
        concrete = Concrete(name="C30", fck=30)
        seismic = SeismicAction(
            a_g=self.ag.get_float(0.25),
            S=self.S.get_float(1.20),
            importance_factor_gamma_I=self.gamma_I.get_float(1.0),
            r_factor=self.r.get_float(1.0),
        )
        res = seismic_footing_check(
            foundation=fdn, column=col,
            N_kN=self.N.get_float(900),
            H_kN=self.H_load.get_float(150),
            M_kNm=self.M.get_float(350),
            soil=soil, concrete=concrete, seismic=seismic,
            design_approach=DesignApproach.DA3,
        )
        o = self.output
        o.writeln("==== SEISMIC FOOTING (EN 1998-5) ====", tag="title")
        o.writeln(f"  k_h = {seismic.k_h:.3f}   a_gR/g = {seismic.a_gR:.3f}")
        o.writeln(f"  N_d = {res.N_d:.0f} kN,  H_d = {res.H_d:.0f} kN,  "
                  f"M_d = {res.M_d:.0f} kN.m")
        o.writeln(f"  e_x = {res.e_x:.3f} m,  regime = {res.regime}")
        o.writeln(f"  bearing  util = {res.bearing_utilization*100:.1f}%",
                  tag="ok" if res.bearing_utilization <= 1 else "fail")
        o.writeln(f"  sliding  util = {res.sliding_utilization*100:.1f}%",
                  tag="ok" if res.sliding_utilization <= 1 else "fail")
        o.writeln(f"  overturn util = {res.overturning_utilization*100:.1f}%",
                  tag="ok" if res.overturning_utilization <= 1 else "fail")

        # Plot — utilisation envelope vs k_h
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        k_h_arr = np.linspace(0.0, 0.45, 16)
        b_arr = []; s_arr = []; o_arr = []
        for k_h in k_h_arr:
            # Build SeismicAction with k_h target — easiest: scale a_g
            ag_eff = k_h * seismic.r_factor / max(self.S.get_float(1.20)
                                                  * self.gamma_I.get_float(1.0), 1e-6)
            if ag_eff <= 0:
                ag_eff = 1e-6
            sa = SeismicAction(
                a_g=ag_eff, S=self.S.get_float(1.20),
                importance_factor_gamma_I=self.gamma_I.get_float(1.0),
                r_factor=self.r.get_float(1.0),
            )
            r2 = seismic_footing_check(
                foundation=fdn, column=col,
                N_kN=self.N.get_float(900),
                H_kN=self.H_load.get_float(150),
                M_kNm=self.M.get_float(350),
                soil=soil, concrete=concrete, seismic=sa,
                design_approach=DesignApproach.DA3,
            )
            b_arr.append(r2.bearing_utilization * 100)
            s_arr.append(r2.sliding_utilization * 100)
            o_arr.append(r2.overturning_utilization * 100)
        ax.plot(k_h_arr, b_arr, "b-o", lw=1.4, label="bearing")
        ax.plot(k_h_arr, s_arr, "r-^", lw=1.4, label="sliding")
        ax.plot(k_h_arr, o_arr, "g-s", lw=1.4, label="overturning")
        ax.axhline(100, color="black", linestyle="--", lw=1)
        ax.set_xlabel("k_h = a_g · S / r")
        ax.set_ylabel("Utilization (%)")
        ax.set_title("Seismic footing envelope")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)


# ---------------------------------------------------------------------------
# SPT correlations
# ---------------------------------------------------------------------------

class SptPage(BasePage):
    title = "SPT correlations"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.ER = LabeledEntry(f, "Energy ratio ER %", "60")
        self.PI = LabeledEntry(f, "Plasticity index PI", "20")
        self.gamma = LabeledEntry(f, "gamma' (kN/m3)", "10")
        self.spt_txt = tk.Text(f, height=14, width=34, font=("Consolas", 9))
        self.spt_txt.insert("1.0",
                            "depth_m,N_raw,soil\n"
                            "1.0, 6, sand\n2.5, 8, sand\n4.0,12, sand\n"
                            "6.0,18, sand\n8.0,22, sand\n10.0,30, sand\n"
                            "12.0,35, sand\n")
        for i, w in enumerate([self.ER, self.PI, self.gamma]):
            w.grid(row=i, column=0, sticky="w", pady=1)
        ttk.Label(f, text="SPT (depth_m,N_raw,soil):").grid(
            row=4, column=0, sticky="w", pady=(8, 2))
        self.spt_txt.grid(row=5, column=0, sticky="we", pady=2)

    def run(self) -> None:
        from foundationcalc.analysis.spt import (
            SPTReading, SoilTypeSPT, derive_parameters,
        )
        gamma = self.gamma.get_float(10)
        ER = self.ER.get_float(60)
        PI = self.PI.get_float(20)
        rows = []
        for line in self.spt_txt.get("1.0", "end").strip().splitlines()[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                continue
            depth = float(parts[0])
            N_raw = int(float(parts[1]))
            soil = SoilTypeSPT(parts[2])
            sigma_eff = gamma * depth
            rdg = SPTReading(depth_m=depth, N_raw=N_raw,
                             sigma_v0_eff_kPa=sigma_eff,
                             energy_ratio_ER=ER, soil_type=soil)
            rows.append(derive_parameters(rdg, plasticity_index=PI))
        if not rows:
            self.output.writeln("No valid SPT rows.", tag="fail")
            return
        o = self.output
        o.writeln("==== SPT CORRELATIONS ====", tag="title")
        o.writeln("  depth   N_raw  N_60  N_1(60)  phi'   c_u    E      D_R")
        for r in rows:
            phi_s = f"{r.phi_deg:.1f}" if r.phi_deg is not None else "  --"
            cu_s = f"{r.c_u_kPa:.0f}" if r.c_u_kPa is not None else "--"
            E_s = f"{r.E_MPa:.1f}" if r.E_MPa is not None else "--"
            Dr_s = f"{r.relative_density_pct:.0f}" if r.relative_density_pct is not None else "--"
            o.writeln(f"  {r.depth_m:5.1f}   {r.N_raw:4d}   "
                      f"{r.N_60:5.1f}  {r.N_1_60:5.1f}  "
                      f"{phi_s:>5}  {cu_s:>4}  {E_s:>5}  {Dr_s:>4}")
        # Plot — N vs depth (raw + corrected)
        self.fig.clear()
        ax1 = self.fig.add_subplot(1, 2, 1)
        ax2 = self.fig.add_subplot(1, 2, 2, sharey=ax1)
        depths = [r.depth_m for r in rows]
        N_raw_arr = [r.N_raw for r in rows]
        N1_60 = [r.N_1_60 for r in rows]
        phi_arr = [r.phi_deg if r.phi_deg is not None else float("nan") for r in rows]
        ax1.plot(N_raw_arr, depths, "ko-", lw=1.4, label="N_raw", mfc="white")
        ax1.plot(N1_60, depths, "b-^", lw=1.4, label="N_1(60)")
        ax1.invert_yaxis()
        ax1.set_xlabel("N")
        ax1.set_ylabel("Depth (m)")
        ax1.set_title("Raw & corrected N")
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=8)
        ax2.plot(phi_arr, depths, "r-s", lw=1.4, label="phi (Hatanaka)")
        ax2.set_xlabel("phi' (deg)")
        ax2.set_title("Derived phi")
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=8)


# ---------------------------------------------------------------------------
# Multi-layer bearing capacity (Meyerhof-Hanna)
# ---------------------------------------------------------------------------

class MultiLayerBcPage(BasePage):
    title = "Multi-layer bearing"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.B = LabeledEntry(f, "B (mm)", "2500")
        self.L = LabeledEntry(f, "L (mm)", "2500")
        self.H = LabeledEntry(f, "h (mm)", "600")
        self.emb = LabeledEntry(f, "Founding depth (mm)", "1500")
        self.gamma_w = LabeledEntry(f, "Water table (m)", "10")
        self.layers_txt = tk.Text(f, height=10, width=40,
                                  font=("Consolas", 9))
        self.layers_txt.insert(
            "1.0",
            "name,thickness_m,type,phi,c_kPa,cu_kPa,gamma\n"
            "fill,1.0,cohesionless,30,0,0,18\n"
            "dense_sand,3.0,cohesionless,38,0,0,20\n"
            "soft_clay,4.0,cohesive,0,5,40,17\n"
            "stiff_clay,5.0,cohesive,0,10,150,19\n")
        for i, w in enumerate([self.B, self.L, self.H, self.emb, self.gamma_w]):
            w.grid(row=i, column=0, sticky="w", pady=1)
        ttk.Label(f, text="Soil profile:").grid(
            row=6, column=0, sticky="w", pady=(8, 2))
        self.layers_txt.grid(row=7, column=0, sticky="we", pady=2)

    def run(self) -> None:
        from foundationcalc.analysis.multi_layer_bc import (
            multi_layer_bearing_capacity,
        )
        from foundationcalc.core.geometry import RectangularFoundation
        from foundationcalc.core.soil import SoilLayer, SoilProfile, SoilType

        fdn = RectangularFoundation(
            length=self.L.get_float(2500),
            width=self.B.get_float(2500),
            thickness=self.H.get_float(600),
            embedment_depth=self.emb.get_float(1500),
        )
        layers: List[SoilLayer] = []
        for line in self.layers_txt.get("1.0", "end").strip().splitlines()[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 7:
                continue
            soil_type = SoilType.COHESIONLESS if parts[2] == "cohesionless" else SoilType.COHESIVE
            layers.append(SoilLayer(
                name=parts[0],
                thickness=float(parts[1]),
                soil_type=soil_type,
                friction_angle=float(parts[3]),
                cohesion=float(parts[4]),
                undrained_shear_strength=float(parts[5]) if parts[5] else None,
                unit_weight=float(parts[6]),
            ))
        if not layers:
            self.output.writeln("No layers parsed.", tag="fail")
            return
        profile = SoilProfile(layers=layers,
                              water_table_depth=self.gamma_w.get_float(10))
        res = multi_layer_bearing_capacity(
            foundation=fdn, profile=profile,
            founding_depth_m=self.emb.get_float(1500) / 1000.0,
        )
        o = self.output
        o.writeln("==== MULTI-LAYER BEARING (Meyerhof-Hanna) ====", tag="title")
        o.writeln(f"  Layers in influence: {', '.join(res.layers_in_influence)}")
        o.writeln(f"  Governing case  = {res.governing_case}")
        o.writeln(f"  Governing layer = {res.governing_layer}")
        o.writeln(f"  q_ult           = {res.q_ult_kPa:.0f} kPa", tag="title")
        if res.bottom_strong_q_ult is not None:
            o.writeln(f"     q_ult top layer alone     = "
                      f"{res.bottom_strong_q_ult:.0f} kPa")
        if res.weak_layer_q_ult is not None:
            o.writeln(f"     q_ult weak layer (uncfd.) = "
                      f"{res.weak_layer_q_ult:.0f} kPa")
        if res.punching_q_ult is not None:
            o.writeln(f"     q_punching (Hanna-Meyerhof) = "
                      f"{res.punching_q_ult:.0f} kPa")

        # Plot — soil profile with q_ult bars
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        z = 0.0
        for layer in layers:
            colour = "#d4a373" if layer.soil_type == SoilType.COHESIONLESS else "#8a817c"
            ax.barh((z + z + layer.thickness) / 2.0, 1.0,
                    height=layer.thickness, color=colour, edgecolor="black",
                    align="center")
            ax.text(0.5, (z + z + layer.thickness) / 2.0,
                    f"{layer.name}\nphi={layer.friction_angle:.0f}, "
                    f"c_u={layer.undrained_shear_strength or 0:.0f}",
                    va="center", ha="center", fontsize=8)
            z += layer.thickness
        emb_m = self.emb.get_float(1500) / 1000.0
        ax.axhline(emb_m, color="red", linestyle="--",
                   label=f"founding plane = {emb_m:.2f} m")
        ax.invert_yaxis()
        ax.set_xticks([])
        ax.set_ylabel("Depth (m)")
        ax.set_title(f"q_ult = {res.q_ult_kPa:.0f} kPa  ({res.governing_case})")
        ax.legend(fontsize=8, loc="lower right")


# ---------------------------------------------------------------------------
# Failure-mode classifier (Vesic)
# ---------------------------------------------------------------------------

class FailureModePage(BasePage):
    title = "Failure mode (Vesic)"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.E = LabeledEntry(f, "E (kPa)", "30000")
        self.nu = LabeledEntry(f, "nu", "0.30")
        self.cprime = LabeledEntry(f, "c' (kPa)", "5")
        self.phi = LabeledEntry(f, "phi' (deg)", "32")
        self.qprime = LabeledEntry(f, "q' overburden (kPa)", "30")
        self.B = LabeledEntry(f, "B (m)", "2.5")
        self.L = LabeledEntry(f, "L (m)", "2.5")
        self.Nq = LabeledEntry(f, "N_q", "23.2")
        self.Dr = LabeledEntry(f, "Relative density %", "50")
        for i, w in enumerate([self.E, self.nu, self.cprime, self.phi,
                               self.qprime, self.B, self.L, self.Nq, self.Dr]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationcalc.analysis.failure_mode import classify_failure_mode
        res = classify_failure_mode(
            E_kPa=self.E.get_float(30000),
            nu=self.nu.get_float(0.30),
            c_prime_kPa=self.cprime.get_float(5),
            phi_deg=self.phi.get_float(32),
            q_prime_kPa=self.qprime.get_float(30),
            B_m=self.B.get_float(2.5),
            L_m=self.L.get_float(2.5),
            Nq=self.Nq.get_float(23.2),
            relative_density_pct=self.Dr.get_float(50),
        )
        o = self.output
        o.writeln("==== FAILURE-MODE CLASSIFIER (Vesic 1973) ====", tag="title")
        o.writeln(f"  I_r   = {res.I_r:.1f}")
        o.writeln(f"  I_rc  = {res.I_rc:.1f}   "
                  f"(threshold)")
        tag = "ok" if res.mode.value == "general_shear" else "fail"
        o.writeln(f"  MODE  = {res.mode.value.upper()}", tag=tag)
        o.writeln(f"  zeta_q     = {res.zeta_q:.3f}")
        o.writeln(f"  zeta_c     = {res.zeta_c:.3f}")
        o.writeln(f"  zeta_gamma = {res.zeta_gamma:.3f}")

        # Plot — zeta_q vs phi for several I_r values
        from foundationcalc.analysis.failure_mode import (
            critical_rigidity_index, vesic_reduction_factors,
        )
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        phi_arr = np.linspace(10, 45, 36)
        for Ir in (10, 50, 200, 1000):
            zq = []
            for phi in phi_arr:
                _, zq_v, _ = vesic_reduction_factors(
                    phi, Ir, self.B.get_float(2.5), self.L.get_float(2.5),
                    self.Nq.get_float(23.2),
                )
                zq.append(zq_v)
            ax.plot(phi_arr, zq, lw=1.4, label=f"I_r={Ir}")
        Irc_arr = [critical_rigidity_index(p) for p in phi_arr]
        ax2 = ax.twinx()
        ax2.semilogy(phi_arr, Irc_arr, "k--", lw=1, label="I_rc (Vesic)")
        ax2.set_ylabel("I_rc (log scale)")
        ax.set_xlabel("phi' (deg)")
        ax.set_ylabel("zeta_q (reduction)")
        ax.set_title(f"Vesic zeta_q vs phi  (current mode: {res.mode.value})")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="lower left")
        ax2.legend(fontsize=8, loc="upper right")


# ---------------------------------------------------------------------------
# Single-pile axial capacity (EC7 §7.6.2.3, calculation method)
# ---------------------------------------------------------------------------

class PileAxialCapacityPage(BasePage):
    title = "Pile axial capacity (EC7)"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.D = LabeledEntry(f, "Diameter (mm)", "600")
        self.L = LabeledEntry(f, "Length (mm)", "12000")
        self.pile_type = LabeledCombobox(
            f, "Pile type",
            ["bored", "driven_precast", "driven_in_situ", "cfa",
             "micropile", "steel"], default="bored",
        )
        self.alpha = LabeledEntry(f, "alpha (cohesive)", "0.55")
        self.beta = LabeledEntry(f, "beta (cohesionless)", "0.30")
        self.Nq = LabeledEntry(f, "N_q (base, drained)", "30")
        self.xi3 = LabeledEntry(f, "xi_3 (mean)", "1.40")
        self.xi4 = LabeledEntry(f, "xi_4 (min)", "1.40")
        self.gamma_b = LabeledEntry(f, "gamma_b (base)", "1.10")
        self.gamma_s = LabeledEntry(f, "gamma_s (shaft)", "1.10")
        self.gamma_t = LabeledEntry(f, "gamma_t (total)", "1.00")
        self.wt = LabeledEntry(f, "Water table (m)", "5.0")
        self.layers_txt = tk.Text(f, height=10, width=40,
                                  font=("Consolas", 9))
        self.layers_txt.insert(
            "1.0",
            "name,thickness_m,type,phi,c_kPa,cu_kPa,gamma,E_MPa\n"
            "fill,1.5,cohesionless,28,0,0,18,8\n"
            "soft_clay,3.5,cohesive,0,2,30,17,3\n"
            "med_sand,4.0,cohesionless,34,0,0,19,18\n"
            "dense_sand,6.0,cohesionless,40,0,0,20,40\n")
        widgets = [self.D, self.L, self.pile_type, self.alpha, self.beta,
                   self.Nq, self.xi3, self.xi4, self.gamma_b, self.gamma_s,
                   self.gamma_t, self.wt]
        for i, w in enumerate(widgets):
            w.grid(row=i, column=0, sticky="w", pady=1)
        ttk.Label(f, text="Soil profile:").grid(
            row=len(widgets) + 1, column=0, sticky="w", pady=(8, 2))
        self.layers_txt.grid(row=len(widgets) + 2, column=0, sticky="we", pady=2)

    def run(self) -> None:
        from foundationcalc.analysis.pile_capacity import pile_axial_capacity
        from foundationcalc.core.piles import Pile, PileType
        from foundationcalc.core.soil import SoilLayer, SoilProfile, SoilType

        pile = Pile(
            diameter=self.D.get_float(600),
            length=self.L.get_float(12000),
            pile_type=PileType(self.pile_type.get()),
        )
        layers: List[SoilLayer] = []
        for line in self.layers_txt.get("1.0", "end").strip().splitlines()[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 7:
                continue
            soil_type = (SoilType.COHESIONLESS if parts[2] == "cohesionless"
                         else SoilType.COHESIVE)
            E = float(parts[7]) if len(parts) >= 8 and parts[7] else None
            cu = float(parts[5]) if parts[5] else None
            layers.append(SoilLayer(
                name=parts[0],
                thickness=float(parts[1]),
                soil_type=soil_type,
                friction_angle=float(parts[3]),
                cohesion=float(parts[4]),
                undrained_shear_strength=cu,
                unit_weight=float(parts[6]),
                youngs_modulus=E,
            ))
        if not layers:
            self.output.writeln("No layers parsed.", tag="fail")
            return
        profile = SoilProfile(layers=layers, water_table_depth=self.wt.get_float(5.0))
        tip_depth_m = pile.length_m

        # Resolve the layer at the tip
        tip_layer = profile.layer_at(tip_depth_m)

        res = pile_axial_capacity(
            pile=pile, soil_profile=profile, base_soil=tip_layer,
            Nq=self.Nq.get_float(30),
            alpha_shaft=self.alpha.get_float(0.55),
            beta_shaft=self.beta.get_float(0.30),
            xi3=self.xi3.get_float(1.40),
            xi4=self.xi4.get_float(1.40),
            gamma_b=self.gamma_b.get_float(1.10),
            gamma_s=self.gamma_s.get_float(1.10),
            gamma_t=self.gamma_t.get_float(1.00),
            tip_depth_m=tip_depth_m,
        )

        o = self.output
        o.writeln("==== SINGLE PILE AXIAL CAPACITY (EC7 §7.6.2.3) ====",
                  tag="title")
        o.writeln(f"  Pile: Ø {pile.diameter:.0f} mm, L = {pile.length:.0f} mm")
        o.writeln(f"  Tip in layer: {tip_layer.name}  "
                  f"(type={tip_layer.soil_type.value})")
        o.writeln("")
        o.writeln(f"  R_bk  (base)   = {res.R_bk:>10,.0f} kN")
        o.writeln(f"  R_sk  (shaft)  = {res.R_sk:>10,.0f} kN")
        o.writeln(f"  R_ck  (total)  = {res.R_ck:>10,.0f} kN", tag="title")
        o.writeln(f"  R_cd  (design) = {res.R_cd:>10,.0f} kN", tag="ok")
        o.writeln(f"  Note: {res.note}", tag="muted")

        # ---- Plot: capacity build-up vs depth + base resistance at tip ----
        self.fig.clear()
        ax1 = self.fig.add_subplot(1, 2, 1)
        ax2 = self.fig.add_subplot(1, 2, 2, sharey=ax1)

        # Sweep tip depth from 1 m to the entered length: builds the R(L) curve
        depths = np.linspace(1.0, pile.length_m, 25)
        R_b_arr = []; R_s_arr = []; R_c_arr = []
        for L_try in depths:
            p_try = Pile(
                diameter=pile.diameter, length=L_try * 1000.0,
                pile_type=pile.pile_type,
            )
            tip_layer_try = profile.layer_at(L_try)
            r = pile_axial_capacity(
                pile=p_try, soil_profile=profile, base_soil=tip_layer_try,
                Nq=self.Nq.get_float(30),
                alpha_shaft=self.alpha.get_float(0.55),
                beta_shaft=self.beta.get_float(0.30),
                xi3=self.xi3.get_float(1.40),
                xi4=self.xi4.get_float(1.40),
                gamma_b=self.gamma_b.get_float(1.10),
                gamma_s=self.gamma_s.get_float(1.10),
                gamma_t=self.gamma_t.get_float(1.00),
                tip_depth_m=L_try,
            )
            R_b_arr.append(r.R_bk)
            R_s_arr.append(r.R_sk)
            R_c_arr.append(r.R_cd)
        ax1.plot(R_b_arr, depths, "b-", lw=1.6, label="R_bk (base)")
        ax1.plot(R_s_arr, depths, "g-", lw=1.6, label="R_sk (shaft)")
        ax1.plot(R_c_arr, depths, "r-", lw=2.0, label="R_cd (design)")
        ax1.invert_yaxis()
        ax1.set_xlabel("Capacity (kN)")
        ax1.set_ylabel("Tip depth (m)")
        ax1.set_title("Capacity vs embedment length")
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=8)

        # Soil profile sketch with water table
        z = 0.0
        for layer in layers:
            colour = "#d4a373" if layer.soil_type == SoilType.COHESIONLESS else "#8a817c"
            ax2.barh((z + z + layer.thickness) / 2.0, 1.0,
                     height=layer.thickness, color=colour, edgecolor="black",
                     align="center")
            label = (f"{layer.name}\nphi={layer.friction_angle:.0f}, "
                     f"c_u={layer.undrained_shear_strength or 0:.0f}")
            ax2.text(0.5, (z + z + layer.thickness) / 2.0, label,
                     va="center", ha="center", fontsize=7)
            z += layer.thickness
        ax2.axhline(self.wt.get_float(5.0), color="blue", linestyle=":",
                    lw=1.4, label="water table")
        ax2.axhline(pile.length_m, color="red", linestyle="--",
                    lw=1.4, label=f"pile tip @ {pile.length_m:.1f} m")
        ax2.set_xticks([])
        ax2.set_title("Soil profile")
        ax2.legend(fontsize=8, loc="lower right")


__all__ = [
    "CranePage",
    "PileLateralPage",
    "PileCapPage",
    "PileAxialCapacityPage",
    "StrapBeamPage",
    "StrengtheningPage",
    "SeismicFootingPage",
    "SptPage",
    "MultiLayerBcPage",
    "FailureModePage",
]
