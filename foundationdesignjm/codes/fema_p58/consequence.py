"""Consequence functions: damage state → cost / time / casualties.

FEMA P-58 represents consequences as lognormal distributions parameterised
by a median cost (or downtime, or casualty rate) and dispersion. For the
minimal port we store just the median per damage state — Monte Carlo
sampling adds dispersion at the loss-aggregation step (see `loss.py`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ConsequenceFunction:
    """Median cost (and optionally downtime / injuries) per damage state.

    For a component with N damage states, ``cost_per_ds`` is a list of
    length N (the cost when in DS_i; DS0 = undamaged → cost is 0 and
    implicit, not stored here).

    Units: caller's choice — typically USD or EUR. Stay consistent.
    """
    name: str
    cost_per_ds: List[float] = field(default_factory=list)
    cost_dispersion: float = 0.40   # default β for repair-cost spread
    downtime_per_ds_days: List[float] = field(default_factory=list)

    def expected_cost(self, p_in_state: List[float]) -> float:
        """E[cost] = Σ P(DS_i) · median_cost_i  (i=1..N; DS0 has no cost)."""
        if not p_in_state:
            return 0.0
        # p_in_state has n+1 entries; the first is DS0 (undamaged).
        damaged = p_in_state[1:]
        if len(damaged) != len(self.cost_per_ds):
            raise ValueError(
                f"Expected {len(self.cost_per_ds)} damaged-state probs, "
                f"got {len(damaged)}"
            )
        return sum(p * c for p, c in zip(damaged, self.cost_per_ds))

    def expected_downtime_days(self, p_in_state: List[float]) -> float:
        if not self.downtime_per_ds_days:
            return 0.0
        damaged = p_in_state[1:]
        return sum(p * d for p, d in zip(damaged, self.downtime_per_ds_days))


__all__ = ["ConsequenceFunction"]
