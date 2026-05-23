"""Integration adapters with sibling libraries.

The integration sub-package contains opt-in bridges to other tools so
that `FoundationDesignJm` can be used as the *foundation side* of a
larger workflow without forcing a hard dependency on those tools.

Currently available:

- ``dynamicsjm_bridge``: converts a ``FoundationImpedance`` (Gazetas
  springs) into the dynamic boundary conditions used by ``DynamicsJm``,
  computes the SSI-modified natural period of a SDOF building, and
  runs the full **CPT → SSI → dynamic → FEMA P-58 loss** pipeline
  via the ``EarthquakeRiskAnalyzer`` of ``DynamicsJm.risk``.

If the target library is not installed, the bridge functions raise
``ImportError`` with a clear message instead of failing silently.
"""

from .dynamicsjm_bridge import (
    DYNAMICSJM_AVAILABLE,
    SSIResponse,
    SeismicLossPipelineResult,
    cpt_to_seismic_loss_pipeline,
    impedance_to_springs,
    ssi_modified_period,
)

from .geojm_bridge import (
    get_py_springs_from_geojm,
    get_mander_concrete_from_geojm,
    PYSpring,
    ManderConfinedConcrete,
    PileLayerData,
)

__all__ = [
    "DYNAMICSJM_AVAILABLE",
    "SSIResponse",
    "SeismicLossPipelineResult",
    "cpt_to_seismic_loss_pipeline",
    "impedance_to_springs",
    "ssi_modified_period",
    "get_py_springs_from_geojm",
    "get_mander_concrete_from_geojm",
    "PYSpring",
    "ManderConfinedConcrete",
    "PileLayerData",
]
