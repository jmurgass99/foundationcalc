"""Tests de la jerarquia de excepciones."""
from __future__ import annotations
import pytest

from foundationdesignjm.exceptions import (
    FoundationError, GeotechError, DesignError, CodeError,
    ConvergenceError, FastSAPBridgeError,
    DependencyError, ConfigurationError,
)


def test_hierarchy():
    for cls in (GeotechError, DesignError, CodeError, ConvergenceError,
                FastSAPBridgeError, DependencyError, ConfigurationError):
        assert issubclass(cls, FoundationError)


def test_convergence_carries_metadata():
    exc = ConvergenceError("no convergio", iteration=15, residual=0.01)
    assert exc.iteration == 15
    assert exc.residual == 0.01


def test_can_catch_via_base():
    with pytest.raises(FoundationError):
        raise GeotechError("phi negativo")
    with pytest.raises(FoundationError):
        raise FastSAPBridgeError("COM no responde")


def test_can_catch_specific():
    with pytest.raises(GeotechError):
        raise GeotechError("suelo invalido")
    with pytest.raises(CodeError):
        raise CodeError("Mononobe fuera de rango")


def test_dependency_error_distinct():
    with pytest.raises(DependencyError):
        raise DependencyError("falta ezdxf")
    with pytest.raises(FoundationError):
        raise DependencyError("idem")  # tambien atrapable por base


def test_can_reexport_from_package():
    """Las excepciones se exportan desde el namespace raiz del paquete."""
    import foundationdesignjm as fdj
    assert fdj.FoundationError is FoundationError
    assert fdj.GeotechError is GeotechError
    assert fdj.ConvergenceError is ConvergenceError
