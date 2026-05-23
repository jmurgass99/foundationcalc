"""RSWall-style 'Welcome' dialog — pick a designer template at startup.

The dialog shows a grid of template tiles (Custom Footing, Cantilever
Wall, Gravity Wall, MSE Wall, ...) plus a project-settings panel with:

- **Design Standard** dropdown (Eurocode 7, AASHTO, NCMA, ...).
- **Wall / footing type** dropdown.

When the user clicks **OK**, the dialog stores the selection and returns
it to the caller. **Cancel** returns `None`.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, Dict, List, Optional


@dataclass
class WelcomeTemplate:
    key: str
    title: str
    icon: str = "□"
    description: str = ""


@dataclass
class WelcomeChoice:
    template_key: str
    design_standard: str
    sub_type: str


_DEFAULT_TEMPLATES: List[WelcomeTemplate] = [
    WelcomeTemplate("empty",         "Empty project",     "≡"),
    WelcomeTemplate("custom_footing","Isolated footing",  "▣"),
    WelcomeTemplate("combined_footing","Combined footing", "▤"),
    WelcomeTemplate("mat",           "Mat / raft",        "▦"),
    WelcomeTemplate("cpt",           "From CPT data",     "↧"),
    WelcomeTemplate("crane",         "Tower crane pad",   "⊥"),
    WelcomeTemplate("seismic_footing","Seismic footing",  "≋"),
    WelcomeTemplate("strap_beam",    "Strap / tie beam",  "═"),
    WelcomeTemplate("cantilever_wall","Cantilever wall",  "Г"),
    WelcomeTemplate("gravity_wall",  "Gravity wall",      "▲"),
    WelcomeTemplate("counterfort_wall","Counterfort wall","Γ"),
    WelcomeTemplate("mse_wall",      "MSE wall",          "◫"),
    WelcomeTemplate("anchored_wall", "Anchored wall",     "↘"),
    WelcomeTemplate("diaphragm_wall","Diaphragm wall",    "║"),
    WelcomeTemplate("basement_wall", "Basement wall",     "⊥"),
    WelcomeTemplate("pile_axial",    "Pile axial cap.",   "↡"),
    WelcomeTemplate("pile_group",    "Pile group",        "⋮⋮"),
    WelcomeTemplate("pile_cap",      "Pile cap (STM)",    "▥"),
    WelcomeTemplate("pile_lateral",  "Lateral pile p-y",  "⇉"),
    WelcomeTemplate("strengthening", "Strengthening",     "⇪"),
    WelcomeTemplate("impedance",     "Foundation imped.", "≈"),
    WelcomeTemplate("ec8",           "EC8 spectrum",      "⟆"),
    WelcomeTemplate("spt",           "SPT correlations",  "↡"),
    WelcomeTemplate("multilayer_bc", "Multi-layer BC",    "▦"),
    WelcomeTemplate("failure_mode",  "Failure mode",      "△"),
]


class WelcomeDialog(tk.Toplevel):
    """Modal welcome dialog. Use `.result` after closing."""

    DESIGN_STANDARDS = [
        "Eurocode 7 (EN 1997:2004)",
        "Eurocode 7 — Spain NA",
        "AASHTO LRFD (2020)",
        "NCMA SRW Design Manual",
        "British Standard BS 8002",
        "Australian Standard AS 4678",
    ]
    SUB_TYPES = {
        "cantilever_wall": ["Cantilever T-shape", "L-shape (toe only)",
                          "Inverted-L (heel only)", "With shear key"],
        "gravity_wall":    ["Mass concrete", "Masonry", "Gabion", "Crib"],
        "counterfort_wall":["Standard", "With buttresses front"],
        "mse_wall":        ["Segmental block", "Welded wire", "Geogrid"],
        "anchored_wall":   ["Sheet pile", "Soldier pile + lagging",
                          "Continuous bored pile"],
        "diaphragm_wall":  ["Slurry wall", "Secant pile wall"],
        "basement_wall":   ["Propped cantilever", "Cantilever", "Multi-prop"],
        "custom_footing":  ["Isolated rectangular", "Square", "Strip"],
        "combined_footing":["Rectangular (2 col.)", "Trapezoidal (1 at line)"],
        "mat":             ["Flat plate", "Thickened under columns",
                          "Beam-and-slab"],
        "pile_group":      ["Driven piles", "Bored piles", "Micropiles"],
        "cpt":             ["Robertson 2010 SBT"],
        "impedance":       ["Gazetas 1991 (surface rectangle)"],
        "ec8":             ["Spectrum type 1 (M_s > 5.5)",
                          "Spectrum type 2 (M_s ≤ 5.5)"],
        "crane":           ["In-service envelope", "Out-of-service (storm)",
                          "Service + OOS combined"],
        "seismic_footing": ["EN 1998-5 Annex F", "Pseudo-static (Pecker)",
                          "DA-3 ground / structural"],
        "strap_beam":      ["Two-footing strap", "Property-line + interior",
                          "EC8 §5.4.1.2 tie"],
        "pile_axial":      ["Bored pile (alpha+beta)",
                          "Driven precast (alpha+beta)",
                          "CFA pile",
                          "Steel section"],
        "pile_cap":        ["2 piles", "3 piles (equilateral)",
                          "4 piles (rectangular)"],
        "pile_lateral":    ["Matlock soft clay", "Reese sand",
                          "API RP 2A sand/clay"],
        "strengthening":   ["Micropile underpinning",
                          "Mass-concrete pits",
                          "RC enlargement"],
        "spt":             ["Hatanaka-Uchida (sand)",
                          "Peck-Hanson-Thornburn (sand)",
                          "Stroud (clay)"],
        "multilayer_bc":   ["Strong over weak", "Weak over strong",
                          "3+ layers (auto-pick)"],
        "failure_mode":    ["Drained (Vesic)", "Undrained (Vesic)",
                          "Auto from D_R"],
        "empty":           ["—"],
    }

    def __init__(self, master: tk.Tk,
                 templates: Optional[List[WelcomeTemplate]] = None):
        super().__init__(master)
        self.title("Welcome")
        self.transient(master)
        self.grab_set()
        self.geometry("760x620")
        self.minsize(680, 580)
        self.resizable(True, True)
        self.configure(bg="#f3f3f3")
        self.result: Optional[WelcomeChoice] = None
        self.templates = templates or _DEFAULT_TEMPLATES
        self._selected_key = tk.StringVar(value=self.templates[1].key)

        # Title
        title = tk.Label(self, text="  Start with a project template",
                       bg="#f3f3f3", fg="#1f497d",
                       font=("Segoe UI", 13, "bold"), anchor="w")
        title.pack(fill="x", padx=14, pady=(12, 8))

        # Grid of tiles in a scrollable canvas
        grid_frame = tk.Frame(self, bg="#f3f3f3")
        grid_frame.pack(fill="both", expand=True, padx=14, pady=4)

        self._tiles: Dict[str, tk.Frame] = {}
        n_cols = 4
        for i, tpl in enumerate(self.templates):
            row, col = divmod(i, n_cols)
            self._build_tile(grid_frame, tpl, row, col)
        for c in range(n_cols):
            grid_frame.columnconfigure(c, weight=1, uniform="tiles")

        # Project settings frame
        settings = tk.LabelFrame(self, text=" Project settings ",
                                bg="#f3f3f3", fg="#1f497d",
                                font=("Segoe UI", 9, "bold"),
                                bd=1, relief="solid")
        settings.pack(fill="x", padx=14, pady=(10, 8))

        tk.Label(settings, text="Design Standard:", bg="#f3f3f3",
                font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w",
                                          padx=8, pady=4)
        self.design_standard = ttk.Combobox(settings, values=self.DESIGN_STANDARDS,
                                           state="readonly", width=36)
        self.design_standard.set(self.DESIGN_STANDARDS[0])
        self.design_standard.grid(row=0, column=1, sticky="ew", padx=8, pady=4)

        tk.Label(settings, text="Sub-type:", bg="#f3f3f3",
                font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w",
                                          padx=8, pady=4)
        self.sub_type = ttk.Combobox(settings, values=self._get_subtypes(),
                                    state="readonly", width=36)
        self.sub_type.set(self._get_subtypes()[0] if self._get_subtypes() else "")
        self.sub_type.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        settings.columnconfigure(1, weight=1)

        # Actions
        actions = tk.Frame(self, bg="#f3f3f3")
        actions.pack(fill="x", padx=14, pady=(0, 12))
        self.dont_show = tk.BooleanVar(value=False)
        tk.Checkbutton(actions, text="Don't show this next time",
                      variable=self.dont_show, bg="#f3f3f3",
                      font=("Segoe UI", 9)).pack(side="left")
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(
            side="right", padx=(6, 0))
        ttk.Button(actions, text="OK", command=self._ok).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    # ------------------------------------------------------------------
    def _build_tile(self, parent, tpl: WelcomeTemplate, row: int, col: int):
        tile = tk.Frame(parent, bg="white", bd=1, relief="solid",
                       highlightthickness=2,
                       highlightbackground="#cccccc")
        tile.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        parent.rowconfigure(row, weight=1, uniform="rows")
        icon = tk.Label(tile, text=tpl.icon, bg="white", fg="#1f497d",
                       font=("Segoe UI Symbol", 28))
        icon.pack(pady=(10, 0))
        lab = tk.Label(tile, text=tpl.title, bg="white", fg="#222222",
                      font=("Segoe UI", 9), wraplength=130)
        lab.pack(pady=(4, 10), padx=4)

        def _click(_e):
            self._selected_key.set(tpl.key)
            self._update_selection()
        for w in (tile, icon, lab):
            w.bind("<Button-1>", _click)
            w.bind("<Double-Button-1>", lambda _e: self._ok())
            w.configure(cursor="hand2")
        self._tiles[tpl.key] = tile
        self._update_selection()

    def _update_selection(self) -> None:
        sel = self._selected_key.get()
        for k, tile in self._tiles.items():
            tile.configure(
                highlightbackground=("#1f497d" if k == sel else "#cccccc"),
                highlightthickness=(3 if k == sel else 1),
            )
        # Refresh sub-types
        if hasattr(self, "sub_type"):
            subs = self._get_subtypes()
            self.sub_type["values"] = subs
            if subs:
                self.sub_type.set(subs[0])

    def _get_subtypes(self) -> List[str]:
        return self.SUB_TYPES.get(self._selected_key.get(), ["—"])

    # ------------------------------------------------------------------
    def _ok(self):
        self.result = WelcomeChoice(
            template_key=self._selected_key.get(),
            design_standard=self.design_standard.get(),
            sub_type=self.sub_type.get(),
        )
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


def ask_welcome(master: tk.Tk) -> Optional[WelcomeChoice]:
    """Show the welcome dialog and return the user's choice (or None)."""
    dlg = WelcomeDialog(master)
    master.wait_window(dlg)
    return dlg.result


__all__ = [
    "WelcomeChoice",
    "WelcomeTemplate",
    "WelcomeDialog",
    "ask_welcome",
]
