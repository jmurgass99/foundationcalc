"""Diaphragm (slurry) wall design.

A diaphragm wall is a continuous RC wall built **in situ** before
excavation, using bentonite slurry to keep the trench open while
reinforcement is lowered and concrete tremied. Used for:

- Deep basements and metro stations (excavations 10–40 m).
- Cut-off walls under dams.
- Permanent retaining + structural function combined.

The wall behaves as a **propped cantilever beam** spanning between:
- The base of excavation (passive resistance at the embedded toe).
- The slab(s) / props above.

This module gives:

- **Embedment depth** required to mobilise enough passive pressure
  to balance the active thrust above (Free Earth Support method —
  classical Blum / Tschebotarioff).
- **Prop force** from horizontal equilibrium with the passive force that
  the moment equilibrium about the (upper) prop actually mobilises,
  P_p,mob = M_a / arm_p. With several prop levels the total is split in
  equal parts — a heuristic that does not satisfy moment equilibrium,
  so the bending diagram is only rigorous for a single prop.
- **Bending moment and shear** by integrating the net pressure
  (design active minus mobilised passive, triangular below formation).
- **Penetration ratio** F = M_passive / M_active computed with DESIGN
  values (φ_d of set M, γ_G/γ_Q on the active side, γ_R;e on the passive
  side); `embedment_required_m` targets F = 1.5 on top of those factors.
- Cohesion and water are NOT modelled: `check()` raises if they are given.

References: EN 1997-1 §9, EAB-86 (German DIN approach), Bowles 2001.
Theory: docs/theory/06_retaining_walls.md §6.1 (diaphragm walls).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

from ..codes.eurocode7 import DesignApproach, LimitState, get_partial_factors


class DiaphragmWallGeometry(BaseModel):
    H_excavation: float = Field(..., gt=2.0)
    embedment_m: float = Field(..., gt=0.5)
    thickness_m: float = Field(0.60, gt=0.30,
                              description="Wall thickness (m, typ. 0.60–1.20)")
    prop_levels_m: List[float] = Field(
        default_factory=list,
        description="Depths (m below top) of prop / slab supports",
    )


class DiaphragmWallLoading(BaseModel):
    phi_deg: float = Field(..., ge=20, le=45)
    gamma_kN_m3: float = Field(..., gt=10)
    c_kPa: float = Field(0.0, ge=0)
    water_table_above_excavation_m: float = Field(0.0, ge=0)
    surcharge_q: float = Field(0.0, ge=0)


@dataclass
class DiaphragmWallResult:
    P_active_kN_per_m: float
    P_passive_kN_per_m: float
    overturning_safety_factor: float
    embedment_required_m: float
    prop_forces_kN_per_m: List[float]
    M_max_kNm_per_m: float
    V_max_kN_per_m: float
    P_passive_mobilised_kN_per_m: float = 0.0
    z_of_M_max_m: float = 0.0


class DiaphragmWallDesigner:
    """Free Earth Support analysis of a single-/multi-propped diaphragm wall."""

    def __init__(
        self,
        geometry: DiaphragmWallGeometry,
        loading: DiaphragmWallLoading,
        design_approach: DesignApproach = DesignApproach.DA2,
    ):
        self.geo = geometry
        self.load = loading
        self.da = design_approach

    @staticmethod
    def _K_a(phi_deg: float) -> float:
        return math.tan(math.radians(45.0 - phi_deg / 2.0)) ** 2

    @staticmethod
    def _K_p(phi_deg: float) -> float:
        return math.tan(math.radians(45.0 + phi_deg / 2.0)) ** 2

    def _design_parameters(self) -> dict:
        pf = get_partial_factors(self.da, LimitState.GEO)
        # Design strength (set M): tan φ_d = tan φ_k / γ_φ; passive earth
        # resistance divided by γ_R;e of the approach (R2 = 1,4; R1/R3 = 1,0).
        phi_d = math.degrees(math.atan(
            math.tan(math.radians(self.load.phi_deg)) / pf.soil.gamma_phi))
        return {
            "gG": pf.actions.gamma_G_unfav,
            "gQ": pf.actions.gamma_Q_unfav,
            "gR_e": pf.resistance.gamma_Re,
            "phi_d": phi_d,
            "K_a": self._K_a(phi_d),
            "K_p": self._K_p(phi_d),
        }

    def _moments_about_prop(self, D: float, prop_z: float, dp: dict) -> Tuple[float, float, float, float]:
        """(P_a,d, M_a about the prop, P_p,d available, arm of P_p) for embedment D."""
        H = self.geo.H_excavation
        gamma = self.load.gamma_kN_m3
        q = self.load.surcharge_q
        Lt = H + D
        Pa_s = dp["gG"] * 0.5 * dp["K_a"] * gamma * Lt ** 2   # resultant at 2/3·Lt
        Pa_q = dp["gQ"] * dp["K_a"] * q * Lt                    # resultant at Lt/2
        M_a = Pa_s * (2.0 * Lt / 3.0 - prop_z) + Pa_q * (Lt / 2.0 - prop_z)
        P_p = 0.5 * dp["K_p"] * gamma * D ** 2 / dp["gR_e"]    # resultant at H + 2/3·D
        arm_p = H + 2.0 * D / 3.0 - prop_z
        return Pa_s + Pa_q, M_a, P_p, arm_p

    def check(self) -> DiaphragmWallResult:
        if self.load.c_kPa > 0 or self.load.water_table_above_excavation_m > 0:
            raise ValueError(
                "DiaphragmWallDesigner no modela cohesión ni agua: hasta la 1.1.0 "
                "aceptaba c_kPa y water_table_above_excavation_m y los ignoraba "
                "sin avisar. Úsalos a 0 o modela el empuje en otra herramienta.")
        dp = self._design_parameters()
        H = self.geo.H_excavation
        D = self.geo.embedment_m
        gamma = self.load.gamma_kN_m3
        q = self.load.surcharge_q
        K_a, K_p = dp["K_a"], dp["K_p"]
        gG, gQ = dp["gG"], dp["gQ"]
        props = sorted(self.geo.prop_levels_m) if self.geo.prop_levels_m else [0.0]
        prop_z = props[0]

        # ---- Free earth support: moments about the (upper) prop ----------
        P_a_total, M_overturning, P_p, arm_p = self._moments_about_prop(D, prop_z, dp)
        FoS = (P_p * arm_p) / max(M_overturning, 1e-9)

        # ---- Required embedment for FoS = 1,5 (bisection) ----------------
        # NOTE: the target 1.5 is applied on top of the partial factors of
        # the design approach (double safety, kept from the original module).
        target = 1.5
        D_lo, D_hi = 0.1, 5.0 * H
        for _ in range(60):
            D_try = 0.5 * (D_lo + D_hi)
            _, M_a_t, P_p_t, arm_p_t = self._moments_about_prop(D_try, prop_z, dp)
            if (P_p_t * arm_p_t) / max(M_a_t, 1e-9) >= target:
                D_hi = D_try
            else:
                D_lo = D_try
        D_req = D_hi

        # ---- Prop force from equilibrium ----------------------------------
        # DEFECTO CORREGIDO (1.1.0): antes T = P_a − P_p con TODO el pasivo
        # disponible, aunque el equilibrio de momentos sólo movilice
        # P_p,mob = M_a / brazo_p (= P_p / FoS). Con FoS > 1 subestimaba el
        # puntal (podía salir negativo). Ahora T = P_a − P_p,mob.
        P_p_mob = M_overturning / max(arm_p, 1e-9)
        F_prop_total = P_a_total - P_p_mob
        n_props = len(props)
        prop_forces = [F_prop_total / n_props] * n_props

        # ---- Bending moment and shear by integrating the net pressure ----
        # DEFECTO CORREGIDO (1.1.0): antes M_max = T²/(2·q_max), fórmula de
        # carga UNIFORME aplicada con la ordenada máxima del triángulo activo,
        # que con un puntal en cabeza daba momentos decenas de veces menores
        # que el equilibrio. Ahora M(z) = Σ T_i·(z − z_i) − ∫(z − ζ)·w(ζ)dζ
        # con w = presión activa de cálculo − pasivo movilizado (triangular
        # bajo el fondo de excavación).
        Lt = H + D
        n = 4001
        z = np.linspace(0.0, Lt, n)
        w = gG * K_a * gamma * z + gQ * K_a * q
        if D > 0:
            p_peak = 2.0 * P_p_mob / D           # triangle with resultant P_p,mob
            w = w - np.where(z > H, p_peak * (z - H) / D, 0.0)
        dz = z[1] - z[0]
        W = np.concatenate(([0.0], np.cumsum(0.5 * (w[1:] + w[:-1]) * dz)))
        Mw = np.concatenate(([0.0], np.cumsum(0.5 * (W[1:] + W[:-1]) * dz)))
        V = -W
        M = -Mw
        for z_i, T_i in zip(props, prop_forces):
            V = V + np.where(z >= z_i, T_i, 0.0)
            M = M + np.where(z >= z_i, T_i * (z - z_i), 0.0)
        M_max = float(np.max(np.abs(M)))
        V_max = float(np.max(np.abs(V)))

        return DiaphragmWallResult(
            P_active_kN_per_m=P_a_total,
            P_passive_kN_per_m=P_p,
            overturning_safety_factor=FoS,
            embedment_required_m=D_req,
            prop_forces_kN_per_m=prop_forces,
            M_max_kNm_per_m=M_max,
            V_max_kN_per_m=V_max,
            P_passive_mobilised_kN_per_m=P_p_mob,
            z_of_M_max_m=float(z[int(np.argmax(np.abs(M)))]),
        )


__all__ = [
    "DiaphragmWallGeometry",
    "DiaphragmWallLoading",
    "DiaphragmWallResult",
    "DiaphragmWallDesigner",
]
