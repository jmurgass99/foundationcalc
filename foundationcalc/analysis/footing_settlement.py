"""End-to-end settlement of a rectangular footing on a layered profile.

Combines:
- `stress.boussinesq_rect_centre` to compute Δσ_z(z) under the centre.
- Elastic settlement (Schmertmann 1970 / Janbu et al. 1956) for
  cohesionless layers.
- Terzaghi 1-D consolidation for cohesive layers (`consolidation.py`).

The footing is discretised into a stack of *settlement sub-layers* of
configurable thickness, each evaluated at its mid-depth. The total
settlement is the sum of:
- s_imm    immediate (elastic) settlement of cohesionless layers.
- s_c      primary consolidation settlement of cohesive layers.
- s_imm,c  immediate (undrained) settlement of clays — Mayne & Poulos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.geometry import RectangularFoundation
from ..core.soil import SoilLayer, SoilProfile, SoilType
from .consolidation import (
    ClayLayer,
    elastic_settlement_rectangle,
    settlement_consolidation,
    time_to_consolidation,
)
from .stress import boussinesq_rect_centre


@dataclass
class SubLayerContribution:
    """Settlement contribution of one analysis sub-layer."""

    z_top: float
    z_bot: float
    layer_name: str
    soil_type: SoilType
    sigma_0_kPa: float
    delta_sigma_kPa: float
    s_immediate_mm: float = 0.0
    s_consolidation_mm: float = 0.0
    t_90_years: Optional[float] = None

    @property
    def s_total_mm(self) -> float:
        return self.s_immediate_mm + self.s_consolidation_mm


class FootingSettlementResult(BaseModel):
    """Aggregated settlement result."""

    s_immediate_mm: float
    s_consolidation_mm: float
    s_total_mm: float
    t_90_years_max: Optional[float] = None
    sublayers: List[dict]   # serialised SubLayerContribution


def total_footing_settlement(
    foundation: RectangularFoundation,
    profile: SoilProfile,
    founding_depth_m: float,
    q_applied_kPa: float,
    influence_depth_factor: float = 2.0,
    sub_layer_thickness_m: float = 0.5,
    elastic_C_c_for_sand: bool = False,
    consolidation_for_clay: bool = True,
) -> FootingSettlementResult:
    """Compute the total settlement under the centre of the footing.

    Algorithm:
    1. Determine the depth of influence H_inf = `influence_depth_factor` · B
       below the footing.
    2. Discretise the soil between (D, D + H_inf) into thin sub-layers.
    3. For each sub-layer i:
        - z_mid relative to footing base.
        - Δσ_z,i = q_net · I_z (Boussinesq, rectangular flexible).
        - σ_0,i = effective overburden at z_mid (before construction).
        - If sand (E available): s_imm,i = Δσ_z · Δz / E.
        - If clay (C_c, e_0, σ'_p available): primary consolidation
                  formula from `consolidation.settlement_consolidation`.
    4. Sum contributions.

    Args:
        q_applied_kPa: total contact pressure at the base of the footing
                       INCLUDING gravity loads. Convention: positive
                       downwards.
        influence_depth_factor: H_inf = factor · B. Default 2.
        sub_layer_thickness_m: integration step.
    """
    B = foundation.width_m
    L = foundation.length_m
    H_inf = influence_depth_factor * B

    # Net pressure = applied − existing overburden
    q_overburden_at_base = profile.effective_stress_at(founding_depth_m)
    q_net = max(q_applied_kPa - q_overburden_at_base, 0.0)

    # Build sub-layers
    sublayers: List[SubLayerContribution] = []
    z = 0.0  # local depth below the footing base
    while z < H_inf:
        z_top = z
        z_bot = min(z + sub_layer_thickness_m, H_inf)
        z_mid_local = 0.5 * (z_top + z_bot)
        z_mid_global = founding_depth_m + z_mid_local
        thickness = z_bot - z_top
        layer = profile.layer_at(z_mid_global)

        # Stress increment at mid-depth from Boussinesq rectangle
        delta_sigma = boussinesq_rect_centre(q_net, B, L, z_mid_local)
        sigma_0 = profile.effective_stress_at(z_mid_global)

        sl = SubLayerContribution(
            z_top=z_mid_global - thickness / 2.0,
            z_bot=z_mid_global + thickness / 2.0,
            layer_name=layer.name,
            soil_type=layer.soil_type,
            sigma_0_kPa=sigma_0,
            delta_sigma_kPa=delta_sigma,
        )

        # Immediate settlement for cohesionless sub-layer
        if layer.soil_type == SoilType.COHESIONLESS and layer.youngs_modulus:
            E_kPa = layer.youngs_modulus * 1000.0  # MPa → kPa
            sl.s_immediate_mm = (delta_sigma * thickness / E_kPa) * 1000.0
        elif layer.soil_type == SoilType.COHESIONLESS:
            # Fallback: use elastic_settlement_rectangle formula on the slice
            E_kPa = 30e3  # generic default
            sl.s_immediate_mm = (delta_sigma * thickness / E_kPa) * 1000.0

        # Consolidation for cohesive sub-layer
        if (layer.soil_type == SoilType.COHESIVE
                and consolidation_for_clay
                and sigma_0 > 0):
            # We need C_c, e0, sigma_p_kPa, c_v from the layer if available.
            # We synthesise from rough rules of thumb if absent.
            e0 = 0.8  # default
            C_c = 0.30
            C_r = 0.05
            sigma_p = sigma_0 * layer.OCR
            c_v = 2.0  # m²/year typical
            clay = ClayLayer(
                thickness_m=thickness, e0=e0,
                C_c=C_c, C_r=C_r, OCR=layer.OCR,
                sigma_p_kPa=max(sigma_p, sigma_0 + 1.0),
                c_v_m2_per_year=c_v,
                two_way_drainage=True,
            )
            s_c = settlement_consolidation(
                clay, sigma_0_kPa=sigma_0, delta_sigma_kPa=delta_sigma,
            )
            sl.s_consolidation_mm = s_c * 1000.0
            sl.t_90_years = time_to_consolidation(clay, U_target=0.90)

        sublayers.append(sl)
        z = z_bot

    s_imm = sum(sl.s_immediate_mm for sl in sublayers)
    s_con = sum(sl.s_consolidation_mm for sl in sublayers)
    t90_max = max((sl.t_90_years for sl in sublayers
                  if sl.t_90_years is not None), default=None)

    return FootingSettlementResult(
        s_immediate_mm=s_imm,
        s_consolidation_mm=s_con,
        s_total_mm=s_imm + s_con,
        t_90_years_max=t90_max,
        sublayers=[
            dict(
                z_top=sl.z_top, z_bot=sl.z_bot, layer_name=sl.layer_name,
                soil_type=sl.soil_type.value if hasattr(sl.soil_type, "value") else str(sl.soil_type),
                sigma_0_kPa=sl.sigma_0_kPa, delta_sigma_kPa=sl.delta_sigma_kPa,
                s_immediate_mm=sl.s_immediate_mm, s_consolidation_mm=sl.s_consolidation_mm,
                t_90_years=sl.t_90_years,
            )
            for sl in sublayers
        ],
    )


__all__ = [
    "SubLayerContribution",
    "FootingSettlementResult",
    "total_footing_settlement",
]
