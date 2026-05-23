"""Engineering Demand Parameters (EDPs) for FEMA P-58.

Bridges FastSAP analysis results (drifts from ``codes/drifts.py``, peak
floor accelerations from extractor DataFrames) to the format expected by
:func:`expected_loss`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import pandas as pd


@dataclass
class StoryEDP:
    """Per-story engineering demand parameters."""
    story: str
    drift_x: float = 0.0           # interstory drift (Δ/h, X direction)
    drift_y: float = 0.0
    pfa_x: float = 0.0             # peak floor acceleration g (top of story)
    pfa_y: float = 0.0

    @property
    def drift_max(self) -> float:
        return max(abs(self.drift_x), abs(self.drift_y))

    @property
    def pfa_max(self) -> float:
        return max(abs(self.pfa_x), abs(self.pfa_y))


@dataclass
class BuildingEDP:
    """All stories' EDPs for one analysis realisation."""
    stories: List[StoryEDP] = field(default_factory=list)
    name: str = "EDP"

    def n_stories(self) -> int:
        return len(self.stories)

    def drifts(self) -> List[float]:
        return [s.drift_max for s in self.stories]

    def accelerations(self) -> List[float]:
        return [s.pfa_max for s in self.stories]


def edp_from_dataframe(df: pd.DataFrame,
                        story_col: str = "story",
                        drift_x_col: str = "drift_x",
                        drift_y_col: str = "drift_y",
                        pfa_x_col: Optional[str] = "pfa_x",
                        pfa_y_col: Optional[str] = "pfa_y",
                        name: str = "EDP") -> BuildingEDP:
    """Build a :class:`BuildingEDP` from an extractor-style DataFrame."""
    stories: List[StoryEDP] = []
    for _, row in df.iterrows():
        stories.append(StoryEDP(
            story=str(row[story_col]),
            drift_x=float(row[drift_x_col]),
            drift_y=float(row[drift_y_col]),
            pfa_x=float(row[pfa_x_col]) if pfa_x_col and pfa_x_col in df.columns else 0.0,
            pfa_y=float(row[pfa_y_col]) if pfa_y_col and pfa_y_col in df.columns else 0.0,
        ))
    return BuildingEDP(stories=stories, name=name)


__all__ = ["StoryEDP", "BuildingEDP", "edp_from_dataframe"]
