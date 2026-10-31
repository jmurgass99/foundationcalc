"""Service layer de FoundationCalc.

Funciones puras tipadas que envuelven los flujos principales de diseño:
zapatas aisladas, pilotes, muros, capacidad portante multi-layer, empuje
sísmico Mononobe-Okabe. Reutilizables desde GUI desktop, dashboard Streamlit,
REST API y job queue.
"""
from __future__ import annotations
from . import footings, walls, piles, bearing, seismic
__all__ = ["footings", "walls", "piles", "bearing", "seismic"]
