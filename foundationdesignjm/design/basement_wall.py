"""Design of basement (subterranean) walls under at-rest earth pressure.

A basement wall does **not** move enough to mobilise the active state —
it is restrained at the top by the floor slab and at the base by the
foundation slab. So the lateral pressure is the **at-rest** pressure
`K_0 = 1 − sin φ'` (Jaky).

The module supports three static schemes (`SupportConfig`):
- CANTILEVER          — top free, base fixed (construction phase before
                        the slab is poured).
- PROPPED_CANTILEVER  — top pinned, base fixed (typical service case).
- PINNED_PINNED       — top and base pinned (envelope; used together
                        with PROPPED_CANTILEVER per the lecture slides).

Two pressure distributions are available (`PressureDiagram`):
- TRIANGULAR  — σ_h(z) = K_0·(γ·z + q) where z is depth from top.
- RECTANGULAR — σ_h = 0.67·K_0·(γ·H + q), uniform.

Three load combinations are run automatically:
1. Construction: lateral pressure + N_min (≈ 0 before the upper
   structure is built).
2. Service:      lateral pressure + N_max.
3. No-soil:      no lateral pressure + N_max (e.g. future excavation
   around the basement).

The result envelopes M_outer (towards the soil — outer-face rebar) and
M_inner (towards the basement — inner-face rebar) are returned per
metre run.

Theory: docs/theory/09_basement_walls.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from pydantic import BaseModel, Field


class SupportConfig(str, Enum):
    CANTILEVER = "cantilever"
    PROPPED_CANTILEVER = "propped_cantilever"
    PINNED_PINNED = "pinned_pinned"


class PressureDiagram(str, Enum):
    TRIANGULAR = "triangular"
    RECTANGULAR = "rectangular"


# ---------------------------------------------------------------------------
# Geometry & loading
# ---------------------------------------------------------------------------

class BasementWallGeometry(BaseModel):
    height: float = Field(..., gt=1.0, description="Total wall height H (m)")
    thickness: float = Field(..., gt=0.15, description="Wall thickness (m)")
    eccentricity_top: float = Field(0.0, description="Eccentricity e_1 of N_max at the top of wall (m, +towards soil)")
    eccentricity_base: float = Field(0.0, description="Eccentricity e_2 of ΣN at the base of wall (m)")


class BasementWallLoading(BaseModel):
    phi_deg: float = Field(..., ge=15, le=45, description="Backfill effective friction angle (deg)")
    gamma_soil: float = Field(..., gt=10, description="Backfill unit weight (kN/m³)")
    surcharge_q: float = Field(0.0, ge=0, description="Surcharge on the backfill (kN/m²)")
    water_height: float = Field(0.0, ge=0, description="Water-table height above the base of the wall (m)")
    N_min_kN_per_m: float = Field(0.0, description="Minimum axial load at top of wall (construction) (kN/m run)")
    N_max_kN_per_m: float = Field(..., description="Maximum axial load at top of wall (service) (kN/m run)")
    OCR: float = Field(1.0, ge=1.0, description="Over-consolidation ratio for K_0 (Mayne-Kulhawy)")

    @property
    def K0(self) -> float:
        sin_phi = math.sin(math.radians(self.phi_deg))
        return (1.0 - sin_phi) * (self.OCR ** sin_phi)


# ---------------------------------------------------------------------------
# Internal: pressure → forces
# ---------------------------------------------------------------------------

def _q0_triangular(load: BasementWallLoading, H: float) -> Tuple[float, float]:
    """Returns (q_top, q_base) of the at-rest triangular pressure diagram (kN/m²).

    Soil triangle: K_0·γ·z from top.
    Surcharge:     K_0·q (uniform, added to both).
    Water:         γ_w·(z − H_dry) over the saturated portion (handled
                   separately as a triangular block in the bottom).
    """
    K0 = load.K0
    q_top = K0 * load.surcharge_q
    q_base = K0 * (load.gamma_soil * H + load.surcharge_q)
    if load.water_height > 0:
        gamma_w = 9.81
        q_base += gamma_w * load.water_height
    return q_top, q_base


def _q_rectangular(load: BasementWallLoading, H: float) -> float:
    """Returns the uniform pressure for the rectangular approach (kN/m²)."""
    K0 = load.K0
    q = 0.67 * K0 * (load.gamma_soil * H + load.surcharge_q)
    if load.water_height > 0:
        q += 0.67 * 9.81 * load.water_height
    return q


# ---------------------------------------------------------------------------
# Closed-form structural responses (per metre run)
# ---------------------------------------------------------------------------

@dataclass
class WallBendingDiagram:
    """Discrete bending and shear diagrams along the wall.

    z is measured from the top (z = 0 at top, z = H at base).
    Positive M produces tension on the **inner** face (towards basement).
    Negative M produces tension on the **outer** face (towards soil).
    """

    z: List[float]
    M: List[float]
    V: List[float]
    reaction_top: float
    reaction_base: float
    M_max_positive: float
    z_of_M_max_positive: float
    M_max_negative: float
    z_of_M_max_negative: float


def _solve_triangular_load(
    H: float, q_top: float, q_base: float, support: SupportConfig,
    n_points: int = 21,
) -> WallBendingDiagram:
    """Bending diagram for a trapezoidal load profile q(z) = q_top + (q_base − q_top)·z/H."""
    # Decompose into a uniform `q_top` plus a triangular `(q_base − q_top)·z/H`.
    q_uniform = q_top
    q_tri_peak = q_base - q_top  # peak at the base

    # Reactions (closed-form):
    # Uniform load over [0, H], support config:
    if support == SupportConfig.CANTILEVER:
        # All load taken at the base
        T_top_u = 0.0
        T_base_u = q_uniform * H
        T_top_t = 0.0
        T_base_t = q_tri_peak * H / 2.0
    elif support == SupportConfig.PROPPED_CANTILEVER:
        # Uniform: T_top = 3wH/8, M_base = -wH^2/8
        T_top_u = 3.0 * q_uniform * H / 8.0
        T_base_u = q_uniform * H - T_top_u
        # Triangular (load increases towards base): T_top = qH/10, M_base = -qH^2/15
        T_top_t = q_tri_peak * H / 10.0
        T_base_t = q_tri_peak * H / 2.0 - T_top_t
    elif support == SupportConfig.PINNED_PINNED:
        # Uniform: T_top = T_base = wH/2
        T_top_u = q_uniform * H / 2.0
        T_base_u = q_uniform * H / 2.0
        # Triangular: T_top = qH/6, T_base = qH/3
        T_top_t = q_tri_peak * H / 6.0
        T_base_t = q_tri_peak * H / 3.0
    else:
        raise ValueError(f"Unknown support config {support}")

    T_top = T_top_u + T_top_t
    T_base = T_base_u + T_base_t

    # Bending at z (taken from top):
    # M(z) = T_top·z − ∫_0^z q(s)·(z − s) ds
    z_grid = [H * i / (n_points - 1) for i in range(n_points)]
    M_list = []
    V_list = []
    for z in z_grid:
        # Integral of uniform: ∫q_top·(z-s)ds = q_top·z²/2
        M_u = T_top * z - q_uniform * z ** 2 / 2.0
        # Integral of triangular: ∫(q_tri_peak·s/H)·(z-s)ds = q_tri_peak/H · (z·z²/2 − z³/3) = q_tri_peak·z³/(6H)
        M_t = -q_tri_peak * z ** 3 / (6.0 * H)
        M = M_u + M_t + T_top_t * z  # already in T_top
        # Recompose cleanly:
        M = T_top * z - q_uniform * z ** 2 / 2.0 - q_tri_peak * z ** 3 / (6.0 * H)
        # Shear: V(z) = T_top − ∫_0^z q(s) ds
        V = T_top - q_uniform * z - q_tri_peak * z ** 2 / (2.0 * H)
        M_list.append(M)
        V_list.append(V)

    # Add the fixed-end moment at the base for cantilever and propped cantilever
    # (compatibility with the closed-form table)
    if support in (SupportConfig.CANTILEVER, SupportConfig.PROPPED_CANTILEVER):
        # Base moment from external load is naturally M(H). For the cantilever
        # case M(H) includes the entire fixed-end action; for the propped
        # cantilever it is the residual hogging moment.
        pass  # already computed

    M_pos = max(M_list)
    M_neg = min(M_list)
    z_pos = z_grid[M_list.index(M_pos)]
    z_neg = z_grid[M_list.index(M_neg)]

    return WallBendingDiagram(
        z=z_grid, M=M_list, V=V_list,
        reaction_top=T_top, reaction_base=T_base,
        M_max_positive=M_pos, z_of_M_max_positive=z_pos,
        M_max_negative=M_neg, z_of_M_max_negative=z_neg,
    )


# ---------------------------------------------------------------------------
# Public solver
# ---------------------------------------------------------------------------

class BasementWallResult(BaseModel):
    """Envelope of M and V across the 3 design combinations."""

    K0: float
    support: SupportConfig
    pressure: PressureDiagram

    # Pressure diagram values
    q_top_kPa: float
    q_base_kPa: float

    # Reactions per metre run
    R_top_kN_per_m: float
    R_base_kN_per_m: float

    # Envelopes (per metre run)
    M_outer_max_kNm: float = Field(description="Worst hogging moment (tension on outer/soil face)")
    z_of_M_outer_max_m: float
    M_inner_max_kNm: float = Field(description="Worst sagging moment (tension on inner/basement face)")
    z_of_M_inner_max_m: float
    V_max_kN: float

    # Combined N+M at the base (most-loaded section)
    N_max_kN_per_m: float
    second_order_M_base_kNm: float

    # Discrete diagrams for plotting / further processing
    z: List[float]
    M_envelope_outer: List[float]
    M_envelope_inner: List[float]
    V_envelope: List[float]


class BasementWallDesigner:
    """Compute the M / V envelopes per metre run for a basement wall."""

    def __init__(
        self,
        geometry: BasementWallGeometry,
        loading: BasementWallLoading,
        support: SupportConfig = SupportConfig.PROPPED_CANTILEVER,
        pressure: PressureDiagram = PressureDiagram.TRIANGULAR,
    ):
        self.geo = geometry
        self.load = loading
        self.support = support
        self.pressure = pressure

    def _pressure_endpoints(self) -> Tuple[float, float]:
        H = self.geo.height
        if self.pressure == PressureDiagram.TRIANGULAR:
            return _q0_triangular(self.load, H)
        # Rectangular: same value top and base
        q = _q_rectangular(self.load, H)
        return q, q

    def solve(self) -> BasementWallResult:
        H = self.geo.height
        q_top, q_base = self._pressure_endpoints()

        # Lateral-pressure-only diagram
        diag_pressure = _solve_triangular_load(H, q_top, q_base, self.support)

        # Diagram from axial-force eccentricity (linear)
        # M_axial(z) = M_top + (M_base_ax − M_top) · z / H
        # where M_top = e_1 · N_max,  M_base_ax = −e_2 · N_max
        N_min = self.load.N_min_kN_per_m
        N_max = self.load.N_max_kN_per_m
        e1 = self.geo.eccentricity_top
        e2 = self.geo.eccentricity_base
        z_grid = diag_pressure.z

        def _M_axial(N: float) -> List[float]:
            M_top_ax = e1 * N
            M_base_ax = -e2 * N
            return [M_top_ax + (M_base_ax - M_top_ax) * z / H for z in z_grid]

        # Combination 1: pressure + N_min
        M1 = [a + b for a, b in zip(diag_pressure.M, _M_axial(N_min))]
        # Combination 2: pressure + N_max
        M2 = [a + b for a, b in zip(diag_pressure.M, _M_axial(N_max))]
        # Combination 3: no pressure, just N_max
        M3 = _M_axial(N_max)

        # Envelope: outer (most negative) and inner (most positive)
        M_outer = [min(a, b, c) for a, b, c in zip(M1, M2, M3)]
        M_inner = [max(a, b, c) for a, b, c in zip(M1, M2, M3)]
        V_env = diag_pressure.V  # axial-only adds no shear

        M_outer_max = min(M_outer)
        M_inner_max = max(M_inner)
        z_outer = z_grid[M_outer.index(M_outer_max)]
        z_inner = z_grid[M_inner.index(M_inner_max)]
        V_peak = max(abs(v) for v in V_env)

        # 2nd-order moment at the base from N_max alone (often used to
        # quantify the contribution of the axial eccentricity)
        M_second_order_base = -e2 * N_max

        return BasementWallResult(
            K0=self.load.K0,
            support=self.support,
            pressure=self.pressure,
            q_top_kPa=q_top, q_base_kPa=q_base,
            R_top_kN_per_m=diag_pressure.reaction_top,
            R_base_kN_per_m=diag_pressure.reaction_base,
            M_outer_max_kNm=M_outer_max,
            z_of_M_outer_max_m=z_outer,
            M_inner_max_kNm=M_inner_max,
            z_of_M_inner_max_m=z_inner,
            V_max_kN=V_peak,
            N_max_kN_per_m=N_max,
            second_order_M_base_kNm=M_second_order_base,
            z=z_grid,
            M_envelope_outer=M_outer,
            M_envelope_inner=M_inner,
            V_envelope=V_env,
        )


@dataclass(frozen=True)
class BasementWallStabilityResult:
    """Resultado de estabilidad geotécnica de muro de sótano bajo empujes de Rankine o Coulomb."""
    method: str
    Ka: float
    thrust_soil_kN_per_m: float
    thrust_surcharge_kN_per_m: float
    total_active_thrust_kN_per_m: float
    overturning_moment_kNm_per_m: float
    resisting_moment_kNm_per_m: float
    driving_shear_kN_per_m: float
    resisting_friction_kN_per_m: float
    FS_sliding: float
    FS_overturning: float
    is_safe_sliding: bool
    is_safe_overturning: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "Ka": self.Ka,
            "thrust_soil_kN_per_m": self.thrust_soil_kN_per_m,
            "thrust_surcharge_kN_per_m": self.thrust_surcharge_kN_per_m,
            "total_active_thrust_kN_per_m": self.total_active_thrust_kN_per_m,
            "overturning_moment_kNm_per_m": self.overturning_moment_kNm_per_m,
            "resisting_moment_kNm_per_m": self.resisting_moment_kNm_per_m,
            "driving_shear_kN_per_m": self.driving_shear_kN_per_m,
            "resisting_friction_kN_per_m": self.resisting_friction_kN_per_m,
            "FS_sliding": self.FS_sliding,
            "FS_overturning": self.FS_overturning,
            "is_safe_sliding": self.is_safe_sliding,
            "is_safe_overturning": self.is_safe_overturning,
        }


def evaluate_wall_stability_coulomb_rankine(
    height_m: float,
    thickness_m: float,
    gamma_soil_kN_m3: float,
    phi_deg: float,
    surcharge_q_kPa: float = 0.0,
    N_axial_kN_per_m: float = 0.0,
    base_width_m: float | None = None,
    delta_deg: float = 0.0,
    method: str = "rankine",
    gamma_concrete_kN_m3: float = 25.0,
    tan_delta_base: float = 0.50,
) -> BasementWallStabilityResult:
    """Evalúa empujes laterales de Rankine o Coulomb y factores de seguridad ante deslizamiento y volcamiento."""
    method_norm = method.lower().strip()
    H = height_m
    B = base_width_m if base_width_m is not None else thickness_m

    if method_norm == "rankine":
        Ka = math.tan(math.radians(45.0 - phi_deg / 2.0)) ** 2
        eff_delta = 0.0
    elif method_norm == "coulomb":
        # Coulomb activo para muro vertical beta=90, relleno horizontal alpha=0
        phi_rad = math.radians(phi_deg)
        delta_rad = math.radians(delta_deg)
        num = math.cos(phi_rad) ** 2
        den = math.cos(delta_rad) * (1.0 + math.sqrt(math.sin(phi_rad + delta_rad) * math.sin(phi_rad) / math.cos(delta_rad))) ** 2
        Ka = num / max(den, 1e-12)
        eff_delta = delta_deg
    else:
        raise ValueError(f"Método '{method}' no soportado. Usar 'rankine' o 'coulomb'.")

    # Empujes de tierra y sobrecarga
    P_soil = 0.5 * Ka * gamma_soil_kN_m3 * (H ** 2)
    P_sur = Ka * surcharge_q_kPa * H
    P_total = P_soil + P_sur

    cos_d = math.cos(math.radians(eff_delta))
    sin_d = math.sin(math.radians(eff_delta))

    P_h = P_total * cos_d
    P_v = P_total * sin_d

    # Momentos volcadores respecto a la base/puntera
    M_ov = (P_soil * cos_d * (H / 3.0)) + (P_sur * cos_d * (H / 2.0))

    # Cargas estabilizadoras
    W_wall = gamma_concrete_kN_m3 * thickness_m * H
    V_total = W_wall + N_axial_kN_per_m + P_v

    # Brazo estabilizador
    x_w = B / 2.0
    M_res = (W_wall * x_w) + (N_axial_kN_per_m * x_w) + (P_v * B)

    # Factores de seguridad
    R_friction = V_total * tan_delta_base
    FS_sl = R_friction / max(P_h, 1e-9)
    FS_ov = M_res / max(M_ov, 1e-9)

    return BasementWallStabilityResult(
        method=method_norm,
        Ka=Ka,
        thrust_soil_kN_per_m=P_soil,
        thrust_surcharge_kN_per_m=P_sur,
        total_active_thrust_kN_per_m=P_total,
        overturning_moment_kNm_per_m=M_ov,
        resisting_moment_kNm_per_m=M_res,
        driving_shear_kN_per_m=P_h,
        resisting_friction_kN_per_m=R_friction,
        FS_sliding=FS_sl,
        FS_overturning=FS_ov,
        is_safe_sliding=FS_sl >= 1.50,
        is_safe_overturning=FS_ov >= 1.50,
    )


__all__ = [
    "SupportConfig",
    "PressureDiagram",
    "BasementWallGeometry",
    "BasementWallLoading",
    "BasementWallResult",
    "BasementWallStabilityResult",
    "BasementWallDesigner",
    "evaluate_wall_stability_coulomb_rankine",
]

