"""Configuracion compartida de pytest para FoundationDesignJm.

Garantiza que el package es importable y anade fixtures comunes.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
import matplotlib
matplotlib.use("Agg", force=True)


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def _close_matplotlib_figures():
    """Cierra todas las figuras de matplotlib tras cada test.

    Evita flakiness por acumulación del estado global de pyplot: el test
    ``test_pdf_report.py::test_builder_creates_valid_pdf`` fallaba de forma
    intermitente (depende del orden) al correr junto a los ``report_*`` tests,
    que abren muchas figuras vía ``plt.figure()``. Forzar backend headless +
    cerrar todas las figuras aísla cada test.
    """
    import matplotlib
    matplotlib.use("Agg", force=True)
    yield
    try:
        import matplotlib.pyplot as plt
        plt.close("all")
    except Exception:
        pass


@pytest.fixture
def rng_seed_42():
    """Numpy Generator determinista."""
    import numpy as np
    return np.random.default_rng(42)


@pytest.fixture
def examples_dir() -> Path:
    return REPO_ROOT / "examples"


@pytest.fixture
def docs_dir() -> Path:
    return REPO_ROOT / "docs"
