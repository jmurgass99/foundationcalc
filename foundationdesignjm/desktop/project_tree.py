"""Left 'Segment Tree' panel — RSWall-style hierarchical project view.

A `ProjectTree` shows the project structure as collapsible sections:

    Project
    ├── Geometry
    │   ├── Footing 1
    │   └── Column 1
    ├── Soils
    │   ├── Soil 1  (■ purple)
    │   └── Soil 2  (■ green)
    ├── Loads
    │   └── Load Case 1
    └── Reinforcement
        └── Mesh 1

Each item is a row in a `ttk.Treeview`. Items can have a colour swatch
(stored in the item's `text` prefix). The tree exposes:

- `set_project_name(name)`        — change the root label.
- `add_item(parent_id, label, color="")` → new id
- `clear()`                       — remove everything.
- `on_select(callback)`           — register a click handler.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ProjectTree(ttk.Frame):
    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, **kwargs)
        ttk.Label(self, text=" Segment Tree", anchor="w",
                 font=("Segoe UI", 9, "bold"),
                 foreground="#1f497d").pack(fill="x", pady=(2, 1))
        self.tree = ttk.Treeview(self, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True)
        self._project_id = self.tree.insert("", "end", text=" Project",
                                           open=True)
        self._sections: dict[str, str] = {}
        for sec in ("Geometry", "Soils", "Loads", "Reinforcement",
                    "Results"):
            self._sections[sec] = self.tree.insert(
                self._project_id, "end", text=f"  {sec}", open=True,
            )
        self._on_select_callback: Optional[Callable[[str], None]] = None
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # ------------------------------------------------------------------
    def set_project_name(self, name: str) -> None:
        self.tree.item(self._project_id, text=f" {name}")

    def add_item(self, section: str, label: str, color: str = "") -> str:
        """Add an item under one of the standard sections."""
        parent = self._sections.get(section, self._project_id)
        prefix = f"■ " if color else ""
        item_id = self.tree.insert(parent, "end",
                                   text=f"  {prefix}{label}")
        if color:
            try:
                self.tree.tag_configure(f"color_{item_id}", foreground=color)
                self.tree.item(item_id, tags=(f"color_{item_id}",))
            except tk.TclError:
                pass
        return item_id

    def clear(self) -> None:
        for sec_id in self._sections.values():
            for child in self.tree.get_children(sec_id):
                self.tree.delete(child)

    def on_select(self, callback: Callable[[str], None]) -> None:
        self._on_select_callback = callback

    def _on_select(self, _evt) -> None:
        if not self._on_select_callback:
            return
        sel = self.tree.selection()
        if not sel:
            return
        self._on_select_callback(self.tree.item(sel[0], "text").strip())


__all__ = ["ProjectTree"]
