"""Pagina MVC: capacidad portante multi-layer."""
from __future__ import annotations
import logging
import tkinter as tk
from tkinter import ttk, messagebox

from ...services.bearing import (
    SoilLayerSpec, BearingInput, bearing_capacity_multilayer,
)
from ...exceptions import FoundationError, GeotechError

log = logging.getLogger("foundationcalc.desktop.bearing")


class BearingCapacityPage:
    """Calculadora rapida de capacidad portante multi-layer.

    Para v1 admite un perfil de hasta 3 capas con un widget tabla simple.
    """

    def __init__(self, parent: tk.Widget) -> None:
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self) -> None:
        # Geometria
        geom = ttk.LabelFrame(self.frame, text="Geometria zapata")
        geom.pack(fill=tk.X, padx=8, pady=4)
        self.var_Lx = tk.DoubleVar(value=2.5)
        self.var_Ly = tk.DoubleVar(value=2.5)
        self.var_depth = tk.DoubleVar(value=1.0)
        self.var_kh = tk.DoubleVar(value=0.0)
        for i, (label, var) in enumerate([
            ("L_x (m)", self.var_Lx), ("L_y (m)", self.var_Ly),
            ("Df (m)", self.var_depth), ("kh (sism)", self.var_kh),
        ]):
            ttk.Label(geom, text=label).grid(row=0, column=i * 2, padx=4, pady=2)
            ttk.Entry(geom, textvariable=var, width=8).grid(row=0, column=i * 2 + 1)

        # Capas
        layers_frame = ttk.LabelFrame(self.frame,
                                      text="Perfil de suelo (max 3 capas)")
        layers_frame.pack(fill=tk.X, padx=8, pady=4)
        headers = ["Capa", "espesor (m)", "gamma (kN/m3)",
                   "phi (deg)", "c (kPa)"]
        for i, h in enumerate(headers):
            ttk.Label(layers_frame, text=h).grid(row=0, column=i,
                                                 padx=4, pady=2)
        self.layer_vars: list[dict] = []
        defaults = [(2.0, 18.0, 30.0, 0.0),
                    (5.0, 19.0, 33.0, 0.0),
                    (10.0, 20.0, 35.0, 0.0)]
        for r, (t, g, phi, c) in enumerate(defaults):
            ttk.Label(layers_frame, text=f"L{r+1}").grid(row=r + 1, column=0,
                                                        padx=4)
            vars_dict = {
                "t": tk.DoubleVar(value=t),
                "gamma": tk.DoubleVar(value=g),
                "phi": tk.DoubleVar(value=phi),
                "c": tk.DoubleVar(value=c),
            }
            ttk.Entry(layers_frame, textvariable=vars_dict["t"], width=10
                      ).grid(row=r + 1, column=1, padx=4, pady=2)
            ttk.Entry(layers_frame, textvariable=vars_dict["gamma"], width=10
                      ).grid(row=r + 1, column=2, padx=4, pady=2)
            ttk.Entry(layers_frame, textvariable=vars_dict["phi"], width=10
                      ).grid(row=r + 1, column=3, padx=4, pady=2)
            ttk.Entry(layers_frame, textvariable=vars_dict["c"], width=10
                      ).grid(row=r + 1, column=4, padx=4, pady=2)
            self.layer_vars.append(vars_dict)

        ttk.Button(self.frame, text="Calcular qu",
                   command=self._on_compute).pack(pady=8)
        self.output = tk.Text(self.frame, height=10, font=("Consolas", 9))
        self.output.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    def _on_compute(self) -> None:
        try:
            layers = tuple(
                SoilLayerSpec(
                    thickness=v["t"].get(),
                    gamma=v["gamma"].get(),
                    phi=v["phi"].get(),
                    c=v["c"].get(),
                ) for v in self.layer_vars
                if v["t"].get() > 0
            )
            if not layers:
                raise GeotechError("Define al menos una capa con espesor > 0")
            inp = BearingInput(
                L_x=self.var_Lx.get(), L_y=self.var_Ly.get(),
                depth=self.var_depth.get(), layers=layers,
                seismic_kh=self.var_kh.get(),
            )
            result = bearing_capacity_multilayer(inp)
            self.output.delete("1.0", tk.END)
            lines = [
                "CAPACIDAD PORTANTE MULTI-LAYER",
                "=" * 40,
                f"qu = {result.qu_kPa:.1f} kPa",
                f"qa = {result.qa_kPa:.1f} kPa  (FS = {result.FS})",
                f"metodo = {result.method}",
                "",
                "NOTAS:",
            ]
            lines += [f"  - {n}" for n in result.notes]
            self.output.insert("1.0", "\n".join(lines))
            log.info("Bearing capacity: qu=%.1f kPa", result.qu_kPa)
        except GeotechError as exc:
            log.warning("Geotech: %s", exc)
            messagebox.showerror("Suelo", str(exc))
        except FoundationError as exc:
            log.warning("Foundation: %s", exc)
            messagebox.showerror("Capacidad portante", str(exc))
        except Exception as exc:  # pragma: no cover
            log.exception("Unexpected")
            messagebox.showerror("Error", str(exc))
