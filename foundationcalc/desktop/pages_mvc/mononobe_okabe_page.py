"""Pagina MVC: empuje sismico Mononobe-Okabe (EC8-5)."""
from __future__ import annotations
import logging
import tkinter as tk
from tkinter import ttk, messagebox

from ...services.seismic import (
    MononobeOkabeInput, mononobe_okabe_thrust,
)
from ...exceptions import FoundationError, CodeError

log = logging.getLogger("foundationcalc.desktop.mononobe_okabe")


class MononobeOkabePage:
    """Calculadora de empuje sismico activo Mononobe-Okabe."""

    def __init__(self, parent: tk.Widget) -> None:
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self) -> None:
        form = ttk.LabelFrame(self.frame, text="Mononobe-Okabe (EC8-5)")
        form.pack(fill=tk.X, padx=8, pady=8)
        self.vars = {
            "H (m)": tk.DoubleVar(value=4.0),
            "gamma (kN/m3)": tk.DoubleVar(value=18.0),
            "phi (deg)": tk.DoubleVar(value=30.0),
            "delta (deg)": tk.DoubleVar(value=0.0),
            "beta (deg)": tk.DoubleVar(value=0.0),
            "alpha (deg)": tk.DoubleVar(value=0.0),
            "kh": tk.DoubleVar(value=0.15),
            "kv": tk.DoubleVar(value=0.0),
        }
        for i, (label, var) in enumerate(self.vars.items()):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky=tk.W,
                                             padx=4, pady=2)
            ttk.Entry(form, textvariable=var, width=10).grid(row=i, column=1,
                                                             padx=4, pady=2)
        ttk.Button(self.frame, text="Calcular empuje",
                   command=self._on_compute).pack(pady=8)
        self.output = tk.Text(self.frame, height=10, font=("Consolas", 9))
        self.output.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    def _on_compute(self) -> None:
        try:
            inp = MononobeOkabeInput(
                H=self.vars["H (m)"].get(),
                gamma=self.vars["gamma (kN/m3)"].get(),
                phi=self.vars["phi (deg)"].get(),
                delta=self.vars["delta (deg)"].get(),
                beta=self.vars["beta (deg)"].get(),
                alpha=self.vars["alpha (deg)"].get(),
                kh=self.vars["kh"].get(),
                kv=self.vars["kv"].get(),
            )
            result = mononobe_okabe_thrust(inp)
            self.output.delete("1.0", tk.END)
            lines = [
                "MONONOBE-OKABE (EC8-5)",
                "=" * 40,
                f"K_AE     = {result.K_AE:.4f}",
                f"P_AE     = {result.P_AE:.1f} kN/m",
                f"theta    = {result.theta:.2f} deg",
                "",
                "NOTAS:",
            ]
            lines += [f"  - {n}" for n in result.notes]
            self.output.insert("1.0", "\n".join(lines))
            log.info("Mononobe-Okabe: K_AE=%.4f, P_AE=%.1f",
                     result.K_AE, result.P_AE)
        except CodeError as exc:
            log.warning("Code error: %s", exc)
            messagebox.showerror("Norma EC8-5",
                                 f"Caso fuera de aplicabilidad:\n{exc}")
        except FoundationError as exc:
            log.warning("Foundation error: %s", exc)
            messagebox.showerror("Mononobe-Okabe", str(exc))
        except Exception as exc:  # pragma: no cover
            log.exception("Unexpected error")
            messagebox.showerror("Error inesperado", str(exc))
