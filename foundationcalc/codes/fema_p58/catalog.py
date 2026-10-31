"""Curated, minimal P-58 component catalog.

This is intentionally a SMALL hand-curated subset — the user can extend
it via JSON files under ``fastsap/codes/fema_p58/data/``. Values are
illustrative, NOT FEMA-conformant; replace with your own PACT-derived
data for real projects.

Components included:
  - drywall_partition      (drift-sensitive)
  - suspended_ceiling      (acceleration-sensitive)
  - hvac_chiller           (acceleration-sensitive)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from .consequence import ConsequenceFunction
from .fragility import FragilitySet, LognormalFragility


# ---------------------------------------------------------------------------
# Hard-coded baseline components
# ---------------------------------------------------------------------------

def drywall_partition() -> tuple[FragilitySet, ConsequenceFunction]:
    """Gypsum-board partition, drift-sensitive (per FEMA P-58 B1051.011a)."""
    frag = FragilitySet(
        name="drywall_partition",
        damage_states=[
            LognormalFragility(theta=0.0021, beta=0.6),   # DS1 cracking
            LognormalFragility(theta=0.0071, beta=0.45),  # DS2 major damage
        ],
    )
    cons = ConsequenceFunction(
        name="drywall_partition",
        cost_per_ds=[60.0, 200.0],          # USD per m² per DS (illustrative)
        downtime_per_ds_days=[1.0, 5.0],
        cost_dispersion=0.40,
    )
    return frag, cons


def suspended_ceiling() -> tuple[FragilitySet, ConsequenceFunction]:
    """Acoustic suspended ceiling, PFA-sensitive (FEMA P-58 C3032.001a)."""
    frag = FragilitySet(
        name="suspended_ceiling",
        damage_states=[
            LognormalFragility(theta=0.55, beta=0.40),    # DS1 tile drop
            LognormalFragility(theta=1.20, beta=0.40),    # DS2 grid collapse
        ],
    )
    cons = ConsequenceFunction(
        name="suspended_ceiling",
        cost_per_ds=[40.0, 150.0],
        downtime_per_ds_days=[0.5, 4.0],
        cost_dispersion=0.40,
    )
    return frag, cons


def hvac_chiller() -> tuple[FragilitySet, ConsequenceFunction]:
    """HVAC chiller, PFA-sensitive (illustrative)."""
    frag = FragilitySet(
        name="hvac_chiller",
        damage_states=[
            LognormalFragility(theta=0.30, beta=0.50),    # DS1 anchorage
            LognormalFragility(theta=0.80, beta=0.45),    # DS2 housing
            LognormalFragility(theta=1.50, beta=0.40),    # DS3 total loss
        ],
    )
    cons = ConsequenceFunction(
        name="hvac_chiller",
        cost_per_ds=[8_000.0, 25_000.0, 80_000.0],
        downtime_per_ds_days=[3.0, 15.0, 60.0],
        cost_dispersion=0.50,
    )
    return frag, cons


BUILTIN_COMPONENTS: Dict[str, callable] = {
    "drywall_partition": drywall_partition,
    "suspended_ceiling": suspended_ceiling,
    "hvac_chiller":      hvac_chiller,
}


def get(name: str) -> tuple[FragilitySet, ConsequenceFunction]:
    """Look up a built-in component by name."""
    if name not in BUILTIN_COMPONENTS:
        raise KeyError(f"Component '{name}' not in built-in catalog; "
                       f"available: {sorted(BUILTIN_COMPONENTS)}")
    return BUILTIN_COMPONENTS[name]()


# ---------------------------------------------------------------------------
# JSON loader (extends the catalog at runtime)
# ---------------------------------------------------------------------------

def load_from_json(path: str | Path
                   ) -> tuple[FragilitySet, ConsequenceFunction]:
    """Load a custom component from a JSON file.

    Schema:
        {
            "name": "...",
            "damage_states": [{"theta": 0.01, "beta": 0.4}, ...],
            "cost_per_ds":     [100.0, 250.0, ...],
            "cost_dispersion": 0.4,
            "downtime_per_ds_days": [1.0, 5.0, ...]
        }
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    frag = FragilitySet(
        name=data["name"],
        damage_states=[
            LognormalFragility(theta=ds["theta"], beta=ds["beta"])
            for ds in data["damage_states"]
        ],
    )
    cons = ConsequenceFunction(
        name=data["name"],
        cost_per_ds=list(data["cost_per_ds"]),
        cost_dispersion=float(data.get("cost_dispersion", 0.40)),
        downtime_per_ds_days=list(data.get("downtime_per_ds_days", [])),
    )
    return frag, cons


__all__ = [
    "drywall_partition",
    "suspended_ceiling",
    "hvac_chiller",
    "BUILTIN_COMPONENTS",
    "get",
    "load_from_json",
]
