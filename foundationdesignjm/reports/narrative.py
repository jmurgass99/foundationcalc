"""Renderizador narrativo paso a paso para verificaciones estructurales.

Estructura cada verificacion como: input -> formula -> referencia normativa
-> sustitucion numerica -> resultado -> veredicto. Devuelve bloques que se
inyectan directamente en `reports.Report` via `add_narrative_check`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

from .pdf_builder import Report


@dataclass
class CheckStep:
    description: str
    formula: str = ""
    reference: str = ""
    inputs: Sequence[Tuple[str, Any]] = ()
    result_label: str = ""
    result_value: Any = None
    units: str = ""
    verdict: Optional[bool] = None
    limit: Any = None


@dataclass
class NarrativeCheck:
    title: str
    code: str = ""               # p.ej. "AISC 360-22 F2"
    steps: List[CheckStep] = field(default_factory=list)

    def step(self, **kwargs) -> "NarrativeCheck":
        self.steps.append(CheckStep(**kwargs))
        return self


def add_narrative_check(rep: Report, check: NarrativeCheck) -> Report:
    """Renderiza un `NarrativeCheck` dentro de un `Report` existente."""
    rep.add_subsection(check.title)
    if check.code:
        rep.add_paragraph(f"<b>Normativa:</b> {check.code}")
    for i, st in enumerate(check.steps, 1):
        head = f"<b>Paso {i}.</b> {st.description}"
        rep.add_paragraph(head)
        if st.reference:
            rep.add_paragraph(f"<i>Ref.: {st.reference}</i>")
        if st.formula:
            rep.add_paragraph(f"<font face='Courier'>{st.formula}</font>")
        if st.inputs:
            rep.add_kv_table(list(st.inputs))
        if st.result_value is not None:
            row = (st.result_label or "Resultado",
                   f"{st.result_value} {st.units}".strip())
            rep.add_kv_table([row])
        if st.verdict is not None:
            tag = "OK" if st.verdict else "NO CUMPLE"
            line = f"<b>Veredicto:</b> {tag}"
            if st.limit is not None:
                line += f"  (limite: {st.limit})"
            rep.add_paragraph(line)
    return rep


__all__ = ["CheckStep", "NarrativeCheck", "add_narrative_check"]
