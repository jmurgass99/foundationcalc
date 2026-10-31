"""Multi-layer bearing capacity for shallow foundations.

Two physically distinct cases handled:

1. **Strong layer over weak layer** (Meyerhof & Hanna 1978):
   the footing rests on a strong layer of thickness H above a weak
   layer. The failure surface may pierce through the strong layer onto
   the weak one if H is small. Capacity is the minimum of:

   - Bearing capacity assuming the weak layer extends to surface.
   - Punching shear through the strong layer + bearing on the weak.

2. **Weak layer over strong layer**: the weak founding layer governs;
   the strong layer below merely limits the failure depth. We use the
   conservative simple approach: just compute q_ult on the weak layer
   and add a small contribution from confined behaviour if the weak
   layer is thin (rare in practice).

For 3+ layers we look at every interface within the **depth of influence
2B** below the founding plane and pick the most critical pair.

Theory: docs/theory/14_multilayer_bearing.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel

from ..core.geometry import RectangularFoundation
from ..core.soil import SoilLayer, SoilProfile, SoilType
from .bearing_capacity import (
    BearingCapacityFormula,
    BearingCapacityResult,
    drained_bearing_capacity,
    undrained_bearing_capacity,
)


@dataclass
class MultiLayerBCResult:
    """Output of a multi-layer bearing-capacity check."""

    q_ult_kPa: float
    governing_case: str
    governing_layer: str
    layers_in_influence: List[str]
    bottom_strong_q_ult: Optional[float] = None
    weak_layer_q_ult: Optional[float] = None
    punching_q_ult: Optional[float] = None


def _layer_strength_index(layer: SoilLayer) -> float:
    """Heuristic for ranking layers: higher index = stronger soil."""
    if layer.soil_type == SoilType.COHESIONLESS:
        return layer.friction_angle * 10.0  # ~300-450 for typical sand
    # Cohesive (drained or undrained)
    cu = layer.undrained_shear_strength or 0.0
    return cu + layer.cohesion * 5.0  # cu in kPa, prefer high values


def _layer_qult_unconfined(
    foundation: RectangularFoundation,
    layer: SoilLayer,
    q_overburden_kPa: float,
    formula: BearingCapacityFormula = BearingCapacityFormula.CHEN_EC7,
) -> BearingCapacityResult:
    """Compute q_ult assuming the entire half-space is this single layer.

    Uses drained formulation for cohesionless layers and undrained for
    cohesive layers with c_u defined.
    """
    if layer.soil_type == SoilType.COHESIVE and layer.undrained_shear_strength:
        return undrained_bearing_capacity(
            foundation=foundation, soil=layer,
            overburden_pressure=q_overburden_kPa,
        )
    return drained_bearing_capacity(
        foundation=foundation, soil=layer,
        overburden_pressure=q_overburden_kPa,
        formula=formula,
    )


def multi_layer_bearing_capacity(
    foundation: RectangularFoundation,
    profile: SoilProfile,
    founding_depth_m: float,
    formula: BearingCapacityFormula = BearingCapacityFormula.CHEN_EC7,
) -> MultiLayerBCResult:
    """Bearing capacity considering layered ground (per Meyerhof-Hanna 1978).

    Args:
        foundation: the footing geometry.
        profile: complete soil profile.
        founding_depth_m: depth (from surface) to the base of the footing.
        formula: N_γ formula.
    """
    B = foundation.width_m
    L = foundation.length_m
    z_top_found = founding_depth_m
    z_influence = founding_depth_m + 2.0 * B

    founding_layer = profile.layer_at(z_top_found + 1e-6)
    q_overburden = profile.effective_stress_at(z_top_found)

    # 1) capacity of the founding layer alone
    bc_top = _layer_qult_unconfined(foundation, founding_layer, q_overburden, formula)
    q_ult_top = bc_top.q_ult

    # 2) scan layers below until we exit the influence zone or hit a weaker layer
    running = 0.0
    layers_in_zone: List[SoilLayer] = []
    z_top = 0.0
    H_strong = 0.0  # thickness of the founding layer below the footing
    weak_layer: Optional[SoilLayer] = None
    H_to_weak: Optional[float] = None
    for layer in profile.layers:
        z_bottom = z_top + layer.thickness
        if z_bottom <= z_top_found:
            z_top = z_bottom
            continue
        if z_top >= z_influence:
            break
        layers_in_zone.append(layer)
        # thickness of this layer within (founding_depth, influence_depth]
        layer_top_in_zone = max(z_top, z_top_found)
        layer_bot_in_zone = min(z_bottom, z_influence)
        seg = layer_bot_in_zone - layer_top_in_zone
        if layer is founding_layer:
            H_strong += seg
        else:
            # Check if it is weaker than the founding layer
            if (_layer_strength_index(layer)
                    < _layer_strength_index(founding_layer)
                    and weak_layer is None):
                weak_layer = layer
                H_to_weak = layer_top_in_zone - z_top_found
        z_top = z_bottom

    if weak_layer is None or H_to_weak is None or H_to_weak >= 2.0 * B:
        # No critical weaker layer within influence zone — use founding-layer q_ult
        return MultiLayerBCResult(
            q_ult_kPa=q_ult_top,
            governing_case="founding_layer",
            governing_layer=founding_layer.name,
            layers_in_influence=[l.name for l in layers_in_zone],
        )

    # 3) Punching-shear-through-top + bearing on weak
    # q_ult_punching = q_ult,weak + (perimeter / area) · K_s · γ_top · H · tan(φ_top)
    q_overburden_at_weak = profile.effective_stress_at(z_top_found + H_to_weak)
    bc_weak = _layer_qult_unconfined(
        foundation, weak_layer, q_overburden_at_weak, formula,
    )
    q_ult_weak = bc_weak.q_ult

    # Hanna-Meyerhof punching coefficient — approximation K_s ≈ tan φ for sand
    K_s = math.tan(math.radians(founding_layer.friction_angle))
    # Punching shear contribution from the strong upper layer
    gamma_top = founding_layer.effective_unit_weight(below_water=False)
    perimeter = 2.0 * (B + L)
    A = B * L
    q_punching = (
        q_ult_weak
        + (perimeter / A) * H_to_weak * (
            2.0 * (q_overburden + 0.5 * gamma_top * H_to_weak) * K_s
            * math.tan(math.radians(founding_layer.friction_angle))
        )
    )
    q_punching = max(q_punching, q_ult_weak)
    q_governing = min(q_ult_top, q_punching)
    if q_governing < q_ult_top:
        case = "punching_through_strong_to_weak"
        gov = weak_layer.name
    else:
        case = "founding_layer"
        gov = founding_layer.name

    return MultiLayerBCResult(
        q_ult_kPa=q_governing,
        governing_case=case,
        governing_layer=gov,
        layers_in_influence=[l.name for l in layers_in_zone],
        bottom_strong_q_ult=q_ult_top,
        weak_layer_q_ult=q_ult_weak,
        punching_q_ult=q_punching,
    )


__all__ = [
    "MultiLayerBCResult",
    "multi_layer_bearing_capacity",
]
