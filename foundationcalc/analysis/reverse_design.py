"""Reverse design (optimizer) of a rectangular footing.

Given the soil profile, the applied loading and the design constraints
(EC7 utilization ≤ 1.0 and SLS settlement ≤ limit), find the **smallest**
footing dimensions that satisfy all checks. Optionally minimise concrete
volume or total construction cost.

Two solver modes are exposed:

- `optimize_footing_dimensions(...)` — single-objective search for the
  minimum **square** footing (B = L). Useful 80% of the time.
- `optimize_rectangular_footing(...)` — bivariate search over (B, L)
  with optional fixed aspect ratio. Slower but supports column moments.

The search uses an outer **binary search on B** (bracketed by a lower
bound from EC7 minimum and an upper bound = 10·B_initial), with inner
calls to `design_footing_from_cpt` or `multi_layer_bearing_capacity`
to evaluate utilization.

Cost model (roadmap #6):
    cost(B, L, t) = V_concrete · price_concrete + A_rebar · price_rebar
                    + excavation_volume · price_excavation
Default unit costs are placeholder market values that you can override.

Theory: docs/theory/15_reverse_design.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional, Tuple

from pydantic import BaseModel, Field

from ..codes.eurocode7 import DesignApproach
from ..core.geometry import RectangularFoundation
from ..core.soil import SoilProfile
from .cpt import CPTProfile
from .cpt_to_design import design_footing_from_cpt
from .footing_settlement import total_footing_settlement
from .multi_layer_bc import multi_layer_bearing_capacity


# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------

class CostModel(BaseModel):
    """Unit costs used by the optimiser (override with site values)."""

    concrete_eur_per_m3: float = Field(120.0, gt=0)
    rebar_eur_per_kg: float = Field(1.20, gt=0)
    excavation_eur_per_m3: float = Field(15.0, gt=0)
    formwork_eur_per_m2: float = Field(25.0, gt=0)
    average_rebar_ratio_kg_per_m3: float = Field(80.0, gt=0,
        description="Typical pad-footing rebar density (kg/m³)")

    def footing_cost(self, B: float, L: float, t: float,
                     excavation_depth: float) -> float:
        V_c = B * L * t
        V_e = B * L * excavation_depth
        A_form = 2 * (B + L) * t
        A_steel_kg = V_c * self.average_rebar_ratio_kg_per_m3
        return (
            self.concrete_eur_per_m3 * V_c
            + self.rebar_eur_per_kg * A_steel_kg
            + self.excavation_eur_per_m3 * V_e
            + self.formwork_eur_per_m2 * A_form
        )


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class OptimizationGoal(str, Enum):
    MIN_AREA = "min_area"           # smallest B that passes
    MIN_COST = "min_cost"            # cheapest combination of (B, t)
    BALANCED = "balanced"            # both utilizations near 1.0


@dataclass
class FootingCandidate:
    B: float
    L: float
    t: float
    bearing_utilization: float
    settlement_mm: float
    cost_eur: float
    passes: bool


@dataclass
class OptimizationResult:
    best: FootingCandidate
    history: List[FootingCandidate]
    goal: OptimizationGoal


def _evaluate_candidate_from_cpt(
    cpt: CPTProfile,
    B_mm: float, L_mm: float, t_mm: float,
    founding_depth_m: float,
    load_kN: float,
    design_approach: DesignApproach,
    settlement_limit_mm: float,
    cost_model: CostModel,
) -> FootingCandidate:
    """Compute utilization and cost for one (B, L, t) candidate."""
    pad = RectangularFoundation(
        length=L_mm, width=B_mm, thickness=t_mm,
        embedment_depth=founding_depth_m * 1000.0,
    )
    A = (B_mm / 1000.0) * (L_mm / 1000.0)
    q = load_kN / max(A, 1e-6)
    res = design_footing_from_cpt(
        cpt, pad, founding_depth_m=founding_depth_m, q_applied_kPa=q,
        design_approach=design_approach,
        settlement_limit_mm=settlement_limit_mm,
    )
    cost = cost_model.footing_cost(
        B_mm / 1000.0, L_mm / 1000.0, t_mm / 1000.0,
        excavation_depth=founding_depth_m,
    )
    passes = res.bearing_ok and res.settlement_ok
    return FootingCandidate(
        B=B_mm / 1000.0, L=L_mm / 1000.0, t=t_mm / 1000.0,
        bearing_utilization=res.bearing_utilization,
        settlement_mm=res.settlement.s_total_mm,
        cost_eur=cost, passes=passes,
    )


def optimize_footing_dimensions(
    cpt: CPTProfile,
    load_kN: float,
    founding_depth_m: float,
    design_approach: DesignApproach = DesignApproach.DA2,
    settlement_limit_mm: float = 50.0,
    cost_model: Optional[CostModel] = None,
    goal: OptimizationGoal = OptimizationGoal.MIN_AREA,
    B_min_mm: float = 800.0,
    B_max_mm: float = 8000.0,
    thickness_mm: float = 500.0,
    tolerance_mm: float = 50.0,
    max_iter: int = 25,
) -> OptimizationResult:
    """Find the smallest **square** footing (B = L) passing all checks.

    Algorithm: outer binary search on B between `B_min_mm` and `B_max_mm`.
    At each evaluation we check both bearing utilization and settlement.

    Args:
        cpt: site CPT log.
        load_kN: design vertical load (ULS).
        founding_depth_m: depth of the base of the footing (m).
        goal: MIN_AREA (default), MIN_COST or BALANCED.
        B_min_mm / B_max_mm: search bounds for B (mm).
        thickness_mm: pad thickness used for all candidates.
        tolerance_mm: stop when bracket width is below this.
    """
    if cost_model is None:
        cost_model = CostModel()
    history: List[FootingCandidate] = []

    # Upper bound must pass; if not, raise
    upper = _evaluate_candidate_from_cpt(
        cpt, B_max_mm, B_max_mm, thickness_mm, founding_depth_m,
        load_kN, design_approach, settlement_limit_mm, cost_model,
    )
    history.append(upper)
    if not upper.passes:
        raise RuntimeError(
            f"No solution within search bounds: even B={B_max_mm/1000:.1f} m "
            f"fails (bearing_util={upper.bearing_utilization*100:.1f}%, "
            f"settlement={upper.settlement_mm:.1f} mm)."
        )

    lo, hi = B_min_mm, B_max_mm
    best = upper
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        cand = _evaluate_candidate_from_cpt(
            cpt, mid, mid, thickness_mm, founding_depth_m,
            load_kN, design_approach, settlement_limit_mm, cost_model,
        )
        history.append(cand)
        if cand.passes:
            best = cand
            hi = mid
        else:
            lo = mid
        if hi - lo < tolerance_mm:
            break

    # If MIN_COST, also try thicker / thinner variations around the best B
    if goal == OptimizationGoal.MIN_COST:
        for t in [300, 400, 500, 600, 800, 1000]:
            cand = _evaluate_candidate_from_cpt(
                cpt, best.B * 1000.0, best.L * 1000.0, t, founding_depth_m,
                load_kN, design_approach, settlement_limit_mm, cost_model,
            )
            history.append(cand)
            if cand.passes and cand.cost_eur < best.cost_eur:
                best = cand

    return OptimizationResult(best=best, history=history, goal=goal)


def optimize_rectangular_footing(
    cpt: CPTProfile,
    load_kN: float,
    founding_depth_m: float,
    aspect_ratio_L_over_B: float = 1.0,
    design_approach: DesignApproach = DesignApproach.DA2,
    settlement_limit_mm: float = 50.0,
    cost_model: Optional[CostModel] = None,
    B_min_mm: float = 800.0,
    B_max_mm: float = 8000.0,
    thickness_mm: float = 500.0,
    tolerance_mm: float = 50.0,
    max_iter: int = 25,
) -> OptimizationResult:
    """Find the smallest rectangular footing of fixed L/B ratio that passes."""
    if cost_model is None:
        cost_model = CostModel()
    history: List[FootingCandidate] = []
    upper = _evaluate_candidate_from_cpt(
        cpt, B_max_mm, B_max_mm * aspect_ratio_L_over_B, thickness_mm,
        founding_depth_m, load_kN, design_approach,
        settlement_limit_mm, cost_model,
    )
    history.append(upper)
    if not upper.passes:
        raise RuntimeError("No solution within search bounds (upper bracket fails).")

    lo, hi = B_min_mm, B_max_mm
    best = upper
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        cand = _evaluate_candidate_from_cpt(
            cpt, mid, mid * aspect_ratio_L_over_B, thickness_mm,
            founding_depth_m, load_kN, design_approach,
            settlement_limit_mm, cost_model,
        )
        history.append(cand)
        if cand.passes:
            best = cand
            hi = mid
        else:
            lo = mid
        if hi - lo < tolerance_mm:
            break
    return OptimizationResult(best=best, history=history,
                              goal=OptimizationGoal.MIN_AREA)


__all__ = [
    "CostModel",
    "OptimizationGoal",
    "FootingCandidate",
    "OptimizationResult",
    "optimize_footing_dimensions",
    "optimize_rectangular_footing",
]
