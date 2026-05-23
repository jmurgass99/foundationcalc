"""Optional efficalc backend for richer LaTeX-rendered design calcs.

`efficalc` is a 3rd-party library that wraps SymPy-formatted equations
into LaTeX PDF output. It requires a working LaTeX installation. We treat
it as fully optional: import failures degrade silently so the rest of
`fastsap.reports` keeps working.
"""
from __future__ import annotations

try:
    import efficalc  # type: ignore
    HAS_EFFICALC = True
except Exception:                                              # noqa: BLE001
    efficalc = None
    HAS_EFFICALC = False


def is_available() -> bool:
    """True if efficalc imported successfully on this machine."""
    return HAS_EFFICALC


def build_efficalc_section(*args, **kwargs):                   # pragma: no cover
    """Stub — wire actual efficalc usage here.

    Raises:
        RuntimeError: when efficalc is not installed.
    """
    if not HAS_EFFICALC:
        raise RuntimeError(
            "efficalc is not installed. `pip install efficalc` (requires "
            "LaTeX) or use the reportlab backend in `pdf_builder.Report`."
        )
    raise NotImplementedError("Efficalc backend stub — wire as needed.")


__all__ = ["is_available", "build_efficalc_section", "HAS_EFFICALC"]
