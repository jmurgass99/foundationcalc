"""RSWall-style ribbon widget for the FoundationDesignJm desktop app.

The ribbon has two levels:

1. **Tab bar** (top): "File", "Home", "Footings", "Walls", "Deep & Dyn.",
   "Results", "Help". Clicking a tab swaps the ribbon body below.
2. **Ribbon body**: a horizontal strip of **groups**. Each group is a
   small framed area containing one big icon-label button (or two
   stacked small buttons) plus a centred group-name label at the
   bottom.

The user supplies a list of `RibbonTab` objects, each containing
`RibbonGroup`s, each containing `RibbonAction`s. Clicking an action
triggers its callback.

This widget is **theme-aware**: in `light` mode the tab bar is the
Office-blue band `#1f497d` with white text; the body is `#f3f3f3` with
black labels. A `set_theme("dark")` switches both.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk
from typing import Callable, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RibbonAction:
    """One button inside a ribbon group."""

    label: str
    callback: Callable[[], None]
    icon: str = "*"                # ASCII glyph — replaceable with image later
    tooltip: str = ""
    big: bool = True               # True = full-height button, False = compact


@dataclass
class RibbonGroup:
    """A framed group of related actions."""

    name: str
    actions: List[RibbonAction] = field(default_factory=list)


@dataclass
class RibbonTab:
    """A top-level ribbon tab (File / Home / ...)."""

    name: str
    groups: List[RibbonGroup] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Theme palettes
# ---------------------------------------------------------------------------

_PALETTE = {
    "light": {
        "tab_bg": "#1f497d",
        "tab_fg": "#ffffff",
        "tab_active_bg": "#ffffff",
        "tab_active_fg": "#1f497d",
        "body_bg": "#f3f3f3",
        "group_bg": "#fafafa",
        "group_border": "#cccccc",
        "label_fg": "#222222",
        "label_muted": "#666666",
        "btn_hover": "#e1ecf7",
    },
    "dark": {
        "tab_bg": "#0d2840",
        "tab_fg": "#cfcfcf",
        "tab_active_bg": "#2a2a2a",
        "tab_active_fg": "#7fb1e0",
        "body_bg": "#1f1f1f",
        "group_bg": "#2a2a2a",
        "group_border": "#444444",
        "label_fg": "#dddddd",
        "label_muted": "#999999",
        "btn_hover": "#3a3a3a",
    },
}


# ---------------------------------------------------------------------------
# Ribbon widget
# ---------------------------------------------------------------------------

class Ribbon(tk.Frame):
    """The full ribbon (tab strip + body)."""

    def __init__(self, master: tk.Misc, theme: str = "light", **kwargs):
        super().__init__(master, **kwargs)
        self.theme = theme
        self.tabs: List[RibbonTab] = []
        self.current_tab_index = 0

        self.tab_strip = tk.Frame(self, height=30)
        self.tab_strip.pack(fill="x", side="top")
        self.body = tk.Frame(self, height=86)
        self.body.pack(fill="x", side="top")

        self._tab_buttons: List[tk.Label] = []
        self._apply_theme()

    # ------------------------------------------------------------------ API
    def set_tabs(self, tabs: List[RibbonTab]) -> None:
        """Define the entire ribbon contents."""
        self.tabs = tabs
        self._rebuild_tab_strip()
        self._render_body(0)

    def set_theme(self, theme: str) -> None:
        """Switch between 'light' and 'dark'."""
        if theme not in _PALETTE:
            raise ValueError(f"Unknown theme '{theme}'")
        self.theme = theme
        self._apply_theme()
        self._rebuild_tab_strip()
        self._render_body(self.current_tab_index)

    # ------------------------------------------------------- internals ----
    @property
    def palette(self) -> dict:
        return _PALETTE[self.theme]

    def _apply_theme(self) -> None:
        p = self.palette
        self.configure(bg=p["body_bg"])
        self.tab_strip.configure(bg=p["tab_bg"])
        self.body.configure(bg=p["body_bg"])

    def _rebuild_tab_strip(self) -> None:
        for w in self.tab_strip.winfo_children():
            w.destroy()
        self._tab_buttons.clear()
        p = self.palette
        for i, tab in enumerate(self.tabs):
            lbl = tk.Label(
                self.tab_strip, text=f"  {tab.name}  ",
                fg=p["tab_fg"], bg=p["tab_bg"],
                font=("Segoe UI", 10),
                padx=12, pady=6, cursor="hand2",
            )
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda _e, idx=i: self._on_tab_click(idx))
            self._tab_buttons.append(lbl)
        if self._tab_buttons:
            self._highlight_tab(self.current_tab_index)

    def _highlight_tab(self, idx: int) -> None:
        p = self.palette
        for i, lbl in enumerate(self._tab_buttons):
            if i == idx:
                lbl.configure(bg=p["tab_active_bg"], fg=p["tab_active_fg"],
                              font=("Segoe UI", 10, "bold"))
            else:
                lbl.configure(bg=p["tab_bg"], fg=p["tab_fg"],
                              font=("Segoe UI", 10))

    def _on_tab_click(self, idx: int) -> None:
        self.current_tab_index = idx
        self._highlight_tab(idx)
        self._render_body(idx)

    def _render_body(self, idx: int) -> None:
        for w in self.body.winfo_children():
            w.destroy()
        if not self.tabs or idx >= len(self.tabs):
            return
        p = self.palette
        tab = self.tabs[idx]
        for grp in tab.groups:
            self._build_group(self.body, grp)

    def _build_group(self, parent: tk.Frame, group: RibbonGroup) -> None:
        p = self.palette
        # Outer frame with a thin border on the right (group separator)
        outer = tk.Frame(parent, bg=p["body_bg"])
        outer.pack(side="left", fill="y", padx=(0, 6), pady=2)

        inner = tk.Frame(outer, bg=p["group_bg"],
                        highlightbackground=p["group_border"],
                        highlightthickness=1)
        inner.pack(side="top", fill="both", expand=True, padx=2, pady=2)

        # Stack actions horizontally (big buttons) or vertically (small)
        action_row = tk.Frame(inner, bg=p["group_bg"])
        action_row.pack(side="top", fill="both", expand=True, padx=4, pady=(4, 0))

        big_actions = [a for a in group.actions if a.big]
        small_actions = [a for a in group.actions if not a.big]
        for a in big_actions:
            self._make_big_button(action_row, a)
        if small_actions:
            small_col = tk.Frame(action_row, bg=p["group_bg"])
            small_col.pack(side="left", fill="y", padx=(2, 0))
            for a in small_actions:
                self._make_small_button(small_col, a)

        # Group name at the bottom
        tk.Label(inner, text=group.name, bg=p["group_bg"],
                fg=p["label_muted"], font=("Segoe UI", 8),
                ).pack(side="bottom", pady=(0, 2))

    def _make_big_button(self, parent, action: RibbonAction) -> None:
        p = self.palette
        wrap_lines = action.label.split(" ")
        if len(wrap_lines) > 2:
            wrap_lines = [" ".join(wrap_lines[:-1]), wrap_lines[-1]]
        text_label = "\n".join(wrap_lines) if len(wrap_lines) > 1 else action.label

        btn = tk.Frame(parent, bg=p["group_bg"], cursor="hand2", padx=4, pady=2)
        btn.pack(side="left", padx=2)
        icon_lbl = tk.Label(btn, text=action.icon, bg=p["group_bg"],
                           fg=p["label_fg"], font=("Segoe UI Symbol", 18))
        icon_lbl.pack(side="top", pady=(2, 0))
        txt_lbl = tk.Label(btn, text=text_label, bg=p["group_bg"],
                          fg=p["label_fg"], font=("Segoe UI", 8),
                          justify="center", wraplength=80)
        txt_lbl.pack(side="top")

        def _hover_in(_):
            btn.configure(bg=p["btn_hover"])
            icon_lbl.configure(bg=p["btn_hover"])
            txt_lbl.configure(bg=p["btn_hover"])
        def _hover_out(_):
            btn.configure(bg=p["group_bg"])
            icon_lbl.configure(bg=p["group_bg"])
            txt_lbl.configure(bg=p["group_bg"])
        for w in (btn, icon_lbl, txt_lbl):
            w.bind("<Enter>", _hover_in)
            w.bind("<Leave>", _hover_out)
            w.bind("<Button-1>", lambda _e: action.callback())
        if action.tooltip:
            self._attach_tooltip(btn, action.tooltip)

    def _make_small_button(self, parent, action: RibbonAction) -> None:
        p = self.palette
        btn = tk.Frame(parent, bg=p["group_bg"], cursor="hand2")
        btn.pack(side="top", fill="x", padx=2, pady=1)
        ic = tk.Label(btn, text=action.icon, bg=p["group_bg"], fg=p["label_fg"],
                     font=("Segoe UI Symbol", 11), width=2)
        ic.pack(side="left")
        tx = tk.Label(btn, text=action.label, bg=p["group_bg"], fg=p["label_fg"],
                     font=("Segoe UI", 9), anchor="w")
        tx.pack(side="left", fill="x", expand=True)
        for w in (btn, ic, tx):
            w.bind("<Enter>", lambda _e, b=btn, i=ic, t=tx:
                  [b.configure(bg=p["btn_hover"]), i.configure(bg=p["btn_hover"]),
                   t.configure(bg=p["btn_hover"])])
            w.bind("<Leave>", lambda _e, b=btn, i=ic, t=tx:
                  [b.configure(bg=p["group_bg"]), i.configure(bg=p["group_bg"]),
                   t.configure(bg=p["group_bg"])])
            w.bind("<Button-1>", lambda _e: action.callback())
        if action.tooltip:
            self._attach_tooltip(btn, action.tooltip)

    def _attach_tooltip(self, widget: tk.Widget, text: str) -> None:
        """Simple tooltip on hover."""
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


__all__ = ["Ribbon", "RibbonTab", "RibbonGroup", "RibbonAction"]
