"""FoundationCalc — a modern Eurocode-based foundation design library.

Theory and references in `docs/theory/`.
"""

# Core models
from .core.geometry import (
    Column,
    CombinedFoundation,
    FootingType,
    MatFoundation,
    RectangularFoundation,
    StrapFoundation,
    StripFoundation,
)
from .core.loading import (
    ActionCategory,
    CombinationEntry,
    LoadCombination,
    LoadType,
    PointLoad,
    seismic_combination,
    sls_characteristic,
    sls_quasi_permanent,
    uls_persistent_transient,
)
from .core.material import Concrete, ReinforcingSteel, Soil
from .core.piles import Pile, PileCap, PileInPlan, PileSupport, PileType
from .core.soil import (
    DrainageCondition,
    SoilLayer,
    SoilProfile,
    SoilType,
    homogeneous_clay,
    homogeneous_sand,
)

# Codes
from .codes.eurocode7 import (
    DesignApproach,
    EC7PartialFactors,
    LimitState,
    NationalAnnex,
    PartialFactorSet,
    get_partial_factors,
    utilization_ratio,
)

# Analysis
from .analysis.base_pressure import BasePressureAnalysis, CornerPressures, PressureRegime
from .analysis.mat_foundation import ColumnLoad, MatFoundationSolver, MatResult
from .analysis.crane import (
    CraneCheckResult,
    CraneLoadCase,
    CraneLoadState,
    crane_foundation_check,
    design_envelope,
)
from .analysis.bearing_capacity import (
    BearingCapacityFormula,
    BearingCapacityResult,
    bearing_capacity_factors,
    drained_bearing_capacity,
    shape_factors,
    undrained_bearing_capacity,
)
from .analysis.earth_pressure import (
    EarthPressureResult,
    K0,
    Ka_coulomb,
    Ka_rankine,
    Kp_coulomb,
    Kp_rankine,
    PressureState,
    active_thrust,
    at_rest_thrust,
    heel_min_width_for_rankine,
    passive_thrust,
    tension_crack_depth,
)
from .analysis.pile_capacity import PileCapacityResult, pile_axial_capacity
from .analysis.winkler import (
    FootingGeometry as WinklerFootingGeometry,
    WinklerStiffness,
    gazetas_stiffness,
)
from .analysis.seismic import (
    LiquefactionCheck,
    MononobeOkabeResult,
    cyclic_stress_ratio,
    liquefaction_screening,
    mononobe_okabe_K,
    normalised_SPT,
    reinforced_earth_external,
    rigid_wall_dynamic_increment,
    seismic_thrust,
)
from .analysis.stability import (
    OverturningCheck,
    SlidingCheck,
    overturning_check,
    sliding_resistance_drained,
    sliding_resistance_undrained,
)

# Design
from .design.pile_cap import (
    PileCapTieResult,
    cap_four_piles,
    cap_three_piles,
    cap_two_piles,
    distribute_forces_rigid_cap,
    pile_cap_secondary_vertical,
)
from .design.punching_shear import (
    AciPunchingShearResult,
    PunchingShearResult,
    punching_shear_aci318_check,
    punching_shear_check,
)
from .design.reinforcement import (
    ReinforcementResult,
    critical_section_offset,
    flexural_reinforcement,
    reinforcement_distribution_rectangular_footing,
    strut_and_tie_rigid_footing,
)
from .design.strap_beam import (
    GroundType,
    StrapBeamSpec,
    seismic_tie_force,
    strap_for_two_footings,
    tie_beam_minimum_dimensions,
)

__version__ = "0.2.0"

__all__ = [
    # Core — geometry
    "Column", "CombinedFoundation", "FootingType", "MatFoundation",
    "RectangularFoundation", "StrapFoundation", "StripFoundation",
    # Core — loading
    "ActionCategory", "CombinationEntry", "LoadCombination", "LoadType",
    "PointLoad", "seismic_combination", "sls_characteristic",
    "sls_quasi_permanent", "uls_persistent_transient",
    # Core — materials & soil
    "Concrete", "ReinforcingSteel", "Soil",
    "Pile", "PileCap", "PileInPlan", "PileSupport", "PileType",
    "DrainageCondition", "SoilLayer", "SoilProfile", "SoilType",
    "homogeneous_clay", "homogeneous_sand",
    # Codes
    "DesignApproach", "EC7PartialFactors", "LimitState", "NationalAnnex",
    "PartialFactorSet", "get_partial_factors", "utilization_ratio",
    # Analysis
    "BasePressureAnalysis", "CornerPressures", "PressureRegime",
    "BearingCapacityFormula", "BearingCapacityResult",
    "bearing_capacity_factors", "drained_bearing_capacity",
    "shape_factors", "undrained_bearing_capacity",
    "EarthPressureResult", "K0", "Ka_coulomb", "Ka_rankine", "Kp_coulomb",
    "Kp_rankine", "PressureState", "active_thrust", "at_rest_thrust",
    "heel_min_width_for_rankine", "passive_thrust", "tension_crack_depth",
    "PileCapacityResult", "pile_axial_capacity",
    "LiquefactionCheck", "MononobeOkabeResult", "cyclic_stress_ratio",
    "liquefaction_screening", "mononobe_okabe_K", "normalised_SPT",
    "reinforced_earth_external", "rigid_wall_dynamic_increment",
    "seismic_thrust",
    "OverturningCheck", "SlidingCheck", "overturning_check",
    "sliding_resistance_drained", "sliding_resistance_undrained",
    # Crane
    "CraneCheckResult", "CraneLoadCase", "CraneLoadState",
    "crane_foundation_check", "design_envelope",
    # Mat foundation
    "MatFoundationSolver", "MatResult", "ColumnLoad",
    # Design
    "PileCapTieResult", "cap_four_piles", "cap_three_piles", "cap_two_piles",
    "distribute_forces_rigid_cap", "pile_cap_secondary_vertical",
    "AciPunchingShearResult", "PunchingShearResult", "punching_shear_aci318_check", "punching_shear_check",
    "ReinforcementResult", "critical_section_offset",
    "flexural_reinforcement", "reinforcement_distribution_rectangular_footing",
    "strut_and_tie_rigid_footing",
    "GroundType", "StrapBeamSpec", "seismic_tie_force",
    "strap_for_two_footings", "tie_beam_minimum_dimensions",
    # Winkler / Gazetas SSI springs (P5 — FastSAP bridge)
    "WinklerFootingGeometry", "WinklerStiffness", "gazetas_stiffness",
]

# -----------------------------------------------------------------------------
# Exceptions hierarchy (Mejora B)
# -----------------------------------------------------------------------------
from .exceptions import (
    FoundationError, GeotechError, DesignError, CodeError,
    ConvergenceError, FastSAPBridgeError,
    DependencyError, ConfigurationError,
)

from . import reaction_bridge
from .design.reinforcement import (
    FootingFlexureDetail,
    anchorage_length_ec2,
    design_footing_flexure_both_ways,
    select_footing_rebar,
)
from .integration.dxf_armado import ArmadoZapataDXF, export_armado_zapata
from .integration.foundation_chain import (
    FoundationChainResult,
    FoundationPackageResult,
    foundation_chain_from_etabs,
    foundation_package,
)

__all__ += [
    "FootingFlexureDetail",
    "anchorage_length_ec2",
    "design_footing_flexure_both_ways",
    "select_footing_rebar",
    "ArmadoZapataDXF",
    "export_armado_zapata",
    "FoundationChainResult",
    "FoundationPackageResult",
    "foundation_chain_from_etabs",
    "foundation_package",
]
