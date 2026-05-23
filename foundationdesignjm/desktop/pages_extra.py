"""Additional desktop pages: walls, mat, pile group, reverse design, etc."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

import matplotlib
import numpy as np

from .pages import BasePage
from .widgets import LabeledCombobox, LabeledEntry


# ---------------------------------------------------------------------------
# Gravity wall
# ---------------------------------------------------------------------------

class GravityWallPage(BasePage):
    title = "Gravity wall"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.H = LabeledEntry(f, "Stem height (m)", "4.0")
        self.top = LabeledEntry(f, "Stem top width (m)", "0.3")
        self.bot = LabeledEntry(f, "Stem bottom width (m)", "1.5")
        self.toe = LabeledEntry(f, "Toe ext. (m)", "0.3")
        self.heel = LabeledEntry(f, "Heel ext. (m)", "0.4")
        self.base_t = LabeledEntry(f, "Base thickness (m)", "0.40")
        self.back_batter = LabeledEntry(f, "Back batter (deg)", "0")
        self.material = LabeledCombobox(
            f, "Material",
            ["mass_concrete", "masonry", "gabion", "crib"],
            default="mass_concrete",
        )
        self.phi_f = LabeledEntry(f, "Backfill phi", "32")
        self.gamma_f = LabeledEntry(f, "Backfill gamma", "18")
        self.alpha = LabeledEntry(f, "Backfill slope (deg)", "0")
        self.q = LabeledEntry(f, "Surcharge (kPa)", "5")
        self.hw = LabeledEntry(f, "Water height (m)", "0")
        self.phi_g = LabeledEntry(f, "Foundation phi", "34")
        self.gamma_g = LabeledEntry(f, "Foundation gamma", "20")
        for i, w in enumerate([self.H, self.top, self.bot,
                              self.toe, self.heel, self.base_t,
                              self.back_batter, self.material,
                              self.phi_f, self.gamma_f, self.alpha,
                              self.q, self.hw, self.phi_g, self.gamma_g]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.core.soil import SoilLayer, SoilType
        from foundationdesignjm.design.gravity_wall import (
            GravityWallDesigner, GravityWallGeometry, GravityWallLoading,
            GravityWallMaterial,
        )
        geo = GravityWallGeometry(
            H=self.H.get_float(4),
            top_width=self.top.get_float(0.3),
            stem_bottom=self.bot.get_float(1.5),
            toe=self.toe.get_float(0.3),
            heel=self.heel.get_float(0.4),
            base_thickness=self.base_t.get_float(0.4),
            back_batter_deg=self.back_batter.get_float(0),
        )
        bf = SoilLayer(name="bf", thickness=10, soil_type=SoilType.COHESIONLESS,
                      friction_angle=self.phi_f.get_float(32),
                      unit_weight=self.gamma_f.get_float(18))
        fd = SoilLayer(name="fd", thickness=10, soil_type=SoilType.COHESIONLESS,
                      friction_angle=self.phi_g.get_float(34),
                      unit_weight=self.gamma_g.get_float(20))
        load = GravityWallLoading(
            backfill=bf, foundation_soil=fd,
            surcharge_q=self.q.get_float(5),
            water_height=self.hw.get_float(0),
            backfill_slope_deg=self.alpha.get_float(0),
        )
        res = GravityWallDesigner(
            geo, load, material=GravityWallMaterial(self.material.get()),
        ).check()
        o = self.output
        o.writeln(f"==== GRAVITY WALL ({self.material.get()}) — Coulomb + Hansen ====",
                 tag="title")
        o.writeln(f"  Geometry:  H_stem = {geo.H:.2f} m,  "
                 f"a_top = {geo.top_width:.2f} m,  "
                 f"stem_bot = {geo.stem_bottom:.2f} m")
        o.writeln(f"             toe = {geo.toe:.2f} m,  heel = {geo.heel:.2f} m,  "
                 f"base_t = {geo.base_thickness:.2f} m   "
                 f"=>  TOTAL B = {geo.B:.2f} m")
        o.writeln(f"  Stabilising weights:", tag="title")
        o.writeln(f"    Stem    = {res.W_stem_kN_per_m:>6.1f} kN/m")
        if res.W_footing_kN_per_m > 0:
            o.writeln(f"    Footing = {res.W_footing_kN_per_m:>6.1f} kN/m")
        if res.W_backfill_on_heel_kN_per_m > 0:
            o.writeln(f"    Fill on heel = {res.W_backfill_on_heel_kN_per_m:>6.1f} kN/m")
        o.writeln(f"    TOTAL W = {res.W_kN_per_m:>6.1f} kN/m  "
                 f"at x_W = {res.x_W_m:.3f} m  (B/2 = {geo.B/2:.3f})")
        o.writeln(f"  K_a (Coulomb, delta_w = {(self.phi_f.get_float(32) * 2/3):.1f}°) "
                 f"= {res.K_a:.3f}")
        o.writeln(f"  Active thrust P_a = {res.P_a_total_kN_per_m:.1f} kN/m")
        o.writeln(f"    P_h (destabilising) = {res.P_h_kN_per_m:.1f} kN/m  "
                 f"@ z = {res.z_P_h_m:.2f} m")
        o.writeln(f"    P_v (stabilising)   = {res.P_v_kN_per_m:.1f} kN/m")
        if res.P_w_kN_per_m > 0:
            o.writeln(f"  Water thrust P_w = {res.P_w_kN_per_m:.1f} kN/m")
        o.writeln()
        o.writeln(f"  V_d = {res.V_d:.1f} kN/m,  H_d = {res.H_d:.1f} kN/m")
        o.writeln(f"  M_dst = {res.M_dst:.1f} kN.m/m,  M_stb = {res.M_stb:.1f} kN.m/m")
        o.writeln(f"  e_x = {res.e_x:+.3f} m   middle-third: {res.middle_third}",
                 tag="ok" if res.middle_third else "fail")
        o.writeln(f"  q_max = {res.q_max_kPa:.1f} kPa,  q_min = {res.q_min_kPa:.1f} kPa")
        o.writeln()
        o.writeln("==== ULS verdict (DA-2) ====", tag="title")
        for label, util in [
            ("Bearing (Hansen + i factors)", res.bearing_utilization),
            ("Sliding (delta_b interface)",  res.sliding_utilization),
            ("Overturning (EQU)",            res.overturning_utilization),
        ]:
            o.writeln(f"  {label:<32} {util*100:>5.1f}%",
                     tag="ok" if util <= 1.0 else "fail")
        if res.joint_tension and self.material.get() != "mass_concrete":
            o.writeln("  WARNING: e_x outside middle-third — masonry/gabion/crib "
                     "wall has NO tensile capacity at horizontal joints.",
                     tag="fail")
        o.writeln()
        o.writeln(f"OVERALL: {'OK' if res.all_ok else 'FAILS'}",
                 tag="ok" if res.all_ok else "fail")

        # Plot — actual geometry with stem + footing + backfill on heel
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_aspect("equal")

        a = geo.top_width
        s = geo.stem_bottom
        toe = geo.toe
        heel = geo.heel
        t = geo.base_thickness
        H = geo.H
        B = geo.B
        # y-coord of base of the stem (top of the footing)
        y_stem_base = t

        # 1) Footing slab (rectangle) — if present
        if t > 0:
            ax.fill([0, B, B, 0], [0, 0, t, t], color="#666666",
                   edgecolor="black", lw=1.5, label="Footing slab")
        # 2) Stem (trapezoid): vertical back at x = toe + s, battered front
        stem_back = toe + s
        stem_front_top = toe + (s - a)
        ax.fill([toe, stem_back, stem_back, stem_front_top],
               [y_stem_base, y_stem_base, y_stem_base + H, y_stem_base + H],
               color="#888888", edgecolor="black", lw=1.5, label="Stem")
        # 3) Backfill on the heel (if heel > 0)
        if heel > 0:
            ax.fill([stem_back, B, B, stem_back],
                   [y_stem_base, y_stem_base, y_stem_base + H, y_stem_base + H],
                   color="#e2c294", alpha=0.5, edgecolor="brown",
                   hatch="\\\\\\", label="Fill on heel")
        # 4) Backfill behind the wall, sloped at α
        alpha = math.radians(load.backfill_slope_deg)
        bf_top_y_at_3m = y_stem_base + H + (3.0 * math.tan(alpha))
        ax.fill([B, B + 3.0, B + 3.0, B],
               [y_stem_base + H, bf_top_y_at_3m, 0, 0],
               color="#e2c294", alpha=0.4, edgecolor="brown",
               hatch="\\\\\\")
        # 5) Foundation soil (under the base, extends front and back)
        ax.fill([-1, B + 4, B + 4, -1], [0, 0, -1, -1],
               color="#b0a080", alpha=0.5, hatch="...",
               edgecolor="brown")
        # 6) Active thrust arrow at z_P_h above base
        z = res.z_P_h_m
        delta_w = math.radians(load.backfill.friction_angle * 2.0 / 3.0)
        ax.annotate("",
                   xy=(B, z),
                   xytext=(B + 0.8 * math.cos(delta_w),
                          z + 0.8 * math.sin(delta_w)),
                   arrowprops=dict(arrowstyle="->", color="red", lw=2))
        ax.text(B + 1.0, z + 0.1,
               f"P_a = {res.P_a_total_kN_per_m:.0f} kN/m\n"
               f"P_h = {res.P_h_kN_per_m:.0f}\n"
               f"P_v = {res.P_v_kN_per_m:.0f}",
               color="red", fontsize=8, va="bottom")
        # 7) Combined centroid marker
        ax.plot([res.x_W_m], [y_stem_base + H / 4.0], "k+",
               markersize=14, markeredgewidth=2,
               label=f"Combined centroid  x_W={res.x_W_m:.2f} m")
        # 8) B/2 marker for reference
        ax.axvline(B / 2, color="blue", linestyle=":", linewidth=0.8,
                  alpha=0.5)
        ax.text(B / 2, -0.8, "B/2", color="blue", fontsize=7, ha="center")

        ax.set_xlim(-0.5, B + 4)
        ax.set_ylim(-1.2, max(H + t, bf_top_y_at_3m) + 0.5)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title(f"Gravity wall H={H}, stem={s}, toe={toe}, heel={heel}, "
                    f"B={B} m" + ("  OK" if res.all_ok else "  FAILS"))
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)


# ---------------------------------------------------------------------------
# Counterfort wall
# ---------------------------------------------------------------------------

class CounterfortWallPage(BasePage):
    title = "Counterfort wall"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.H = LabeledEntry(f, "Stem H (m)", "8.0")
        self.stem_t = LabeledEntry(f, "Stem thickness (m)", "0.35")
        self.toe = LabeledEntry(f, "Toe (m)", "1.5")
        self.heel = LabeledEntry(f, "Heel (m)", "3.0")
        self.base_t = LabeledEntry(f, "Base thickness (m)", "0.80")
        self.cf_spacing = LabeledEntry(f, "Counterfort spacing (m)", "3.0")
        self.cf_thick = LabeledEntry(f, "Counterfort thickness (m)", "0.40")
        self.phi_f = LabeledEntry(f, "Backfill phi", "33")
        self.gamma_f = LabeledEntry(f, "Backfill gamma", "19")
        self.q = LabeledEntry(f, "Surcharge", "10")
        for i, w in enumerate([self.H, self.stem_t, self.toe, self.heel, self.base_t,
                              self.cf_spacing, self.cf_thick, self.phi_f,
                              self.gamma_f, self.q]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.core.material import Concrete
        from foundationdesignjm.core.soil import SoilLayer, SoilType
        from foundationdesignjm.design.counterfort_wall import (
            CounterfortWallDesigner, CounterfortWallGeometry,
        )
        from foundationdesignjm.design.retaining_wall import RetainingWallLoading
        geo = CounterfortWallGeometry(
            H=self.H.get_float(8), stem_thickness=self.stem_t.get_float(0.35),
            toe=self.toe.get_float(1.5), heel=self.heel.get_float(3.0),
            base_thickness=self.base_t.get_float(0.8),
            counterfort_spacing_m=self.cf_spacing.get_float(3.0),
            counterfort_thickness_m=self.cf_thick.get_float(0.4),
        )
        bf = SoilLayer(name="bf", thickness=10, soil_type=SoilType.COHESIONLESS,
                      friction_angle=self.phi_f.get_float(33),
                      unit_weight=self.gamma_f.get_float(19))
        fd = SoilLayer(name="fd", thickness=10, soil_type=SoilType.COHESIONLESS,
                      friction_angle=36, unit_weight=20)
        load = RetainingWallLoading(
            backfill=bf, foundation_soil=fd, surcharge_q=self.q.get_float(10),
        )
        res = CounterfortWallDesigner(geo, load, Concrete(fck=30)).check()
        g = res.global_check
        o = self.output
        o.writeln(f"==== COUNTERFORT WALL — global ULS ====", tag="title")
        for label, u in [("Bearing", g.bearing_utilization),
                        ("Sliding", g.sliding_utilization),
                        ("Overturning", g.overturning_utilization)]:
            o.writeln(f"  {label:<13} {u*100:>5.1f}%",
                     tag="ok" if u <= 1.0 else "fail")
        o.writeln()
        o.writeln("==== STEM as one-way slab between counterforts ====", tag="title")
        o.writeln(f"  M_midspan = {res.stem_M_midspan_kNm_per_m:.1f} kN.m/m")
        o.writeln(f"  M_support = {res.stem_M_support_kNm_per_m:.1f} kN.m/m")
        o.writeln(f"  V_support = {res.stem_V_at_support_kN_per_m:.1f} kN/m")
        o.writeln()
        o.writeln("==== COUNTERFORT cantilever ====", tag="title")
        o.writeln(f"  T_tie     = {res.counterfort_tie_T_kN:.0f} kN")
        o.writeln(f"  M_base    = {res.counterfort_M_base_kNm:.0f} kN.m")
        o.writeln(f"  V_base    = {res.counterfort_V_base_kN:.0f} kN")
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_aspect("equal")
        B = geo.B
        H = geo.H; t = geo.base_thickness
        ax.fill([0, B, B, 0], [0, 0, t, t], color="#cccccc", edgecolor="black")
        x0 = geo.toe; x1 = x0 + geo.stem_thickness
        ax.fill([x0, x1, x1, x0], [t, t, t+H, t+H], color="#bbbbbb", edgecolor="black")
        # Counterfort behind the stem (triangular fin)
        ax.fill([x1, x1 + 2.0, x1, x1],
               [t, t, t + H, t + H], color="#999999", alpha=0.4, edgecolor="black")
        ax.set_xlim(-0.5, B + 1)
        ax.set_ylim(-0.5, t + H + 0.5)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title(f"Counterfort wall H = {H} m")
        ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# MSE wall
# ---------------------------------------------------------------------------

class MSEWallPage(BasePage):
    title = "MSE wall"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.H = LabeledEntry(f, "Wall height (m)", "5.0")
        self.B = LabeledEntry(f, "Reinforced width (m)", "5.0")
        self.n_layers = LabeledEntry(f, "Number of layers", "5")
        self.spacing = LabeledEntry(f, "Vertical spacing (m)", "1.0")
        self.L_geo = LabeledEntry(f, "Geogrid length (m)", "5.0")
        self.reinf = LabeledCombobox(
            f, "Reinforcement",
            ["steel_strip", "steel_grid", "geogrid_hdpe", "geogrid_pet"],
            default="geogrid_pet",
        )
        self.phi = LabeledEntry(f, "Fill phi", "36")
        self.gamma = LabeledEntry(f, "Fill gamma", "20")
        self.q = LabeledEntry(f, "Surcharge (kPa)", "10")
        for i, w in enumerate([self.H, self.B, self.n_layers, self.spacing,
                              self.L_geo, self.reinf, self.phi, self.gamma, self.q]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.design.mse_wall import (
            MSELayer, MSELoading, MSEReinforcementType,
            MSEWallDesigner, MSEWallGeometry,
        )
        H = self.H.get_float(5.0)
        n = self.n_layers.get_int(5)
        sp = self.spacing.get_float(1.0)
        rt = MSEReinforcementType(self.reinf.get())
        layers = [
            MSELayer(z_below_top_m=H - (i + 0.5) * sp,
                    length_m=self.L_geo.get_float(5.0),
                    reinforcement_type=rt, spacing_vertical_m=sp)
            for i in range(n)
        ]
        geo = MSEWallGeometry(H=H, B_reinforced=self.B.get_float(5.0), layers=layers)
        load = MSELoading(
            phi_fill_deg=self.phi.get_float(36),
            gamma_fill_kN_m3=self.gamma.get_float(20),
            surcharge_q=self.q.get_float(10),
            phi_foundation_deg=32, gamma_foundation_kN_m3=19,
        )
        res = MSEWallDesigner(geo, load).check()
        o = self.output
        o.writeln(f"==== MSE WALL — external stability ====", tag="title")
        for label, u in [("Bearing", res.external.bearing_utilization),
                        ("Sliding", res.external.sliding_utilization),
                        ("Overturning", res.external.overturning_utilization)]:
            o.writeln(f"  {label:<13} {u*100:>5.1f}%",
                     tag="ok" if u <= 1.0 else "fail")
        o.writeln(f"  e_x = {res.external.e_x_m:+.3f} m,  "
                 f"q_max = {res.external.q_max_kPa:.0f} kPa")
        o.writeln()
        o.writeln("==== INTERNAL stability (per layer) ====", tag="title")
        for L in res.internal:
            tag = "ok" if L.ok else "fail"
            o.writeln(f"  z={L.z_m:>4.1f}m   T={L.T_max_kN_per_m:>5.1f}   "
                     f"util_tens={L.tensile_utilization*100:>4.1f}%   "
                     f"util_pullout={L.pullout_utilization*100:>4.1f}%", tag=tag)
        # Plot: wall + layers
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_aspect("equal")
        ax.add_patch(matplotlib.patches.Rectangle(
            (0, 0), geo.B_reinforced, H, facecolor="#dde3eb",
            edgecolor="black", lw=1.5,
        ))
        for L in res.internal:
            ax.plot([0, geo.B_reinforced], [H - L.z_m, H - L.z_m], "g-", lw=2)
            tag = "OK" if L.ok else "FAIL"
            ax.text(geo.B_reinforced + 0.2, H - L.z_m,
                   f"T={L.T_max_kN_per_m:.0f} {tag}",
                   fontsize=7, va="center")
        # Active wedge
        phi_a = math.radians(45 + load.phi_fill_deg / 2)
        x_wedge = H / math.tan(phi_a)
        ax.plot([0, x_wedge], [H, 0], "r--", lw=1, label="active wedge")
        ax.set_xlim(-0.5, geo.B_reinforced + 3)
        ax.set_ylim(-0.5, H + 0.5)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title(f"MSE wall H = {H} m, n = {n} layers")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Anchored wall
# ---------------------------------------------------------------------------

class AnchoredWallPage(BasePage):
    title = "Anchored wall"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.H = LabeledEntry(f, "Excavation H (m)", "10")
        self.D = LabeledEntry(f, "Embedment (m)", "3")
        self.n_anchors = LabeledEntry(f, "Number of anchor rows", "3")
        self.spacing = LabeledEntry(f, "Horizontal spacing (m)", "2.5")
        self.bond_soil = LabeledCombobox(
            f, "Bond zone soil",
            ["rock", "stiff_clay", "dense_sand", "medium_sand", "loose_sand"],
            default="medium_sand",
        )
        self.phi = LabeledEntry(f, "Soil phi", "32")
        self.gamma = LabeledEntry(f, "Soil gamma", "20")
        self.q = LabeledEntry(f, "Surcharge", "15")
        for i, w in enumerate([self.H, self.D, self.n_anchors, self.spacing,
                              self.bond_soil, self.phi, self.gamma, self.q]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.design.anchored_wall import (
            AnchorLevel, AnchoredWallDesigner, AnchoredWallGeometry, AnchoredWallLoading,
        )
        H = self.H.get_float(10)
        n = self.n_anchors.get_int(3)
        zs = [H * (i + 1) / (n + 1) for i in range(n)]
        anchors = [
            AnchorLevel(z_below_top_m=z, horizontal_spacing_m=self.spacing.get_float(2.5),
                       bond_zone_soil=self.bond_soil.get())
            for z in zs
        ]
        geo = AnchoredWallGeometry(H_excavation=H, embedment_m=self.D.get_float(3),
                                   anchor_levels=anchors)
        load = AnchoredWallLoading(phi_deg=self.phi.get_float(32),
                                   gamma_kN_m3=self.gamma.get_float(20),
                                   surcharge_q=self.q.get_float(15))
        res = AnchoredWallDesigner(geo, load).check()
        o = self.output
        o.writeln("==== ANCHORED WALL ====", tag="title")
        o.writeln(f"  Total horizontal load = {res.P_total_kN_per_m:.0f} kN/m of wall")
        o.writeln(f"  p_max (apparent) = {res.p_max_kPa:.0f} kPa")
        o.writeln()
        for a in res.anchors:
            tag = "ok" if a.ok else "fail"
            o.writeln(f"  z={a.z_m:>4.1f}m:  T={a.T_design_kN_per_anchor:>6.0f} kN,  "
                     f"free={a.free_length_m:>4.1f} m,  "
                     f"bond={a.bond_length_m:>4.1f} m  "
                     f"(util={a.bond_utilization*100:.0f}%)", tag=tag)
        # Plot
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_aspect("equal")
        H_total = H + geo.embedment_m
        ax.plot([0, 0], [0, H_total], "k-", lw=3)
        ax.fill([0, 5, 5, 0], [0, 0, -0.5, -0.5], color="#cccccc")  # excavation floor
        for a in res.anchors:
            y = H_total - a.z_m
            dx = a.total_length_m * math.cos(math.radians(15))
            dy = -a.total_length_m * math.sin(math.radians(15))
            ax.annotate("", xy=(dx, y + dy), xytext=(0, y),
                       arrowprops=dict(arrowstyle="->", color="red", lw=1.5))
            ax.text(dx + 0.3, y + dy, f"{a.T_design_kN_per_anchor:.0f} kN",
                   fontsize=8, color="red")
        ax.set_xlim(-1, 25)
        ax.set_ylim(-1, H_total + 1)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("Height above toe [m]")
        ax.set_title(f"Anchored wall H = {H} m + D = {geo.embedment_m} m")
        ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Diaphragm wall
# ---------------------------------------------------------------------------

class DiaphragmWallPage(BasePage):
    title = "Diaphragm wall"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.H = LabeledEntry(f, "Excavation H (m)", "10")
        self.D = LabeledEntry(f, "Embedment (m)", "5")
        self.t = LabeledEntry(f, "Thickness (m)", "0.80")
        self.prop_z = LabeledEntry(f, "Top prop depth (m)", "1.0")
        self.phi = LabeledEntry(f, "Soil phi", "32")
        self.gamma = LabeledEntry(f, "Soil gamma", "20")
        self.q = LabeledEntry(f, "Surcharge", "15")
        for i, w in enumerate([self.H, self.D, self.t, self.prop_z,
                              self.phi, self.gamma, self.q]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.design.diaphragm_wall import (
            DiaphragmWallDesigner, DiaphragmWallGeometry, DiaphragmWallLoading,
        )
        geo = DiaphragmWallGeometry(
            H_excavation=self.H.get_float(10), embedment_m=self.D.get_float(5),
            thickness_m=self.t.get_float(0.8),
            prop_levels_m=[self.prop_z.get_float(1.0)],
        )
        load = DiaphragmWallLoading(phi_deg=self.phi.get_float(32),
                                   gamma_kN_m3=self.gamma.get_float(20),
                                   surcharge_q=self.q.get_float(15))
        res = DiaphragmWallDesigner(geo, load).check()
        o = self.output
        o.writeln("==== DIAPHRAGM WALL ====", tag="title")
        o.writeln(f"  Active thrust  P_a = {res.P_active_kN_per_m:.0f} kN/m")
        o.writeln(f"  Passive resist P_p = {res.P_passive_kN_per_m:.0f} kN/m")
        o.writeln(f"  Overturning FoS    = {res.overturning_safety_factor:.2f}",
                 tag="ok" if res.overturning_safety_factor >= 1.5 else "fail")
        o.writeln(f"  Embedment required = {res.embedment_required_m:.2f} m  "
                 f"(provided {geo.embedment_m:.2f} m)",
                 tag="ok" if geo.embedment_m >= res.embedment_required_m else "fail")
        o.writeln(f"  Prop forces        = "
                 + ", ".join(f"{f:.0f}" for f in res.prop_forces_kN_per_m) + " kN/m")
        o.writeln(f"  M_max             = {res.M_max_kNm_per_m:.0f} kN.m/m")
        o.writeln(f"  V_max             = {res.V_max_kN_per_m:.0f} kN/m")
        # Plot
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        H = geo.H_excavation; D = geo.embedment_m
        ax.plot([0, 0], [0, H + D], "k-", lw=4)
        ax.fill([-2, 0, 0, -2], [0, 0, H, H], color="#bbb", alpha=0.4)  # retained soil
        ax.fill([0, 5, 5, 0], [H, H, 0, 0], color="#eee")               # excavation
        # Pressure diagrams
        K_a = (math.tan(math.radians(45 - load.phi_deg/2)))**2
        K_p = (math.tan(math.radians(45 + load.phi_deg/2)))**2
        z = np.linspace(0, H + D, 30)
        p_a = K_a * load.gamma_kN_m3 * z
        ax.plot(-p_a / 50, H + D - z, "b-", lw=1.5, label="Active")
        z_p = np.linspace(0, D, 15)
        p_p = K_p * load.gamma_kN_m3 * z_p
        ax.plot(p_p / 100, D - z_p, "g-", lw=1.5, label="Passive")
        ax.scatter([0], [H + D - geo.prop_levels_m[0]], color="red", zorder=5, label="Prop")
        ax.set_xlim(-6, 4)
        ax.set_ylim(-1, H + D + 1)
        ax.set_xlabel("Pressure (scaled)")
        ax.set_ylabel("Height above toe [m]")
        ax.set_title(f"Diaphragm wall H = {H} + D = {D} m")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Combined footing
# ---------------------------------------------------------------------------

class CombinedFootingPage(BasePage):
    title = "Combined footing"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.P1 = LabeledEntry(f, "P1 (kN)", "800")
        self.P2 = LabeledEntry(f, "P2 (kN)", "1200")
        self.s = LabeledEntry(f, "Spacing (m)", "4.5")
        self.d_pl = LabeledEntry(f, "P1 to prop. line (m)", "0.0")
        self.col_a = LabeledEntry(f, "Column side (m)", "0.40")
        self.q_allow = LabeledEntry(f, "q_allow (kPa)", "180")
        self.t = LabeledEntry(f, "Thickness (m)", "0.60")
        for i, w in enumerate([self.P1, self.P2, self.s, self.d_pl,
                              self.col_a, self.q_allow, self.t]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.design.combined_footing import (
            CombinedFootingInputs, design_combined_footing,
        )
        res = design_combined_footing(CombinedFootingInputs(
            P1_kN=self.P1.get_float(800), P2_kN=self.P2.get_float(1200),
            col_spacing_m=self.s.get_float(4.5),
            column_1_to_property_line_m=self.d_pl.get_float(0.0),
            column_size_m=self.col_a.get_float(0.4),
            q_allow_kPa=self.q_allow.get_float(180),
            thickness_m=self.t.get_float(0.6),
        ))
        o = self.output
        o.writeln(f"==== COMBINED FOOTING — {res.shape.upper()} ====", tag="title")
        o.writeln(f"  L = {res.L_m:.2f} m")
        if res.shape == "trapezoidal":
            o.writeln(f"  B1 = {res.B1_m:.2f} m (column 1 end)  "
                     f"B2 = {res.B2_m:.2f} m (column 2 end)")
        else:
            o.writeln(f"  B  = {res.B_m:.2f} m")
        o.writeln(f"  A_required = {res.A_required_m2:.2f} m²,  "
                 f"A_provided = {res.A_provided_m2:.2f} m²")
        o.writeln(f"  x_resultant from property line = {res.x_resultant_m:.2f} m")
        o.writeln(f"  {res.note}")
        o.writeln()
        o.writeln("==== BENDING + REINFORCEMENT ====", tag="title")
        o.writeln(f"  M+ (sagging, bottom) = {res.M_pos_kNm:.0f} kN.m")
        o.writeln(f"  M- (hogging, top)    = {res.M_neg_kNm:.0f} kN.m")
        o.writeln(f"  V_max                = {res.V_max_kN:.0f} kN")
        o.writeln(f"  As_bottom = {res.As_bot_mm2:.0f} mm² total")
        o.writeln(f"  As_top    = {res.As_top_mm2:.0f} mm² total")
        # Plot
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_aspect("equal")
        if res.shape == "rectangular":
            ax.add_patch(matplotlib.patches.Rectangle(
                (0, -res.B_m/2), res.L_m, res.B_m,
                facecolor="#dde3eb", edgecolor="black", lw=1.5,
            ))
        else:
            ax.fill([0, res.L_m, res.L_m, 0],
                   [-res.B1_m/2, -res.B2_m/2, res.B2_m/2, res.B1_m/2],
                   facecolor="#dde3eb", edgecolor="black", lw=1.5)
        # Columns
        a = 0.4
        x_col1 = self.d_pl.get_float(0) + a/2
        x_col2 = x_col1 + self.s.get_float(4.5)
        for x in [x_col1, x_col2]:
            ax.add_patch(matplotlib.patches.Rectangle(
                (x - a/2, -a/2), a, a, facecolor="#999", edgecolor="black",
            ))
        # Resultant
        ax.plot([res.x_resultant_m], [0], "rx", markersize=12, label="Resultant")
        ax.set_xlim(-0.5, res.L_m + 0.5)
        ax.set_ylim(-(res.B2_m + 0.5)/2, (res.B2_m + 0.5)/2)
        ax.set_xlabel("x [m] from property line")
        ax.set_ylabel("y [m]")
        ax.set_title(f"Combined footing ({res.shape})  L = {res.L_m:.2f} m")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Basement wall
# ---------------------------------------------------------------------------

class BasementWallPage(BasePage):
    title = "Basement wall"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.H = LabeledEntry(f, "Height (m)", "3.5")
        self.t = LabeledEntry(f, "Thickness (m)", "0.30")
        self.e1 = LabeledEntry(f, "e top (m)", "0.05")
        self.e2 = LabeledEntry(f, "e base (m)", "0.10")
        self.phi = LabeledEntry(f, "phi (deg)", "30")
        self.gamma = LabeledEntry(f, "gamma", "19")
        self.q = LabeledEntry(f, "Surcharge", "10")
        self.Nmax = LabeledEntry(f, "N_max (kN/m)", "200")
        self.support = LabeledCombobox(
            f, "Support",
            ["propped_cantilever", "cantilever", "pinned_pinned"],
            default="propped_cantilever",
        )
        self.diagram = LabeledCombobox(
            f, "Pressure", ["triangular", "rectangular"], default="triangular",
        )
        for i, w in enumerate([self.H, self.t, self.e1, self.e2,
                              self.phi, self.gamma, self.q, self.Nmax,
                              self.support, self.diagram]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.design.basement_wall import (
            BasementWallDesigner, BasementWallGeometry, BasementWallLoading,
            PressureDiagram, SupportConfig,
        )
        geo = BasementWallGeometry(
            height=self.H.get_float(3.5),
            thickness=self.t.get_float(0.30),
            eccentricity_top=self.e1.get_float(0.05),
            eccentricity_base=self.e2.get_float(0.10),
        )
        load = BasementWallLoading(
            phi_deg=self.phi.get_float(30),
            gamma_soil=self.gamma.get_float(19),
            surcharge_q=self.q.get_float(10),
            N_min_kN_per_m=0,
            N_max_kN_per_m=self.Nmax.get_float(200),
        )
        des = BasementWallDesigner(
            geo, load,
            support=SupportConfig(self.support.get()),
            pressure=PressureDiagram(self.diagram.get()),
        )
        res = des.solve()
        o = self.output
        o.writeln(f"==== BASEMENT WALL ({self.support.get()}, {self.diagram.get()}) ====",
                 tag="title")
        o.writeln(f"  K_0 = {res.K0:.3f}")
        o.writeln(f"  q_top = {res.q_top_kPa:.1f} kPa,  q_base = {res.q_base_kPa:.1f} kPa")
        o.writeln(f"  R_top  = {res.R_top_kN_per_m:.1f} kN/m")
        o.writeln(f"  R_base = {res.R_base_kN_per_m:.1f} kN/m")
        o.writeln(f"  V_max  = {res.V_max_kN:.1f} kN/m")
        o.writeln()
        o.writeln(f"  M_inner max = {res.M_inner_max_kNm:+.1f} kN.m/m  at z={res.z_of_M_inner_max_m:.2f} m")
        o.writeln(f"  M_outer max = {res.M_outer_max_kNm:+.1f} kN.m/m  at z={res.z_of_M_outer_max_m:.2f} m")
        # Plot bending envelopes
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.plot(res.M_envelope_outer, res.z, "r-", lw=1.6, label="Outer face")
        ax.plot(res.M_envelope_inner, res.z, "b-", lw=1.6, label="Inner face")
        ax.fill_betweenx(res.z, res.M_envelope_outer, 0, color="r", alpha=0.15)
        ax.fill_betweenx(res.z, res.M_envelope_inner, 0, color="b", alpha=0.15)
        ax.axvline(0, color="black", lw=0.6)
        ax.invert_yaxis()
        ax.set_xlabel("M [kN.m/m]")
        ax.set_ylabel("Depth z [m]")
        ax.set_title("Bending envelope")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)


# ---------------------------------------------------------------------------
# Mat foundation
# ---------------------------------------------------------------------------

class MatFoundationPage(BasePage):
    title = "Mat foundation"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.L = LabeledEntry(f, "Length (m)", "12")
        self.B = LabeledEntry(f, "Width (m)", "10")
        self.t = LabeledEntry(f, "Thickness (m)", "0.7")
        self.nx = LabeledEntry(f, "n_x elements", "16")
        self.ny = LabeledEntry(f, "n_y elements", "12")
        self.ks = LabeledEntry(f, "k_s (kN/m³)", "25000")
        self.q = LabeledEntry(f, "Self-weight pressure (kPa)", "17.5")
        self.col_txt = tk.Text(f, height=8, width=34, font=("Consolas", 9))
        self.col_txt.insert("1.0", "x,y,P,name\n2,2,900,P1\n6,2,1100,P2\n10,2,950,P3\n"
                            "2,8,920,P4\n6,8,1150,P5\n10,8,980,P6\n")
        for i, w in enumerate([self.L, self.B, self.t, self.nx, self.ny,
                              self.ks, self.q]):
            w.grid(row=i, column=0, sticky="w", pady=1)
        ttk.Label(f, text="Columns (x,y,P,name):").grid(
            row=8, column=0, sticky="w", pady=(8, 2),
        )
        self.col_txt.grid(row=9, column=0, sticky="we", pady=2)

    def run(self) -> None:
        from foundationdesignjm.analysis.mat_foundation import MatFoundationSolver
        mat = MatFoundationSolver(
            length=self.L.get_float(12), width=self.B.get_float(10),
            thickness=self.t.get_float(0.7),
            nx=self.nx.get_int(16), ny=self.ny.get_int(12),
            k_s=self.ks.get_float(25000),
        )
        mat.add_uniform_pressure(q=self.q.get_float(17.5))
        for line in self.col_txt.get("1.0", "end").strip().splitlines()[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                x = float(parts[0]); y = float(parts[1]); P = float(parts[2])
                name = parts[3] if len(parts) > 3 else ""
                mat.add_column_load(x=x, y=y, P=P, name=name)
        res = mat.solve()
        self.last_solver = mat
        self.last_result = res
        o = self.output
        o.writeln("==== MAT FOUNDATION — Winkler 2D ====", tag="title")
        o.writeln(f"  Iterations: {res.iterations},  converged: {res.converged}")
        o.writeln(f"  Uplift nodes: {len(res.uplift_nodes)}/{mat.n_nodes}")
        o.writeln(f"  w_max = {res.w_max*1000:.2f} mm,  w_min = {res.w_min*1000:.2f} mm")
        o.writeln(f"  Differential settlement = {res.differential_settlement_mm:.2f} mm")
        o.writeln(f"  M_xx max = {res.M_xx.max():.1f} kN.m/m,  M_yy max = {res.M_yy.max():.1f}")
        # Plot
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        xs = np.linspace(0, mat.length, mat.nx + 1)
        ys = np.linspace(0, mat.width, mat.ny + 1)
        Z = (res.w * 1000).reshape(mat.ny + 1, mat.nx + 1)
        c = ax.contourf(xs, ys, Z, levels=20, cmap="RdBu_r")
        self.fig.colorbar(c, ax=ax, label="w [mm]")
        for cl in mat._column_loads:
            ax.scatter(cl.x, cl.y, c="black", s=40, marker="s")
            ax.text(cl.x, cl.y + 0.15, cl.name or f"{cl.P:.0f}",
                   fontsize=8, ha="center")
        ax.set_aspect("equal")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title("Settlement contour [mm]")


# ---------------------------------------------------------------------------
# Reverse design (optimizer)
# ---------------------------------------------------------------------------

class ReverseDesignPage(BasePage):
    title = "Reverse design"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.load = LabeledEntry(f, "Vertical load (kN)", "1500")
        self.D = LabeledEntry(f, "Founding depth (m)", "1.5")
        self.sls = LabeledEntry(f, "Settlement limit (mm)", "50")
        self.B_min = LabeledEntry(f, "B_min (mm)", "800")
        self.B_max = LabeledEntry(f, "B_max (mm)", "5000")
        self.t = LabeledEntry(f, "Thickness (mm)", "500")
        self.wt = LabeledEntry(f, "Water table (m)", "5")
        self.cpt_txt = tk.Text(f, height=8, width=34, font=("Consolas", 9))
        self.cpt_txt.insert("1.0", "depth,qc,fs\n0.5,12,70\n2,12,70\n4,12,70\n"
                            "6,12,70\n8,12,70\n10,12,70\n")
        for i, w in enumerate([self.load, self.D, self.sls, self.B_min,
                              self.B_max, self.t, self.wt]):
            w.grid(row=i, column=0, sticky="w", pady=1)
        ttk.Label(f, text="CPT (depth,qc,fs):").grid(
            row=8, column=0, sticky="w", pady=(8, 2),
        )
        self.cpt_txt.grid(row=9, column=0, sticky="we", pady=2)

    def run(self) -> None:
        from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
        from foundationdesignjm.analysis.reverse_design import (
            OptimizationGoal, optimize_footing_dimensions,
        )
        from foundationdesignjm.codes.eurocode7 import DesignApproach
        readings = []
        for line in self.cpt_txt.get("1.0", "end").strip().splitlines()[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                readings.append(CPTReading(depth=float(parts[0]),
                                          q_c_MPa=float(parts[1]),
                                          f_s_kPa=float(parts[2])))
        cpt = CPTProfile(readings=readings,
                         water_table_depth_m=self.wt.get_float(5))
        opt = optimize_footing_dimensions(
            cpt, load_kN=self.load.get_float(1500),
            founding_depth_m=self.D.get_float(1.5),
            design_approach=DesignApproach.DA2,
            settlement_limit_mm=self.sls.get_float(50),
            B_min_mm=self.B_min.get_float(800),
            B_max_mm=self.B_max.get_float(5000),
            thickness_mm=self.t.get_float(500),
            goal=OptimizationGoal.MIN_AREA,
        )
        o = self.output
        o.writeln(f"==== REVERSE DESIGN ({len(opt.history)} iter) ====", tag="title")
        o.writeln(f"  Optimum B = L = {opt.best.B*1000:.0f} mm")
        o.writeln(f"  Bearing util  = {opt.best.bearing_utilization*100:.1f} %")
        o.writeln(f"  Settlement    = {opt.best.settlement_mm:.2f} mm")
        o.writeln(f"  Cost estimate = €{opt.best.cost_eur:,.0f}")
        o.writeln(f"  Passes        = {opt.best.passes}",
                 tag="ok" if opt.best.passes else "fail")
        # Plot history
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        Bs = [c.B for c in opt.history]
        utils_ = [c.bearing_utilization*100 for c in opt.history]
        settle = [c.settlement_mm for c in opt.history]
        ax2 = ax.twinx()
        ax.plot(range(len(Bs)), Bs, "b-o", label="B (m)")
        ax2.plot(range(len(Bs)), utils_, "r-^", label="Bearing util (%)")
        ax2.plot(range(len(Bs)), settle, "g-s", label="Settlement (mm)")
        ax.set_xlabel("Iteration")
        ax.set_ylabel("B [m]", color="b")
        ax2.set_ylabel("Util / Settlement", color="r")
        ax.set_title("Binary-search convergence")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", fontsize=8)
        ax2.legend(loc="upper right", fontsize=8)


# ---------------------------------------------------------------------------
# Pile group
# ---------------------------------------------------------------------------

class PileGroupPage(BasePage):
    title = "Pile group"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.rows = LabeledEntry(f, "Rows", "2")
        self.cols = LabeledEntry(f, "Cols", "3")
        self.s = LabeledEntry(f, "Spacing (m)", "2.4")
        self.d = LabeledEntry(f, "Diameter (m)", "0.8")
        self.cap = LabeledEntry(f, "Axial capacity (kN)", "1500")
        self.tens = LabeledEntry(f, "Tension capacity (kN)", "400")
        self.lat = LabeledEntry(f, "Lateral capacity (kN)", "120")
        self.V = LabeledEntry(f, "V (kN)", "6000")
        self.H = LabeledEntry(f, "H (kN)", "600")
        self.Mx = LabeledEntry(f, "M_x (kN.m)", "2000")
        for i, w in enumerate([self.rows, self.cols, self.s, self.d,
                              self.cap, self.tens, self.lat,
                              self.V, self.H, self.Mx]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.analysis.pile_group import (
            distribute_loads_rigid_cap, rectangular_group,
        )
        g = rectangular_group(
            n_rows=self.rows.get_int(2), n_cols=self.cols.get_int(3),
            spacing_m=self.s.get_float(2.4), diameter_m=self.d.get_float(0.8),
            axial_capacity_kN=self.cap.get_float(1500),
            tension_capacity_kN=self.tens.get_float(400),
            lateral_capacity_kN=self.lat.get_float(120),
        )
        res = distribute_loads_rigid_cap(
            g, V_kN=self.V.get_float(6000),
            H_y_kN=self.H.get_float(600),
            M_x_kNm=self.Mx.get_float(2000),
        )
        o = self.output
        o.writeln("==== PILE GROUP ====", tag="title")
        o.writeln(f"  E_axial = {res.axial_efficiency:.3f},  E_lat = {res.lateral_efficiency:.3f}")
        o.writeln(f"  N_max compression = {res.N_max_compression:.0f} kN")
        o.writeln(f"  N_max tension     = {res.N_max_tension:.0f} kN")
        o.writeln(f"  H_max per pile    = {res.H_max_per_pile:.0f} kN")
        o.writeln(f"  Governing pile    = {res.governing_pile}")
        o.writeln(f"  Group util (compression) = {res.group_axial_utilization*100:.1f}%",
                 tag="ok" if res.group_axial_utilization <= 1 else "fail")
        o.writeln(f"  Group util (lateral)     = {res.group_lateral_utilization*100:.1f}%",
                 tag="ok" if res.group_lateral_utilization <= 1 else "fail")
        for f in res.forces:
            o.writeln(f"   {f.pile_name}: x={f.x_m:+5.2f}, y={f.y_m:+5.2f}  "
                     f"N={f.N_kN:>7.0f} kN  util={f.axial_utilization*100:>4.1f}%")
        # Plot
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_aspect("equal")
        for f in res.forces:
            color = "red" if f.axial_utilization > 1 else "blue"
            ax.scatter(f.x_m, f.y_m, s=200, c=color, edgecolors="black", zorder=5)
            ax.text(f.x_m, f.y_m - 0.3, f"{f.N_kN:.0f}", fontsize=8, ha="center")
        ax.set_title("Plan view (red = util > 100%)")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Foundation impedance (SSI)
# ---------------------------------------------------------------------------

class ImpedancePage(BasePage):
    title = "Foundation impedance"

    def __init__(self, master):
        super().__init__(master)
        f = self.form_frame
        self.B = LabeledEntry(f, "B (m)", "3.0")
        self.L = LabeledEntry(f, "L (m)", "3.0")
        self.G = LabeledEntry(f, "G (MPa)", "40")
        self.nu = LabeledEntry(f, "Poisson nu", "0.30")
        self.freq = LabeledEntry(f, "Frequency (Hz)", "2.0")
        for i, w in enumerate([self.B, self.L, self.G, self.nu, self.freq]):
            w.grid(row=i, column=0, sticky="w", pady=1)

    def run(self) -> None:
        from foundationdesignjm.dynamics import rectangular_footing_impedance
        imp = rectangular_footing_impedance(
            B_m=self.B.get_float(3.0), L_m=self.L.get_float(3.0),
            G_MPa=self.G.get_float(40), nu=self.nu.get_float(0.30),
            frequency_Hz=self.freq.get_float(2.0),
        )
        o = self.output
        o.writeln("==== FOUNDATION IMPEDANCE (Gazetas 1991) ====", tag="title")
        o.writeln(f"  V_s = {imp.V_s():.0f} m/s")
        for name, d in [("vertical", imp.vertical),
                        ("horizontal_x", imp.horizontal_x),
                        ("horizontal_y", imp.horizontal_y),
                        ("rocking_x", imp.rocking_x),
                        ("rocking_y", imp.rocking_y),
                        ("torsion", imp.torsion)]:
            o.writeln(f"  {name:<14}  K_static = {d.K_static:>12,.0f}  "
                     f"k_dyn = {d.k_dyn:.3f}  c_dyn = {d.c_dyn:.3f}")
        # Plot stiffness vs frequency
        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)
        from foundationdesignjm.dynamics import rectangular_footing_impedance as rfi
        freqs = np.linspace(0.1, 10, 30)
        Kv = []; Kh = []
        for f in freqs:
            i2 = rfi(B_m=self.B.get_float(3), L_m=self.L.get_float(3),
                    G_MPa=self.G.get_float(40), frequency_Hz=f)
            Kv.append(i2.vertical.K_dyn)
            Kh.append(i2.horizontal_x.K_dyn)
        ax.plot(freqs, np.array(Kv) / 1000, "b-", lw=1.6, label="K_vertical")
        ax.plot(freqs, np.array(Kh) / 1000, "r-", lw=1.6, label="K_horizontal")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Stiffness (MN/m)")
        ax.set_title("Dynamic stiffness vs frequency")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)


__all__ = [
    "GravityWallPage",
    "CounterfortWallPage",
    "MSEWallPage",
    "AnchoredWallPage",
    "DiaphragmWallPage",
    "CombinedFootingPage",
    "BasementWallPage",
    "MatFoundationPage",
    "ReverseDesignPage",
    "PileGroupPage",
    "ImpedancePage",
]
