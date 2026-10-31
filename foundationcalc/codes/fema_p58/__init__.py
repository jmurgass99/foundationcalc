"""FEMA P-58 inspired minimal loss-assessment module.

NOTE: This is a *minimal* re-implementation — fragility & consequence
math only. Not a complete P-58 replica. For production use replace the
catalog with PACT-derived data.

Modules:
    fragility   — LognormalFragility, FragilitySet
    consequence — ConsequenceFunction
    edp         — BuildingEDP, StoryEDP, edp_from_dataframe
    loss        — ComponentGroup, Building, expected_loss,
                  monte_carlo_loss, expected_annual_loss
    catalog     — built-in components + JSON loader
"""
from .catalog import (
    BUILTIN_COMPONENTS,
    drywall_partition,
    get,
    hvac_chiller,
    load_from_json,
    suspended_ceiling,
)
from .consequence import ConsequenceFunction
from .edp import BuildingEDP, StoryEDP, edp_from_dataframe
from .fragility import FragilitySet, LognormalFragility
from .loss import (
    Building,
    ComponentGroup,
    LossResult,
    expected_annual_loss,
    expected_loss,
    monte_carlo_loss,
)

__all__ = [
    # fragility
    "LognormalFragility",
    "FragilitySet",
    # consequence
    "ConsequenceFunction",
    # edp
    "BuildingEDP",
    "StoryEDP",
    "edp_from_dataframe",
    # loss
    "ComponentGroup",
    "Building",
    "LossResult",
    "expected_loss",
    "monte_carlo_loss",
    "expected_annual_loss",
    # catalog
    "BUILTIN_COMPONENTS",
    "get",
    "load_from_json",
    "drywall_partition",
    "suspended_ceiling",
    "hvac_chiller",
]
