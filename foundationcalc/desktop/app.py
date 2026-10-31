"""Main Tk window for FoundationCalc — RSWall-style ribbon UI.

Layout (top → bottom):

    ┌──────────────────────────────────────────────────────────────────────┐
    │ Quick-access  ·  FoundationCalc  ·  🔍 Search   ☼ / ☽            │   title bar
    ├──────────────────────────────────────────────────────────────────────┤
    │  File · Home · Footings · Walls · Deep & Dyn. · Results · Help       │   ribbon tabs
    │  [Big icon buttons grouped by function]                              │   ribbon body
    ├────────────┬─────────────────────────────────────────────────────────┤
    │ Project    │  Project1   ✕   Project2  ✕  …                          │   project tabs
    │ Tree       │                                                         │
    │            │   form ┊ matplotlib canvas + scrolled output            │   center
    ├────────────┴─────────────────────────────────────────────────────────┤
    │ Ready · Data Tips: Max | Min | None · (x, y)                         │   status bar
    └──────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from .._brand import NAME as _BRAND_NAME, TAGLINE as _BRAND_TAGLINE
from .pages import (
    BasePage, CptPipelinePage, CustomFootingPage,
    EC8SpectrumPage, RetainingWallPage,
)
from .pages_extra import (
    AnchoredWallPage, BasementWallPage, CombinedFootingPage,
    CounterfortWallPage, DiaphragmWallPage, GravityWallPage,
    ImpedancePage, MatFoundationPage, MSEWallPage,
    PileGroupPage, ReverseDesignPage,
)
from .pages_new import (
    CranePage, FailureModePage, MultiLayerBcPage, PileAxialCapacityPage,
    PileCapPage, PileLateralPage, SeismicFootingPage, SptPage, StrapBeamPage,
    StrengtheningPage,
)
from .project_tree import ProjectTree
from .ribbon import Ribbon, RibbonAction, RibbonGroup, RibbonTab
from .welcome import ask_welcome


# ---------------------------------------------------------------------------
# Page registry (key → class)
# ---------------------------------------------------------------------------

PAGES = {
    "custom_footing":   CustomFootingPage,
    "combined_footing": CombinedFootingPage,
    "mat":              MatFoundationPage,
    "cpt":              CptPipelinePage,
    "reverse":          ReverseDesignPage,
    "cantilever_wall":  RetainingWallPage,
    "gravity_wall":     GravityWallPage,
    "counterfort_wall": CounterfortWallPage,
    "mse_wall":         MSEWallPage,
    "anchored_wall":    AnchoredWallPage,
    "diaphragm_wall":   DiaphragmWallPage,
    "basement_wall":    BasementWallPage,
    "pile_group":       PileGroupPage,
    "impedance":        ImpedancePage,
    "ec8":              EC8SpectrumPage,
    # New designers (added in this session)
    "crane":            CranePage,
    "pile_axial":       PileAxialCapacityPage,
    "pile_lateral":     PileLateralPage,
    "pile_cap":         PileCapPage,
    "strap_beam":       StrapBeamPage,
    "strengthening":    StrengtheningPage,
    "seismic_footing":  SeismicFootingPage,
    "spt":              SptPage,
    "multilayer_bc":    MultiLayerBcPage,
    "failure_mode":     FailureModePage,
}


# ---------------------------------------------------------------------------
# Mejora B: MVC pages (coexisten con las legacy; uso de services/ y exceptions)
# ---------------------------------------------------------------------------
MVC_PAGES: Dict[str, type] = {}
try:
    from .pages_mvc import (
        IsolatedFootingPage as _MvcIsolated,
        MononobeOkabePage as _MvcMononobe,
        BearingCapacityPage as _MvcBearing,
    )
    MVC_PAGES.update({
        "mvc_isolated_footing": _MvcIsolated,
        "mvc_mononobe_okabe":   _MvcMononobe,
        "mvc_bearing_capacity": _MvcBearing,
    })
except Exception as _exc:  # pragma: no cover
    import logging as _logging
    _logging.getLogger("foundationcalc.desktop").warning(
        "No se pudieron cargar paginas MVC: %s", _exc)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class FoundationDesignApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title(_BRAND_NAME)
        self.geometry("1400x880")
        self.minsize(1200, 760)
        self.configure(bg="#f3f3f3")

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("vista" if sys.platform == "win32" else "clam")
        except tk.TclError:
            self.style.theme_use("default")
        self.style.configure("TButton", padding=(10, 4))

        self._current_page: Optional[BasePage] = None
        self._pages_cache: Dict[str, BasePage] = {}
        self._theme = "light"

        self._build_title_bar()
        self._build_ribbon()
        self._build_main_body()
        self._build_status_bar()
        self._build_menu()

        self.after(120, self._show_welcome)

    # ------------------------------------------------------------------
    # Title bar
    # ------------------------------------------------------------------
    def _build_title_bar(self) -> None:
        bar = tk.Frame(self, bg="#ffffff", height=36)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        quick = tk.Frame(bar, bg="#ffffff")
        quick.pack(side="left", padx=8)
        for icon, tip, cb in [
            ("🏠", "New project", self._new_project),
            ("💾", "Save inputs (JSON)", self.save_inputs),
            ("📂", "Load inputs (JSON)", self.load_inputs),
            ("↶",  "Run (refresh)", self._run_current),
            ("📑", "Report (PDF)",
             lambda: self._current_page and self._save_pdf(self._current_page)),
        ]:
            b = tk.Label(quick, text=icon, font=("Segoe UI Emoji", 11),
                        bg="#ffffff", cursor="hand2", padx=4)
            b.pack(side="left")
            b.bind("<Button-1>", lambda _e, c=cb: c())
            self._tooltip(b, tip)

        brand = tk.Label(bar, text=_BRAND_NAME,
                        bg="#ffffff", fg="#1f497d",
                        font=("Segoe UI", 11, "bold"))
        brand.pack(side="left", expand=True)

        right = tk.Frame(bar, bg="#ffffff")
        right.pack(side="right", padx=8)
        self.theme_toggle = tk.Label(right, text="☼ Light", bg="#ffffff",
                                    fg="#1f497d",
                                    font=("Segoe UI", 9, "bold"),
                                    cursor="hand2", padx=8)
        self.theme_toggle.pack(side="right")
        self.theme_toggle.bind("<Button-1>", lambda _e: self._toggle_theme())
        self._tooltip(self.theme_toggle, "Toggle light / dark theme")

        self.search_var = tk.StringVar()
        search = tk.Entry(right, textvariable=self.search_var,
                         font=("Segoe UI", 9), width=22, bd=1, relief="solid")
        search.pack(side="right", padx=(0, 8))
        search.insert(0, "🔍  Search commands (Ctrl+Q)")
        search.bind("<FocusIn>",
                   lambda _e: search.delete(0, "end")
                   if search.get().startswith("🔍") else None)
        search.bind("<Return>", lambda _e: self._search_jump())
        self.bind_all("<Control-q>", lambda _e: search.focus_set())

    # ------------------------------------------------------------------
    # Ribbon
    # ------------------------------------------------------------------
    def _build_ribbon(self) -> None:
        self.ribbon = Ribbon(self, theme=self._theme)
        self.ribbon.pack(fill="x", side="top")
        self.ribbon.set_tabs(self._build_tab_definitions())

    def _build_tab_definitions(self) -> List[RibbonTab]:
        def page(key):
            return lambda: self._show_page(key)

        return [
            RibbonTab("File", [
                RibbonGroup("Project", [
                    RibbonAction("New", self._new_project, "🗋"),
                    RibbonAction("Open\ninputs", self.load_inputs, "📂"),
                    RibbonAction("Save\ninputs", self.save_inputs, "💾"),
                ]),
                RibbonGroup("Quit", [
                    RibbonAction("Exit", self.destroy, "✕"),
                ]),
            ]),
            RibbonTab("Home", [
                RibbonGroup("Display", [
                    RibbonAction("Run", self._run_current, "▶"),
                    RibbonAction("Refresh", self._run_current, "↻"),
                ]),
                RibbonGroup("Reports", [
                    RibbonAction("PDF\nreport",
                                lambda: self._current_page and self._save_pdf(self._current_page),
                                "📑"),
                    RibbonAction("Save\nplot",
                                lambda: self._current_page and self._current_page._save_plot(),
                                "🖼"),
                    RibbonAction("DXF",
                                lambda: self._current_page and self._save_dxf(self._current_page),
                                "▭"),
                ]),
                RibbonGroup("Help", [
                    RibbonAction("About", self._about, "ℹ"),
                ]),
            ]),
            RibbonTab("Footings", [
                RibbonGroup("Shallow", [
                    RibbonAction("Isolated\nfooting", page("custom_footing"), "▣"),
                    RibbonAction("Combined", page("combined_footing"), "▤"),
                    RibbonAction("Strap\nbeam", page("strap_beam"), "═"),
                ]),
                RibbonGroup("Mat / raft", [
                    RibbonAction("Mat\n(Winkler)", page("mat"), "▦"),
                ]),
                RibbonGroup("Special", [
                    RibbonAction("Tower\ncrane", page("crane"), "⊥"),
                    RibbonAction("Seismic\nfooting", page("seismic_footing"), "≋"),
                ]),
                RibbonGroup("From CPT", [
                    RibbonAction("CPT\npipeline", page("cpt"), "↧"),
                    RibbonAction("Reverse\ndesign", page("reverse"), "⟲"),
                ]),
                RibbonGroup("Strengthening", [
                    RibbonAction("Under-\npinning", page("strengthening"), "⇪"),
                ]),
            ]),
            RibbonTab("Walls", [
                RibbonGroup("Cantilever", [
                    RibbonAction("Cantilever", page("cantilever_wall"), "Г"),
                    RibbonAction("Counterfort", page("counterfort_wall"), "Γ"),
                    RibbonAction("Basement", page("basement_wall"), "⊥"),
                ]),
                RibbonGroup("Gravity / Modular", [
                    RibbonAction("Gravity", page("gravity_wall"), "▲"),
                    RibbonAction("MSE", page("mse_wall"), "◫"),
                ]),
                RibbonGroup("Excavation", [
                    RibbonAction("Anchored", page("anchored_wall"), "↘"),
                    RibbonAction("Diaphragm", page("diaphragm_wall"), "║"),
                ]),
            ]),
            RibbonTab("Deep & Dynamics", [
                RibbonGroup("Piles", [
                    RibbonAction("Axial\ncapacity", page("pile_axial"), "↡"),
                    RibbonAction("Pile\ngroup", page("pile_group"), "⋮⋮"),
                    RibbonAction("Pile\ncap", page("pile_cap"), "▥"),
                    RibbonAction("Lateral\n(p-y)", page("pile_lateral"), "⇉"),
                ]),
                RibbonGroup("Soil-structure", [
                    RibbonAction("Foundation\nimpedance", page("impedance"), "≈"),
                ]),
                RibbonGroup("Seismic", [
                    RibbonAction("EC8\nspectrum", page("ec8"), "⟆"),
                ]),
            ]),
            RibbonTab("Geotech", [
                RibbonGroup("In-situ tests", [
                    RibbonAction("SPT\ncorrelations", page("spt"), "↡"),
                    RibbonAction("CPT\npipeline", page("cpt"), "↧"),
                ]),
                RibbonGroup("Bearing capacity", [
                    RibbonAction("Multi-\nlayer", page("multilayer_bc"), "▦"),
                    RibbonAction("Failure\nmode", page("failure_mode"), "△"),
                ]),
            ]),
            RibbonTab("Results", [
                RibbonGroup("Document", [
                    RibbonAction("PDF\nreport",
                                lambda: self._current_page and self._save_pdf(self._current_page),
                                "📑"),
                    RibbonAction("Save\nplot",
                                lambda: self._current_page and self._current_page._save_plot(),
                                "🖼"),
                ]),
                RibbonGroup("Export", [
                    RibbonAction("DXF",
                                lambda: self._current_page and self._save_dxf(self._current_page),
                                "▭"),
                    RibbonAction("SAFE\n.s2k",
                                lambda: self._current_page and self._save_safe(self._current_page),
                                "≣"),
                ]),
            ]),
            RibbonTab("Help", [
                RibbonGroup("Info", [
                    RibbonAction("About", self._about, "ℹ"),
                ]),
            ]),
            # Mejora B: nuevas paginas MVC (coexisten con las legacy)
            RibbonTab("MVC (new)", [
                RibbonGroup("Shallow", [
                    RibbonAction("Isolated\n(MVC)", page("mvc_isolated_footing"), "▣"),
                    RibbonAction("Bearing\n(MVC)", page("mvc_bearing_capacity"), "▦"),
                ]),
                RibbonGroup("Seismic", [
                    RibbonAction("Mononobe\n-Okabe", page("mvc_mononobe_okabe"), "≋"),
                ]),
            ]),
        ]

    # ------------------------------------------------------------------
    # Main body
    # ------------------------------------------------------------------
    def _build_main_body(self) -> None:
        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=4, pady=2)

        left = ttk.Frame(body, padding=4)
        body.add(left, weight=1)
        self.tree = ProjectTree(left)
        self.tree.pack(fill="both", expand=True)
        self.tree.on_select(self._on_tree_select)

        right = ttk.Frame(body, padding=0)
        body.add(right, weight=8)

        self.project_tab_bar = tk.Frame(right, bg="#ffffff", height=24)
        self.project_tab_bar.pack(fill="x", side="top")
        self._project_tabs: List[tk.Frame] = []
        self._add_project_tab("Project1", active=True)

        self.page_container = ttk.Frame(right)
        self.page_container.pack(fill="both", expand=True)

    def _add_project_tab(self, name: str, active: bool = False) -> None:
        tab = tk.Frame(self.project_tab_bar, bg="#ffffff", padx=6, pady=2)
        tab.pack(side="left")
        lbl = tk.Label(tab,
                      text=("▶ " + name) if active else name,
                      bg="#ffffff",
                      fg=("#1f497d" if active else "#666666"),
                      font=("Segoe UI", 9, "bold" if active else "normal"),
                      cursor="hand2")
        lbl.pack(side="left")
        x = tk.Label(tab, text=" ✕", bg="#ffffff", fg="#aaaaaa",
                    font=("Segoe UI", 8), cursor="hand2")
        x.pack(side="left")
        self._project_tabs.append(tab)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------
    def _build_status_bar(self) -> None:
        bar = tk.Frame(self, bg="#e9eef3", height=22)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self.status_label = tk.Label(bar, text="Ready", bg="#e9eef3",
                                    fg="#333333", font=("Segoe UI", 9))
        self.status_label.pack(side="left", padx=8)
        right = tk.Frame(bar, bg="#e9eef3")
        right.pack(side="right", padx=8)
        tk.Label(right, text="Data Tips:", bg="#e9eef3", fg="#666",
                font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        for tip in ["Max", "Min", "None"]:
            tk.Label(right, text=tip, bg="#dfe6ee", fg="#1f497d",
                    font=("Segoe UI", 9, "bold"), padx=6,
                    ).pack(side="left", padx=2)
        self.coords_label = tk.Label(right, text="(x, y)", bg="#e9eef3",
                                    fg="#1f497d",
                                    font=("Consolas", 9), padx=8)
        self.coords_label.pack(side="left", padx=(8, 0))

    def set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def set_coords(self, x: Optional[float], y: Optional[float]) -> None:
        if x is None or y is None:
            self.coords_label.configure(text="(x, y)")
        else:
            self.coords_label.configure(text=f"({x:7.2f}, {y:7.2f})")

    # ------------------------------------------------------------------
    # Menu (keyboard shortcuts)
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New project    Ctrl+N",
                             command=self._new_project)
        file_menu.add_command(label="Save inputs…    Ctrl+S",
                             command=self.save_inputs)
        file_menu.add_command(label="Load inputs…    Ctrl+O",
                             command=self.load_inputs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)
        self.bind_all("<Control-s>", lambda _e: self.save_inputs())
        self.bind_all("<Control-o>", lambda _e: self.load_inputs())
        self.bind_all("<Control-n>", lambda _e: self._new_project())

    # ------------------------------------------------------------------
    # Welcome + page-switching
    # ------------------------------------------------------------------
    def _show_welcome(self) -> None:
        choice = ask_welcome(self)
        if choice is None:
            return
        self.set_status(f"Template: {choice.template_key}  ·  "
                        f"{choice.design_standard}  ·  {choice.sub_type}")
        if choice.template_key != "empty":
            self._show_page(choice.template_key)
            self.tree.set_project_name(f" {choice.template_key}")
            self.tree.add_item("Geometry", choice.sub_type)
            self.tree.add_item("Soils", "Default soil", color="#9b6dff")

    def _new_project(self) -> None:
        if self._current_page:
            self._current_page.pack_forget()
            self._current_page = None
        self.tree.clear()
        self.tree.set_project_name(" Project")
        self._show_welcome()

    def _show_page(self, key: str) -> None:
        if key in MVC_PAGES:
            self._show_mvc_page(key)
            return
        if key not in PAGES:
            return
        if self._current_page is not None:
            self._current_page.pack_forget()
        page = self._pages_cache.get(key)
        if page is None:
            page = PAGES[key](self.page_container)
            self._pages_cache[key] = page
            self._inject_coord_tracking(page)
        page.pack(fill="both", expand=True)
        self._current_page = page
        self.set_status(f"Designer: {PAGES[key].__name__}")

    def _show_mvc_page(self, key: str) -> None:
        """Mejora B: muestra una pagina MVC (sin acoplar a BasePage)."""
        if self._current_page is not None:
            try:
                self._current_page.pack_forget()
            except Exception:
                pass
            self._current_page = None
        page_obj = self._pages_cache.get(key)
        if page_obj is None:
            cls = MVC_PAGES[key]
            page_obj = cls(self.page_container)
            self._pages_cache[key] = page_obj
        page_obj.frame.pack(fill="both", expand=True)
        # Wrap in a shim so subsequent legacy switches still can call pack_forget
        self._current_page = page_obj.frame
        self.set_status(f"Designer (MVC): {MVC_PAGES[key].__name__}")

    def _run_current(self) -> None:
        if self._current_page is not None:
            self._current_page._run_safely()

    def _inject_coord_tracking(self, page: BasePage) -> None:
        def _on_move(event):
            self.set_coords(event.xdata, event.ydata)
        page.canvas.mpl_connect("motion_notify_event", _on_move)

    # ------------------------------------------------------------------
    # File / save / load
    # ------------------------------------------------------------------
    def save_inputs(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            title="Save project inputs",
        )
        if not path:
            return
        data = {}
        for key, page in self._pages_cache.items():
            page_state = {}
            for widget in page.form_frame.winfo_children():
                if hasattr(widget, "var") and isinstance(widget.var, tk.StringVar):
                    page_state[getattr(widget, "label_text", str(widget))] = widget.var.get()
                elif isinstance(widget, tk.Text):
                    page_state["__text__"] = widget.get("1.0", "end").strip()
            data[key] = page_state
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        self.set_status(f"Saved: {path}")

    def load_inputs(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")], title="Load project inputs",
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for key, state in data.items():
            if key not in PAGES:
                continue
            page = self._pages_cache.get(key)
            if page is None:
                page = PAGES[key](self.page_container)
                self._pages_cache[key] = page
                self._inject_coord_tracking(page)
            for widget in page.form_frame.winfo_children():
                if hasattr(widget, "var") and isinstance(widget.var, tk.StringVar):
                    name = getattr(widget, "label_text", str(widget))
                    if name in state:
                        widget.var.set(state[name])
                elif isinstance(widget, tk.Text) and "__text__" in state:
                    widget.delete("1.0", "end")
                    widget.insert("1.0", state["__text__"])
        self.set_status(f"Loaded inputs for {len(data)} pages")

    # ------------------------------------------------------------------
    # PDF / DXF export
    # ------------------------------------------------------------------
    def _save_pdf(self, page: BasePage) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            title="Save PDF report",
        )
        if not path:
            return
        try:
            from matplotlib.backends.backend_pdf import PdfPages
            from matplotlib.figure import Figure
            with PdfPages(path) as pdf:
                pdf.savefig(page.fig)
                fig_txt = Figure(figsize=(8.27, 11.69))
                ax = fig_txt.add_subplot(1, 1, 1)
                ax.axis("off")
                txt = page.output.text.get("1.0", "end")
                ax.text(0.02, 0.98, f"{type(page).__name__}",
                       fontsize=14, weight="bold", verticalalignment="top",
                       transform=ax.transAxes)
                ax.text(0.02, 0.93, txt, fontsize=8, family="monospace",
                       verticalalignment="top", transform=ax.transAxes)
                pdf.savefig(fig_txt)
            self.set_status(f"PDF saved: {path}")
        except Exception as e:                                  # noqa: BLE001
            messagebox.showerror("Error", f"Could not write PDF:\n{e}")

    def _save_safe(self, page: BasePage) -> None:
        if not isinstance(page, MatFoundationPage):
            messagebox.showwarning(
                "SAFE export",
                "SAFE .s2k export is available for the Mat (Winkler) page only.\n"
                "Open the Mat designer, run it, then click SAFE.",
            )
            return
        solver = getattr(page, "last_solver", None)
        if solver is None:
            messagebox.showwarning(
                "SAFE export",
                "Run the Mat analysis first, then export to SAFE.",
            )
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".s2k", filetypes=[("SAFE", "*.s2k")],
            title="Export mat to SAFE",
        )
        if not path:
            return
        try:
            from foundationcalc.utils.safe_export import export_safe_s2k
            export_safe_s2k(
                nodes_xy=solver.nodes_xy,
                elements=solver.elements,
                column_loads=[(c.x, c.y, c.P, c.Mx, c.My,
                               c.name or f"C{i+1}")
                              for i, c in enumerate(solver._column_loads)],
                uniform_pressure=solver._uniform_pressure,
                thickness=solver.thickness,
                fck_MPa=30.0,
                k_s_kN_m3=solver.k_s,
                output_path=path,
            )
            self.set_status(f"SAFE saved: {path}")
        except Exception as e:                                  # noqa: BLE001
            messagebox.showerror("Error", f"Could not write SAFE .s2k:\n{e}")

    def _save_dxf(self, page: BasePage) -> None:
        if not isinstance(page, (CustomFootingPage, CombinedFootingPage,
                                 CptPipelinePage)):
            messagebox.showwarning("DXF",
                                  "DXF export is available for footing pages only.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".dxf", filetypes=[("DXF", "*.dxf")],
            title="Export footing to DXF",
        )
        if not path:
            return
        try:
            from foundationcalc.utils.dxf_export import export_footing_dxf
            if isinstance(page, CustomFootingPage):
                export_footing_dxf(
                    path,
                    B_mm=page.B.get_float(3500), L_mm=page.L.get_float(3500),
                    column_a_mm=page.col_a.get_float(400),
                    cover_mm=page.cover.get_float(70),
                    rebar_long_count=18, rebar_long_dia_mm=16,
                    rebar_trans_count=18, rebar_trans_dia_mm=16,
                    title=_BRAND_NAME,
                )
            else:
                export_footing_dxf(path, B_mm=2500, L_mm=2500,
                                  column_a_mm=400, title=_BRAND_NAME)
            self.set_status(f"DXF saved: {path}")
        except Exception as e:                                  # noqa: BLE001
            messagebox.showerror("Error", f"Could not write DXF:\n{e}")

    # ------------------------------------------------------------------
    # Theme / search / helpers
    # ------------------------------------------------------------------
    def _toggle_theme(self) -> None:
        self._theme = "dark" if self._theme == "light" else "light"
        self.ribbon.set_theme(self._theme)
        if self._theme == "dark":
            self.configure(bg="#1f1f1f")
            self.theme_toggle.configure(text="☽ Dark", bg="#1f1f1f", fg="#7fb1e0")
        else:
            self.configure(bg="#f3f3f3")
            self.theme_toggle.configure(text="☼ Light", bg="#ffffff", fg="#1f497d")
        self.set_status(f"Theme: {self._theme}")

    def _search_jump(self) -> None:
        q = self.search_var.get().lower().strip()
        if q.startswith("🔍"):
            return
        for key, cls in PAGES.items():
            if q in cls.__name__.lower() or q in cls.title.lower():
                self._show_page(key)
                self.set_status(f"Jumped to: {cls.title}")
                return
        self.set_status(f"No match for '{q}'")

    def _on_tree_select(self, label: str) -> None:
        self.set_status(f"Selected: {label}")

    def _about(self) -> None:
        messagebox.showinfo(
            _BRAND_NAME,
            f"{_BRAND_NAME} — {_BRAND_TAGLINE}.\n\n"
            f"{len(PAGES)} designers · Tkinter ribbon UI · "
            "matplotlib embedded · no extra dependencies."
        )

    def _tooltip(self, widget: tk.Widget, text: str) -> None:
        tip = tk.Toplevel(widget)
        tip.withdraw()
        tip.overrideredirect(True)
        lbl = tk.Label(tip, text=text, bg="#ffffe0", fg="#333333",
                      relief="solid", borderwidth=1, padx=4, pady=2,
                      font=("Segoe UI", 8))
        lbl.pack()
        def _show(_e):
            x = widget.winfo_rootx() + 10
            y = widget.winfo_rooty() + widget.winfo_height() + 2
            tip.geometry(f"+{x}+{y}")
            tip.deiconify()
        def _hide(_e):
            tip.withdraw()
        widget.bind("<Enter>", _show, add="+")
        widget.bind("<Leave>", _hide, add="+")


def main() -> None:
    app = FoundationDesignApp()
    app.mainloop()


if __name__ == "__main__":
    main()
