"""Servicios de diseño de zapatas."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IsolatedFootingInput:
    """Inputs para diseño de zapata aislada.

    Unidades SI: m para dimensiones, kN para cargas, kPa para presiones.
    """
    L_x: float            # longitud zapata en X (m)
    L_y: float            # longitud zapata en Y (m)
    thickness: float      # peralte (m)
    depth: float = 1.0    # profundidad de cimentación (m)
    column_b: float = 0.4
    column_h: float = 0.4
    fc_MPa: float = 25.0
    fy_MPa: float = 420.0
    cover_mm: float = 50.0
    N: float = 1000.0     # axial (kN, + compresión)
    M_x: float = 0.0      # momento eje X (kN·m)
    M_y: float = 0.0      # momento eje Y (kN·m)
    V_x: float = 0.0
    V_y: float = 0.0
    q_allow_kPa: float = 200.0


@dataclass(frozen=True)
class FootingDesignResult:
    """Resultado del diseño de una zapata aislada."""
    pressures: dict       # {q_max, q_min, q_avg, biaxial corner pressures}
    punching: dict        # {Vu, Vc, DCR, perimeter, governs}
    flexure_x: dict       # {Mu, As_required, As_min, As_chosen, bar_spacing}
    flexure_y: dict
    settlements_mm: float | None = None
    notes: list[str] = field(default_factory=list)


def design_isolated_footing(inp: IsolatedFootingInput) -> FootingDesignResult:
    """Diseña una zapata aislada bajo EC7 + EC2 punching shear + flexión RC.

    Esta es la API pública SIMPLIFICADA que envuelve los módulos internos
    `design/isolated_footing.py` y `design/punching.py`. Retorna un
    ViewModel inmutable apto para JSON, HTML y reportes PDF.
    """
    # No existe `IsolatedFooting` interno en este package todavía; usar
    # placeholder funcional (analítico Meyerhof bi-axial + punching simplificado).
    try:
        from ..design.isolated_footing import IsolatedFooting  # type: ignore
    except ImportError:
        return _placeholder_design(inp)

    foot = IsolatedFooting(
        L_x=inp.L_x, L_y=inp.L_y, thickness=inp.thickness,
        depth=inp.depth,
        column_b=inp.column_b, column_h=inp.column_h,
        fc=inp.fc_MPa * 1e6, fy=inp.fy_MPa * 1e6,
        cover=inp.cover_mm / 1000,
    )
    pressures = foot.compute_pressures(
        N=inp.N * 1e3, M_x=inp.M_x * 1e3, M_y=inp.M_y * 1e3,
    )
    punching = foot.check_punching(N=inp.N * 1e3)
    flex_x = foot.compute_flexure(direction="x", q_max=pressures["q_max"])
    flex_y = foot.compute_flexure(direction="y", q_max=pressures["q_max"])
    return FootingDesignResult(
        pressures=pressures, punching=punching,
        flexure_x=flex_x, flexure_y=flex_y,
        notes=[
            f"q_max = {pressures.get('q_max', 0)/1e3:.1f} kPa "
            f"(allow {inp.q_allow_kPa:.0f} kPa)",
            f"Punching DCR = {punching.get('DCR', 0):.2f}",
        ],
    )


def _placeholder_design(inp: IsolatedFootingInput) -> FootingDesignResult:
    """Diseño placeholder si los módulos internos no están disponibles.
    Sirve para tests headless del service layer."""
    import math
    Ag = inp.L_x * inp.L_y
    e_x = (inp.M_y / inp.N) if inp.N > 0 else 0.0
    e_y = (inp.M_x / inp.N) if inp.N > 0 else 0.0
    q_avg = inp.N / Ag                                          # kPa (kN/m²)
    q_max = q_avg * (1 + 6 * abs(e_x) / inp.L_x + 6 * abs(e_y) / inp.L_y)
    q_min = q_avg * (1 - 6 * abs(e_x) / inp.L_x - 6 * abs(e_y) / inp.L_y)
    pressures = {"q_max": q_max, "q_min": q_min, "q_avg": q_avg}
    # Punching simplificado
    d = inp.thickness - inp.cover_mm / 1000
    bo = 4 * (inp.column_b + d)
    Vc = 0.17 * math.sqrt(inp.fc_MPa) * bo * d * 1e3  # crude (kN)
    Vu = inp.N - q_avg * (inp.column_b + d) * (inp.column_h + d)
    punching = {"Vu": Vu, "Vc": Vc, "DCR": Vu / Vc if Vc > 0 else 99.0,
                "perimeter": bo, "governs": "two-way"}
    flex_default = {"Mu": 0.0, "As_required": 0.0, "As_min": 0.001 * Ag,
                    "As_chosen": 0.0, "bar_spacing": 0.2}
    return FootingDesignResult(
        pressures=pressures, punching=punching,
        flexure_x=flex_default, flexure_y=flex_default,
        notes=["Placeholder design (módulos internos no disponibles)"],
    )
