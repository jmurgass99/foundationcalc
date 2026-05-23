"""Loss aggregation: combine fragilities + consequence functions over a
building EDP set to obtain expected repair cost (and optionally downtime).

Two computation modes:

1. **Analytical expected value** — Σ P(DS_i) · cost_i, no Monte Carlo.
   Fast, deterministic; cost dispersion ignored.
2. **Monte Carlo** — for each realisation, sample a damage state from
   the categorical p_in_state and a cost from a lognormal centred on the
   median (with dispersion β). Aggregate to a distribution of building
   loss.

For *Expected Annual Loss* we accept a hazard curve (return-period →
intensity) and an EDP model (intensity → EDP); we integrate by trapezoid
rule over the hazard curve.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .consequence import ConsequenceFunction
from .edp import BuildingEDP
from .fragility import FragilitySet


@dataclass
class ComponentGroup:
    """A bundle of identical components on a given story.

    EDP type tells the loss aggregator which scalar to use:
        "drift"  → uses StoryEDP.drift_max
        "pfa"    → uses StoryEDP.pfa_max
    """
    name: str
    story: str
    quantity: int
    fragility: FragilitySet
    consequence: ConsequenceFunction
    edp_type: str = "drift"            # "drift" or "pfa"


@dataclass
class Building:
    """Collection of component groups."""
    groups: List[ComponentGroup] = field(default_factory=list)
    name: str = "Building"


@dataclass
class LossResult:
    expected_cost: float
    expected_downtime_days: float
    cost_by_group: Dict[str, float]
    n_realisations: int = 1
    cost_realisations: List[float] = field(default_factory=list)

    def percentile(self, q: float) -> float:
        if not self.cost_realisations:
            return self.expected_cost
        s = sorted(self.cost_realisations)
        idx = int(round((q / 100.0) * (len(s) - 1)))
        idx = max(0, min(len(s) - 1, idx))
        return s[idx]


# ---------------------------------------------------------------------------
# Core deterministic E[cost]
# ---------------------------------------------------------------------------

def expected_loss(building: Building, edp: BuildingEDP) -> LossResult:
    """Analytical Σ P(DS_i)·cost_i over every component group."""
    edps_by_story = {s.story: s for s in edp.stories}
    total_cost = 0.0
    total_dt = 0.0
    by_group: Dict[str, float] = {}
    for g in building.groups:
        s = edps_by_story.get(g.story)
        if s is None:
            continue
        x = s.drift_max if g.edp_type == "drift" else s.pfa_max
        p = g.fragility.p_in_state(x)
        cost_per_unit = g.consequence.expected_cost(p)
        dt_per_unit = g.consequence.expected_downtime_days(p)
        cost = cost_per_unit * g.quantity
        total_cost += cost
        total_dt += dt_per_unit * g.quantity
        by_group[g.name] = by_group.get(g.name, 0.0) + cost
    return LossResult(expected_cost=total_cost, expected_downtime_days=total_dt,
                      cost_by_group=by_group, n_realisations=1)


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

def monte_carlo_loss(building: Building, edp: BuildingEDP, *,
                      n_sims: int = 1000, seed: int = 0) -> LossResult:
    """Monte Carlo aggregation: returns mean cost + per-realisation list."""
    rng = random.Random(seed)
    edps_by_story = {s.story: s for s in edp.stories}
    realisations = []
    cost_by_group: Dict[str, float] = {}

    for _ in range(n_sims):
        total = 0.0
        for g in building.groups:
            s = edps_by_story.get(g.story)
            if s is None:
                continue
            x = s.drift_max if g.edp_type == "drift" else s.pfa_max
            p = g.fragility.p_in_state(x)
            # Sample one categorical state per component, n=quantity
            for _q in range(g.quantity):
                state = _categorical_sample(rng, p)
                if state == 0:
                    continue
                median_cost = g.consequence.cost_per_ds[state - 1]
                beta = g.consequence.cost_dispersion
                cost = _lognormal_sample(rng, median_cost, beta)
                total += cost
                cost_by_group[g.name] = cost_by_group.get(g.name, 0.0) + cost
        realisations.append(total)

    n = max(len(realisations), 1)
    mean = sum(realisations) / n
    # Normalise cost_by_group across n_sims so it represents an average
    by_group_avg = {k: v / n for k, v in cost_by_group.items()}
    return LossResult(
        expected_cost=mean,
        expected_downtime_days=0.0,   # downtime in MC handled separately
        cost_by_group=by_group_avg,
        n_realisations=n,
        cost_realisations=realisations,
    )


def _categorical_sample(rng: random.Random, probs: Sequence[float]) -> int:
    u = rng.random()
    acc = 0.0
    for i, p in enumerate(probs):
        acc += p
        if u <= acc:
            return i
    return len(probs) - 1


def _lognormal_sample(rng: random.Random, median: float, beta: float) -> float:
    """Sample a lognormal with given median and log-σ = β."""
    # mean of underlying normal = ln(median); std = β
    z = rng.gauss(0.0, 1.0)
    return median * math.exp(beta * z)


# ---------------------------------------------------------------------------
# Expected Annual Loss (EAL)
# ---------------------------------------------------------------------------

def expected_annual_loss(
    building: Building,
    hazard_curve: Sequence[Tuple[float, float]],
    edp_from_intensity: Callable[[float], BuildingEDP],
) -> float:
    """Integrate loss · |d(λ)/d(im)| over the hazard curve (trapezoid rule).

    Args:
        building: configured building.
        hazard_curve: ordered list of (im, lambda) pairs — intensity vs
                      mean annual rate of exceedance. Must be monotonic
                      in im.
        edp_from_intensity: a callable mapping intensity → BuildingEDP
                            (typically a regression on NLTH results).

    Returns:
        Expected annual loss (in caller's monetary unit per year).
    """
    if len(hazard_curve) < 2:
        return 0.0
    # Sort by intensity ascending
    hc = sorted(hazard_curve, key=lambda t: t[0])
    # Differential rate (annual frequency density per im, central differences)
    eal = 0.0
    for i in range(len(hc) - 1):
        im_a, lam_a = hc[i]
        im_b, lam_b = hc[i + 1]
        # |dλ/dim| ≈ (λ_a − λ_b) / (im_b − im_a)  (positive since λ decreases)
        d_lambda = (lam_a - lam_b)
        # Loss at midpoint
        im_mid = 0.5 * (im_a + im_b)
        edp = edp_from_intensity(im_mid)
        loss = expected_loss(building, edp).expected_cost
        eal += loss * d_lambda
    return eal


__all__ = [
    "ComponentGroup",
    "Building",
    "LossResult",
    "expected_loss",
    "monte_carlo_loss",
    "expected_annual_loss",
]
