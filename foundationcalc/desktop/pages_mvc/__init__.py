"""Paginas MVC del desktop - patron nuevo para refactor progresivo de pages*.py.

Cada pagina vive en su propio archivo y usa los servicios de
`foundationcalc.services`. Logica de negocio NO acoplada a Tkinter.

A medida que se migren paginas legacy de `pages.py`/`pages_extra.py`/
`pages_new.py`, se anaden aqui.
"""
from __future__ import annotations
from .isolated_footing_page import IsolatedFootingPage
from .mononobe_okabe_page import MononobeOkabePage
from .bearing_capacity_page import BearingCapacityPage

__all__ = [
    "IsolatedFootingPage", "MononobeOkabePage", "BearingCapacityPage",
]
