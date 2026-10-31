"""Pagina MVC: diseno de zapata aislada.

Demuestra el patron:
1. UI Tkinter recopila inputs y los valida (form binding).
2. Construye dataclass `IsolatedFootingInput` del service.
3. Llama `services.footings.design_isolated_footing(inp)`.
4. Renderiza `FootingDesignResult` en widgets.
5. Maneja excepciones tipadas y muestra mensajes especificos.
"""
from __future__ import annotations
import logging
import tkinter as tk
from tkinter import ttk, messagebox

from ...services.footings import (
    IsolatedFootingInput, design_isolated_footing,
)
from ...exceptions import (
    FoundationError, GeotechError, DesignError, CodeError,
)

log = logging.getLogger("foundationcalc.desktop.isolated_footing")


class IsolatedFootingPage:
    """Pagina MVC para diseno de zapata aislada."""

    def __init__(self, parent: tk.Widget) -> None:
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self) -> None:
        # Form
        form = ttk.LabelFrame(self.frame, text="Inputs")
        form.pack(fill=tk.X, padx=8, pady=8)

        self.vars = {
            "L_x": tk.DoubleVar(value=2.5),
            "L_y": tk.DoubleVar(value=2.5),
            "thickness": tk.DoubleVar(value=0.6),
            "depth": tk.DoubleVar(value=1.0),
            "column_b": tk.DoubleVar(value=0.4),
            "column_h": tk.DoubleVar(value=0.4),
            "fc_MPa": tk.DoubleVar(value=25.0),
            "fy_MPa": tk.DoubleVar(value=420.0),
            "cover_mm": tk.DoubleVar(value=50.0),
            "N": tk.DoubleVar(value=1500.0),
            "M_x": tk.DoubleVar(value=0.0),
            "M_y": tk.DoubleVar(value=0.0),
            "q_allow_kPa": tk.DoubleVar(value=200.0),
        }
        for i, (label, var) in enumerate(self.vars.items()):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(form, text=f"{label}:").grid(
                row=row, column=col, sticky=tk.W, padx=4, pady=2)
            ttk.Entry(form, textvariable=var, width=12).grid(
                row=row, column=col + 1, sticky=tk.W, padx=4, pady=2)

        # Action
        ttk.Button(self.frame, text="Disenar zapata aislada",
                   command=self._on_design).pack(pady=8)

        # Output
        self.output = tk.Text(self.frame, height=18, font=("Consolas", 9))
        self.output.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    def _on_design(self) -> None:
        """Handler puro: lee form -> llama service -> renderiza."""
        try:
            inp = IsolatedFootingInput(
                L_x=self.vars["L_x"].get(),
                L_y=self.vars["L_y"].get(),
                thickness=self.vars["thickness"].get(),
                depth=self.vars["depth"].get(),
                column_b=self.vars["column_b"].get(),
                column_h=self.vars["column_h"].get(),
                fc_MPa=self.vars["fc_MPa"].get(),
                fy_MPa=self.vars["fy_MPa"].get(),
                cover_mm=self.vars["cover_mm"].get(),
                N=self.vars["N"].get(),
                M_x=self.vars["M_x"].get(),
                M_y=self.vars["M_y"].get(),
                q_allow_kPa=self.vars["q_allow_kPa"].get(),
            )
            result = design_isolated_footing(inp)
            self._render(result)
            log.info("Isolated footing designed: DCR=%.2f",
                     result.punching.get("DCR", 0))
        except GeotechError as exc:
            log.warning("Geotech error: %s", exc)
            messagebox.showerror("Datos de suelo", str(exc))
        except DesignError as exc:
            log.warning("Design error: %s", exc)
            messagebox.showerror("Diseno RC", str(exc))
        except CodeError as exc:
            log.warning("Code error: %s", exc)
            messagebox.showerror("Norma EC2/EC7", str(exc))
        except FoundationError as exc:
            log.warning("Foundation error: %s", exc)
            messagebox.showerror("Error de diseno", str(exc))
        except Exception as exc:  # pragma: no cover
            log.exception("Unexpected error")
            messagebox.showerror("Error inesperado", str(exc))

    def _render(self, result) -> None:
        self.output.delete("1.0", tk.END)
        lines = [
            "=" * 50,
            "DISENO ZAPATA AISLADA (MVC)",
            "=" * 50,
            "",
            "PRESIONES:",
        ]
        for k, v in result.pressures.items():
            lines.append(f"  {k:20s} = {v:12.2f} kPa")
        lines += ["", "PUNCHING SHEAR:"]
        for k, v in result.punching.items():
            if isinstance(v, (int, float)):
                lines.append(f"  {k:20s} = {v:12.2f}")
            else:
                lines.append(f"  {k:20s} = {v}")
        lines += ["", "FLEXION X:"]
        for k, v in result.flexure_x.items():
            if isinstance(v, (int, float)):
                lines.append(f"  {k:20s} = {v:12.4f}")
        lines += ["", "FLEXION Y:"]
        for k, v in result.flexure_y.items():
            if isinstance(v, (int, float)):
                lines.append(f"  {k:20s} = {v:12.4f}")
        if result.notes:
            lines += ["", "NOTAS:"]
            lines += [f"  - {n}" for n in result.notes]
        self.output.insert("1.0", "\n".join(lines))
