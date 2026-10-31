"""Pile-group analysis under combined V + H + M.

Distributes a column reaction (V vertical, H horizontal, M moment) onto
a group of piles under a **rigid pile-cap** assumption, and reports the
group capacity envelope considering:

- **Vertical distribution** (Engesser / rigid-cap formula):
        N_i = V/n  + M_x·y_i / I_x  + M_y·x_i / I_y
  where I_x = Σ y_i², I_y = Σ x_i² with the pile positions referred to
  the cap centroid.
- **Horizontal distribution** weighted by lateral stiffness (default
  uniform).
- **Group efficiency** for axial loading via Converse-Labarre (s/d):
        E = 1 - phi*(((n-1)*m + (m-1)*n) / (90 * m * n))
  where m × n is the pile arrangement and phi the arctan(d/s).
- **Group efficiency** for lateral loading (Mokwa & Duncan 2001):
        E_h ≈ 0.5 + 0.5·min(s/d / 6, 1.0)    (leading-row reduction)

The result lists the maximum and minimum N_i (compression / tension),
the per-pile H_i and the worst-pile utilisation when compared against
the user-supplied per-pile capacity envelope.

Theory: docs/theory/16_pile_groups.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from foundationcalc._common.audit_status import CalculationStatus, resolve_status

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Group efficiency
# ---------------------------------------------------------------------------

def converse_labarre_efficiency(
    n_rows: int, n_cols: int, spacing_m: float, diameter_m: float,
) -> float:
    """Converse-Labarre group efficiency for axial loading.

    E = 1 − φ · [(n−1)·m + (m−1)·n] / (90 · m · n)
    where φ = atan(d/s) in degrees, m = n_cols, n = n_rows.

    Returns 1.0 when s/d ≥ 4 (no group effect) and decreases with
    closer spacings.
    """
    if n_rows < 1 or n_cols < 1 or diameter_m <= 0:
        return 1.0
    s_over_d = spacing_m / diameter_m
    if s_over_d >= 4.0:
        return 1.0
    phi_deg = math.degrees(math.atan(diameter_m / spacing_m))
    m, n = n_cols, n_rows
    if m * n == 1:
        return 1.0
    E = 1.0 - phi_deg * ((n - 1) * m + (m - 1) * n) / (90.0 * m * n)
    return max(E, 0.5)


def mokwa_duncan_lateral_efficiency(spacing_m: float, diameter_m: float) -> float:
    """Lateral group efficiency from leading-row reduction (Mokwa & Duncan 2001).

    Approximation:  E_h ≈ 0.5 + 0.5·min(s/d / 6, 1.0).
    """
    if diameter_m <= 0:
        return 1.0
    s_d = spacing_m / diameter_m
    return 0.5 + 0.5 * min(s_d / 6.0, 1.0)


# ---------------------------------------------------------------------------
# Group geometry
# ---------------------------------------------------------------------------

class PileInGroup(BaseModel):
    """One pile in a rigid-cap group, defined by its centroidal (x, y)."""

    x_m: float = Field(..., description="x coordinate referred to cap centroid (m)")
    y_m: float = Field(..., description="y coordinate referred to cap centroid (m)")
    diameter_m: float = Field(..., gt=0.05)
    axial_capacity_kN: float = Field(0.0, ge=0,
        description="Per-pile design axial capacity (compression, kN). 0 = unknown.")
    tension_capacity_kN: float = Field(0.0, ge=0,
        description="Per-pile design uplift capacity (kN).")
    lateral_capacity_kN: float = Field(0.0, ge=0,
        description="Per-pile design lateral capacity (kN).")
    name: str = ""


class PileGroup(BaseModel):
    """Rectangular or arbitrary pile group under a rigid cap."""

    piles: List[PileInGroup]
    spacing_m: float = Field(..., gt=0,
        description="Centre-to-centre spacing (mean) for group efficiency.")
    arrangement_rows: int = Field(1, ge=1)
    arrangement_cols: int = Field(1, ge=1)

    @property
    def n(self) -> int:
        return len(self.piles)

    @property
    def I_x(self) -> float:
        """I_x = Σ y_i² (used for moment-induced axial)."""
        return sum(p.y_m ** 2 for p in self.piles)

    @property
    def I_y(self) -> float:
        """I_y = Σ x_i²"""
        return sum(p.x_m ** 2 for p in self.piles)

    def axial_efficiency(self) -> float:
        return converse_labarre_efficiency(
            self.arrangement_rows, self.arrangement_cols,
            self.spacing_m, self.piles[0].diameter_m if self.piles else 1.0,
        )

    def lateral_efficiency(self) -> float:
        return mokwa_duncan_lateral_efficiency(
            self.spacing_m,
            self.piles[0].diameter_m if self.piles else 1.0,
        )


# ---------------------------------------------------------------------------
# Helpers — common pile group layouts
# ---------------------------------------------------------------------------

def rectangular_group(
    n_rows: int, n_cols: int,
    spacing_m: float, diameter_m: float,
    axial_capacity_kN: float = 0.0,
    tension_capacity_kN: float = 0.0,
    lateral_capacity_kN: float = 0.0,
) -> PileGroup:
    """Build a m × n rectangular pile group centred on (0, 0)."""
    piles: List[PileInGroup] = []
    x_centre = (n_cols - 1) / 2.0
    y_centre = (n_rows - 1) / 2.0
    for i in range(n_rows):
        for j in range(n_cols):
            x = (j - x_centre) * spacing_m
            y = (i - y_centre) * spacing_m
            piles.append(PileInGroup(
                x_m=x, y_m=y, diameter_m=diameter_m,
                axial_capacity_kN=axial_capacity_kN,
                tension_capacity_kN=tension_capacity_kN,
                lateral_capacity_kN=lateral_capacity_kN,
                name=f"P{i + 1}{j + 1}",
            ))
    return PileGroup(
        piles=piles, spacing_m=spacing_m,
        arrangement_rows=n_rows, arrangement_cols=n_cols,
    )


# ---------------------------------------------------------------------------
# Force distribution
# ---------------------------------------------------------------------------

@dataclass
class PileForce:
    pile_name: str
    x_m: float
    y_m: float
    N_kN: float
    H_x_kN: float
    H_y_kN: float
    #: Utilización en cada dirección. None = NO EVALUADA (hay demanda en esa
    #: dirección pero la capacidad no se declaró). 0.0 = sin demanda en esa
    #: dirección (no hay nada que comprobar). NUNCA 0.0 por capacidad ausente.
    axial_utilization: Optional[float]
    lateral_utilization: Optional[float]
    in_compression: bool
    tension_utilization: Optional[float] = None
    #: SIN valor por defecto a proposito. Tenerlo en `CALCULADO_CUMPLE` era la
    #: misma "omision = cumplimiento" que la Proof Obligation prohibe, solo que
    #: escrita como default de dataclass: construir el objeto sin pensar en el
    #: veredicto producia un veredicto favorable.
    status: CalculationStatus = CalculationStatus.NO_CALCULADO
    missing_inputs: list[str] = field(default_factory=list)


@dataclass
class PileGroupResult:
    """Bundle of per-pile forces + group-level utilizations.

    Las utilizaciones de grupo son ``None`` cuando la dirección no se pudo evaluar
    (capacidad ausente con demanda presente). ``all_ok`` sólo es ``True`` si el
    estado es ``CALCULADO_CUMPLE``: un grupo con un chequeo sin hacer NO se firma.
    """

    forces: List[PileForce]
    N_max_compression: float
    N_max_tension: float
    H_max_per_pile: float
    axial_efficiency: float
    lateral_efficiency: float
    group_axial_utilization: Optional[float]    # worst pile compression check
    group_tension_utilization: Optional[float]  # worst pile tension check
    group_lateral_utilization: Optional[float]
    governing_pile: str
    all_ok: bool
    #: SIN default favorable, por lo mismo que en `PileForce`.
    status: CalculationStatus = CalculationStatus.NO_CALCULADO
    missing_inputs: list[str] = field(default_factory=list)


def _evidencia(
    group: "PileGroup",
    V_kN: float,
    H_x_kN: float,
    H_y_kN: float,
    M_x_kNm: float,
    M_y_kNm: float,
    faltan: list[str],
) -> dict[str, bool]:
    """Declara, condicion por condicion, que verifico ESTE calculo.

    La Proof Obligation es closed-by-default: si este caller no declara, el
    veredicto es ``NO_CALCULADO``. Asi que cada condicion sale de un predicado
    real sobre los datos, no de un ``True`` de cortesia.

    ``demand_present`` merece explicacion. Una accion total NULA sobre una
    cimentacion no es "demanda cero verificada": es que no se aplico ninguna
    accion, es decir, que el analisis no se llego a correr. Una zapata real
    siempre recibe al menos la carga de su pilar. Por eso una solicitacion
    identicamente nula se declara como demanda AUSENTE y no puede firmar -- que es
    exactamente el caso critico que la directiva exige que nunca acabe en CUMPLE.
    Una demanda pequeña pero no nula si es un resultado, y si puede firmar.

    ``material_present`` se declara a partir de las capacidades: en este modulo el
    dato derivado del material ES la capacidad del pilote (kN), no una clase de
    hormigon. ``reinforcement_present`` es ``True`` porque la armadura no es un
    input de la comprobacion de capacidad de grupo -- no se comprueba aqui, asi
    que no puede faltar aqui; el armado del encepado se verifica en su propio
    calculo y con su propia obligacion de prueba.
    """
    accion_total = abs(V_kN) + abs(H_x_kN) + abs(H_y_kN) + abs(M_x_kNm) + abs(M_y_kNm)
    capacidades_completas = not faltan
    return {
        "demand_present": accion_total > 0.0,
        "capacity_present": capacidades_completas,
        "material_present": capacidades_completas,
        "analysis_executed": bool(group.piles),
        "geometry_present": bool(group.piles) and all(
            p.diameter_m > 0.0 for p in group.piles
        ),
        "reinforcement_present": True,
    }


def distribute_loads_rigid_cap(
    group: PileGroup,
    V_kN: float,            # +down
    H_x_kN: float = 0.0,    # global X shear
    H_y_kN: float = 0.0,    # global Y shear
    M_x_kNm: float = 0.0,   # moment about X (causes Δ N in y direction)
    M_y_kNm: float = 0.0,   # moment about Y (causes Δ N in x direction)
) -> PileGroupResult:
    """Distribute V, H_x, H_y, M_x, M_y over the group under a rigid cap.

    Axial per pile (Engesser):
        N_i = V/n  +  M_x · y_i / I_x  +  M_y · x_i / I_y

    Horizontal per pile (uniform among all piles, then × E_h):
        H_xi = (H_x / n) / E_h        ⇒ each pile must resist this much
        H_yi = (H_y / n) / E_h

    Note: the division by E_h means that for tight groups each pile
    has to resist MORE than the simple uniform share — i.e. the group
    is *less* efficient. The resultant horizontal per pile:
        H_i = √(H_xi² + H_yi²)
    """
    n = group.n
    if n == 0:
        raise ValueError("Group has no piles.")
    I_x = group.I_x
    I_y = group.I_y
    E_axial = group.axial_efficiency()
    E_lat = group.lateral_efficiency()
    forces: List[PileForce] = []
    N_max_c = -float("inf")
    N_min_c = float("inf")
    H_max = 0.0
    worst_pile = ""
    worst_util = 0.0

    for p in group.piles:
        # Axial
        N_i = V_kN / n
        if I_x > 1e-9:
            N_i += M_x_kNm * p.y_m / I_x
        if I_y > 1e-9:
            N_i += M_y_kNm * p.x_m / I_y

        # Lateral
        H_xi = (H_x_kN / n) / max(E_lat, 1e-6)
        H_yi = (H_y_kN / n) / max(E_lat, 1e-6)
        H_i = math.sqrt(H_xi ** 2 + H_yi ** 2)
        H_max = max(H_max, H_i)

        # Utilización por dirección. La regla, idéntica en las tres: si hay
        # DEMANDA y la capacidad es desconocida (<= 0, el default), la utilización
        # es None (NO EVALUADA) y se apunta el input que falta. Si NO hay demanda
        # en esa dirección, es 0.0 (no hay nada que comprobar). Nunca 0.0 —ni un
        # número basura dividido por 1e-6— por capacidad ausente.
        miss: list[str] = []

        if N_i > 1e-9:  # compresión
            if p.axial_capacity_kN > 0.0:
                ax_util: Optional[float] = N_i / (p.axial_capacity_kN * E_axial)
            else:
                ax_util = None
                miss.append("axial_capacity_kN")
        else:
            ax_util = 0.0

        if N_i < -1e-9:  # tracción / levantamiento
            if p.tension_capacity_kN > 0.0:
                tens_util: Optional[float] = (-N_i) / p.tension_capacity_kN
            else:
                tens_util = None
                miss.append("tension_capacity_kN")
        else:
            tens_util = 0.0

        if H_i > 1e-9:  # demanda lateral
            if p.lateral_capacity_kN > 0.0:
                lat_util: Optional[float] = H_i / p.lateral_capacity_kN
            else:
                lat_util = None
                miss.append("lateral_capacity_kN")
        else:
            lat_util = 0.0

        computed = [u for u in (ax_util, tens_util, lat_util) if u is not None]
        pile_gov = max(computed) if computed else None
        pile_status = resolve_status(
            pile_gov,
            missing_inputs=miss,
            **_evidencia(group, V_kN, H_x_kN, H_y_kN, M_x_kNm, M_y_kNm, miss),
        )

        forces.append(PileForce(
            pile_name=p.name or f"P{len(forces) + 1}",
            x_m=p.x_m, y_m=p.y_m, N_kN=N_i,
            H_x_kN=H_xi, H_y_kN=H_yi,
            axial_utilization=ax_util,
            lateral_utilization=lat_util,
            in_compression=N_i >= 0,
            tension_utilization=tens_util,
            status=pile_status,
            missing_inputs=miss,
        ))
        if N_i > N_max_c:
            N_max_c = N_i
        if N_i < N_min_c:
            N_min_c = N_i
        if pile_gov is not None and pile_gov > worst_util:
            worst_util = pile_gov
            worst_pile = p.name

    N_max_tension = -N_min_c if N_min_c < 0 else 0.0

    def _group_util(vals: list[Optional[float]]) -> Optional[float]:
        # Si CUALQUIER pilote quedó sin evaluar en esta dirección, la dirección de
        # grupo NO está evaluada — no se toma el máximo de los que sí (ocultaría
        # el hueco).
        if any(v is None for v in vals):
            return None
        return max(vals) if vals else 0.0

    group_ax_util = _group_util([f.axial_utilization for f in forces])
    group_tens_util = _group_util([f.tension_utilization for f in forces])
    group_lat_util = _group_util([f.lateral_utilization for f in forces])

    missing = sorted({m for f in forces for m in f.missing_inputs})
    computed_group = [u for u in (group_ax_util, group_tens_util, group_lat_util)
                      if u is not None]
    governing = max(computed_group) if computed_group else None
    status = resolve_status(
        governing,
        missing_inputs=missing,
        **_evidencia(group, V_kN, H_x_kN, H_y_kN, M_x_kNm, M_y_kNm, missing),
    )
    all_ok = status == CalculationStatus.CALCULADO_CUMPLE

    # governing_pile: el de peor utilización computada; si ninguno se pudo evaluar,
    # el primero al que le falta un dato (es el que hay que mirar).
    if not worst_pile:
        for f in forces:
            if f.missing_inputs:
                worst_pile = f.pile_name
                break

    return PileGroupResult(
        forces=forces,
        N_max_compression=N_max_c,
        N_max_tension=N_max_tension,
        H_max_per_pile=H_max,
        axial_efficiency=E_axial,
        lateral_efficiency=E_lat,
        group_axial_utilization=group_ax_util,
        group_tension_utilization=group_tens_util,
        group_lateral_utilization=group_lat_util,
        governing_pile=worst_pile,
        all_ok=all_ok,
        status=status,
        missing_inputs=missing,
    )


__all__ = [
    "PileInGroup",
    "PileGroup",
    "PileForce",
    "PileGroupResult",
    "converse_labarre_efficiency",
    "mokwa_duncan_lateral_efficiency",
    "rectangular_group",
    "distribute_loads_rigid_cap",
]
