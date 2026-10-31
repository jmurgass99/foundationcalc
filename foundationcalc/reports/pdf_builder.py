"""PDF builder — thin wrapper around reportlab.platypus.

`Report` lets callers compose a multi-section document: cover, headings,
paragraphs, dataframes, matplotlib figures, and key-value spec tables.

Pure Python — no SAP dependency. Used by `templates.py` for prebuilt
report layouts.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional, Sequence, Tuple, Union

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass
class Report:
    """A composable PDF report.

    Call sequence: `Report(...).add_*().save(path)`. All `add_*` methods
    return `self` so calls can be chained.
    """
    title: str
    subtitle: str = ""
    author: str = ""
    project: str = ""
    _story: List[Any] = field(default_factory=list)
    _styles: Any = None

    def __post_init__(self):
        self._styles = getSampleStyleSheet()
        # Cover content
        self._story.append(Paragraph(self.title, self._styles["Title"]))
        if self.subtitle:
            self._story.append(Paragraph(self.subtitle, self._styles["Heading3"]))
        meta_lines = []
        if self.project:
            meta_lines.append(f"<b>Project:</b> {self.project}")
        if self.author:
            meta_lines.append(f"<b>Author:</b> {self.author}")
        meta_lines.append(f"<b>Generated:</b> {datetime.now():%Y-%m-%d %H:%M}")
        for line in meta_lines:
            self._story.append(Paragraph(line, self._styles["BodyText"]))
        self._story.append(Spacer(1, 0.6 * cm))

    # ------------------------------------------------------------------
    def add_section(self, title: str) -> "Report":
        self._story.append(Spacer(1, 0.4 * cm))
        self._story.append(Paragraph(title, self._styles["Heading1"]))
        return self

    def add_subsection(self, title: str) -> "Report":
        self._story.append(Paragraph(title, self._styles["Heading2"]))
        return self

    def add_paragraph(self, text: str) -> "Report":
        self._story.append(Paragraph(text, self._styles["BodyText"]))
        return self

    def add_kv_table(self, rows: Sequence[Tuple[str, Any]]) -> "Report":
        """Two-column key/value table — good for design summaries."""
        data = [[k, _fmt(v)] for k, v in rows]
        t = Table(data, colWidths=[6 * cm, 8 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        self._story.append(t)
        self._story.append(Spacer(1, 0.3 * cm))
        return self

    def add_dataframe(self, df: pd.DataFrame, caption: str = "",
                      max_rows: int = 30,
                      col_widths: Optional[Sequence[float]] = None) -> "Report":
        """Render a pandas DataFrame as a table (header + values)."""
        if caption:
            self._story.append(Paragraph(f"<i>{caption}</i>",
                                          self._styles["BodyText"]))
        truncated = df.head(max_rows) if len(df) > max_rows else df
        data = [list(map(str, truncated.columns))] + \
               [[_fmt(c) for c in row] for row in truncated.itertuples(index=False)]
        n_cols = len(data[0])
        widths = col_widths or [16.0 * cm / n_cols] * n_cols
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f497d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f1f5fb")]),
        ]))
        self._story.append(t)
        self._story.append(Spacer(1, 0.3 * cm))
        if len(df) > max_rows:
            self._story.append(Paragraph(
                f"<i>Showing first {max_rows} of {len(df)} rows.</i>",
                self._styles["BodyText"]))
        return self

    def add_figure(self, fig, caption: str = "", width_cm: float = 16.0,
                   dpi: int = 150) -> "Report":
        """Embed a matplotlib Figure (or any object with `.savefig`)."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        img = Image(buf, width=width_cm * cm,
                    height=width_cm * 0.62 * cm)  # 16:10ish
        self._story.append(img)
        if caption:
            self._story.append(Paragraph(f"<i>{caption}</i>",
                                          self._styles["BodyText"]))
        self._story.append(Spacer(1, 0.3 * cm))
        return self

    def add_page_break(self) -> "Report":
        self._story.append(PageBreak())
        return self

    # ------------------------------------------------------------------
    def save(self, path: str) -> str:
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
            title=self.title, author=self.author or "FastSAP",
        )
        doc.build(self._story)
        return path


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        if abs(v) >= 1e5 or (v != 0 and abs(v) < 1e-3):
            return f"{v:.3e}"
        return f"{v:.4g}"
    if v is None:
        return ""
    return str(v)


__all__ = ["Report"]
