"""FastSAP PDF reports (Phase 3 of the Nuevos integration roadmap).

Pure-Python rendering on top of reportlab. Optional efficalc backend
(LaTeX) auto-detected via :pyfunc:`efficalc_backend.is_available`.
"""
from .efficalc_backend import HAS_EFFICALC, is_available
from .master_report import (
    MaterialsSpec,
    MemoriaData,
    ProjectInfo,
    SeismicParams,
    build_master_memoria,
)
from .narrative import CheckStep, NarrativeCheck, add_narrative_check
from .pdf_builder import Report
from .step_by_step import (
    StepBlock,
    StepRecord,
    aci_scwb_step_block,
    asce7_base_shear_step_block,
    ec8_beam_capacity_step_block,
    generic_notes_block,
    rbs_step_block,
    render_block_markdown,
    render_block_pdf,
    wall_shear_step_block,
)
from .templates import (
    build_audit_report,
    build_drift_report,
    build_loss_report,
    build_modal_report,
    build_section_report,
    build_steel_design_report,
)

__all__ = [
    "HAS_EFFICALC",
    "is_available",
    "MaterialsSpec",
    "MemoriaData",
    "ProjectInfo",
    "SeismicParams",
    "build_master_memoria",
    "CheckStep",
    "NarrativeCheck",
    "add_narrative_check",
    "Report",
    "build_audit_report",
    "build_drift_report",
    "build_loss_report",
    "build_modal_report",
    "build_section_report",
    "build_steel_design_report",
    "StepBlock",
    "StepRecord",
    "aci_scwb_step_block",
    "asce7_base_shear_step_block",
    "ec8_beam_capacity_step_block",
    "generic_notes_block",
    "rbs_step_block",
    "render_block_markdown",
    "render_block_pdf",
    "wall_shear_step_block",
]
