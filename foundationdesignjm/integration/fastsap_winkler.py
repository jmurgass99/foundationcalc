"""Bridge a FastSAP - exporta springs Winkler como joint springs en SAP.

Funciona con dry_run=True para tests sin SAP corriendo.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WinklerSpring:
    joint_name: str
    kx_kN_m: float
    ky_kN_m: float
    kz_kN_m: float


class FastSAPWinklerExporter:
    def __init__(self, client: Any = None, dry_run: bool = False):
        self.client = client
        self.dry_run = dry_run

    def export(self, springs: list[WinklerSpring]) -> dict:
        if self.dry_run or self.client is None:
            return {
                "applied": [s.joint_name for s in springs],
                "n_applied": len(springs),
                "n_failed": 0,
                "dry_run": True,
            }
        applied, failed = [], []
        for s in springs:
            try:
                self.client.PointObj.SetSpring(
                    s.joint_name,
                    (s.kx_kN_m, s.ky_kN_m, s.kz_kN_m, 0, 0, 0),
                )
                applied.append(s.joint_name)
            except Exception:  # pragma: no cover
                failed.append(s.joint_name)
        return {"applied": applied, "failed": failed,
                "n_applied": len(applied), "n_failed": len(failed),
                "dry_run": False}


__all__ = ["WinklerSpring", "FastSAPWinklerExporter"]
