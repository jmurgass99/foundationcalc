"""Reusable Tkinter widgets for the FoundationDesignJm desktop app."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Sequence


class LabeledEntry(ttk.Frame):
    """A simple label + Entry combo with a default value."""

    def __init__(
        self,
        master: tk.Misc,
        label: str,
        default: str = "",
        unit: str = "",
        width: int = 12,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.label_text = label
        self.unit_text = unit
        self.label = ttk.Label(self, text=label, width=22, anchor="w")
        self.label.grid(row=0, column=0, sticky="w", padx=2, pady=1)
        self.var = tk.StringVar(value=default)
        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.entry.grid(row=0, column=1, sticky="w", padx=2)
        if unit:
            self.unit = ttk.Label(self, text=unit, width=10, anchor="w",
                                 foreground="#555555")
            self.unit.grid(row=0, column=2, sticky="w", padx=2)

    def get_float(self, default: float = 0.0) -> float:
        try:
            return float(self.var.get().replace(",", "."))
        except (ValueError, AttributeError):
            return default

    def get_int(self, default: int = 0) -> int:
        try:
            return int(float(self.var.get().replace(",", ".")))
        except (ValueError, AttributeError):
            return default

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str) -> None:
        self.var.set(value)


class LabeledCombobox(ttk.Frame):
    """Label + Combobox with a list of values."""

    def __init__(
        self,
        master: tk.Misc,
        label: str,
        values: Sequence[str],
        default: Optional[str] = None,
        width: int = 18,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        ttk.Label(self, text=label, width=22, anchor="w").grid(
            row=0, column=0, sticky="w", padx=2, pady=1,
        )
        self.var = tk.StringVar(value=default or (values[0] if values else ""))
        self.combo = ttk.Combobox(
            self, textvariable=self.var, values=list(values),
            state="readonly", width=width,
        )
        self.combo.grid(row=0, column=1, sticky="w", padx=2)

    def get(self) -> str:
        return self.var.get()


class ScrolledOutput(tk.Frame):
    """A Text widget with a scrollbar used as a console-like output area."""

    def __init__(self, master: tk.Misc, height: int = 16, **kwargs):
        super().__init__(master, **kwargs)
        self.text = tk.Text(self, height=height, wrap="word",
                            font=("Consolas", 9), background="#fafafa")
        scrollbar = ttk.Scrollbar(self, orient="vertical",
                                  command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        # Tags for coloured status
        self.text.tag_configure("ok", foreground="#1b8a3a", font=("Consolas", 9, "bold"))
        self.text.tag_configure("fail", foreground="#b00020", font=("Consolas", 9, "bold"))
        self.text.tag_configure("title", foreground="#1f497d",
                                font=("Consolas", 10, "bold"))
        self.text.tag_configure("muted", foreground="#666666")

    def clear(self) -> None:
        self.text.delete("1.0", "end")

    def write(self, text: str, tag: Optional[str] = None) -> None:
        if tag:
            self.text.insert("end", text, tag)
        else:
            self.text.insert("end", text)
        self.text.see("end")

    def writeln(self, text: str = "", tag: Optional[str] = None) -> None:
        self.write(text + "\n", tag)
