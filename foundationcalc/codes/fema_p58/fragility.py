"""Lognormal fragility functions (FEMA P-58 style).

A fragility curve is the conditional probability that a component
exceeds a given damage state (DS), as a function of an engineering
demand parameter (EDP, e.g. story drift or peak floor acceleration):

    P[DS ≥ ds_i | EDP = x] = Φ( ln(x / θ_i) / β_i )

where θ_i is the median (50 % probability of exceedance) and β_i is the
log-standard deviation (lognormal dispersion).

This module is pure numpy/math — no scipy needed at runtime (we compute Φ
analytically via the error function). FEMA P-58 reference: Volume 1,
Methodology, §3.3.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Sequence


def _phi(z: float) -> float:
    """Standard normal CDF, computed via erf — no scipy dependency."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


@dataclass
class LognormalFragility:
    """One fragility curve (one damage state).

    Args:
        theta: median EDP at which P[exceedance] = 0.5.
        beta:  log-standard deviation.
    """
    theta: float
    beta: float

    def __post_init__(self):
        if self.theta <= 0 or self.beta <= 0:
            raise ValueError("theta and beta must be positive")

    def p_exceed(self, edp: float) -> float:
        """P[DS exceeded | EDP = edp]."""
        if edp <= 0:
            return 0.0
        z = math.log(edp / self.theta) / self.beta
        return _phi(z)

    # Convenience: vectorised version (no numpy in signature so we
    # don't impose it on the caller).
    def p_exceed_many(self, edps: Sequence[float]) -> List[float]:
        return [self.p_exceed(e) for e in edps]


@dataclass
class FragilitySet:
    """An ordered set of fragility curves for one component.

    Damage states must be ordered from least severe (DS1) to most severe
    (DSn) with monotonically increasing medians. The probability of being
    *in* state DS_i is the difference of two cumulative exceedance
    probabilities (DS_i is exceeded but DS_{i+1} is not).
    """
    name: str
    damage_states: List[LognormalFragility] = field(default_factory=list)

    def __post_init__(self):
        thetas = [f.theta for f in self.damage_states]
        if any(b <= a for a, b in zip(thetas, thetas[1:])):
            raise ValueError("damage_state medians must be strictly increasing")

    def n_states(self) -> int:
        return len(self.damage_states)

    def p_in_state(self, edp: float) -> List[float]:
        """Return ``[P(DS0), P(DS1), ..., P(DSn)]`` (n+1 entries, summing to 1).

        DS0 = "undamaged"; DSn = most severe. The list is normalised by
        construction.
        """
        n = self.n_states()
        if n == 0:
            return [1.0]
        cumulative_exceed = [f.p_exceed(edp) for f in self.damage_states]
        probs = []
        # P(DS0) = 1 - P(exceed DS1)
        probs.append(1.0 - cumulative_exceed[0])
        # P(DS_i) for i in 1..n-1
        for i in range(n - 1):
            probs.append(cumulative_exceed[i] - cumulative_exceed[i + 1])
        # P(DS_n) = P(exceed last DS)
        probs.append(cumulative_exceed[-1])
        # Clamp tiny negatives from float noise
        return [max(0.0, p) for p in probs]

    def expected_state(self, edp: float) -> float:
        """Expected damage-state index 0..n (weighted by p_in_state)."""
        ps = self.p_in_state(edp)
        return sum(i * p for i, p in enumerate(ps))


__all__ = ["LognormalFragility", "FragilitySet"]
