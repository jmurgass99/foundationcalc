"""Tests de las paginas MVC.

Las paginas Tk requieren Tk display. En CI sin display estos tests se
skipean automaticamente. En desarrollo local si se verifican.
"""
from __future__ import annotations
import pytest


@pytest.fixture
def tk_root():
    """Crea un Tk root invisible. Skipea si no hay display."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:
        pytest.skip(f"Tk no disponible: {exc}")
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def test_isolated_footing_page_constructs(tk_root):
    from foundationdesignjm.desktop.pages_mvc.isolated_footing_page import (
        IsolatedFootingPage,
    )
    p = IsolatedFootingPage(tk_root)
    assert p.frame is not None
    assert "N" in p.vars


def test_mononobe_okabe_page_constructs(tk_root):
    from foundationdesignjm.desktop.pages_mvc.mononobe_okabe_page import (
        MononobeOkabePage,
    )
    p = MononobeOkabePage(tk_root)
    assert p.frame is not None


def test_bearing_capacity_page_constructs(tk_root):
    from foundationdesignjm.desktop.pages_mvc.bearing_capacity_page import (
        BearingCapacityPage,
    )
    p = BearingCapacityPage(tk_root)
    assert p.frame is not None
    assert len(p.layer_vars) == 3


def test_pages_mvc_re_export():
    from foundationdesignjm.desktop.pages_mvc import (
        IsolatedFootingPage, MononobeOkabePage, BearingCapacityPage,
    )
    assert IsolatedFootingPage is not None
    assert MononobeOkabePage is not None
    assert BearingCapacityPage is not None
