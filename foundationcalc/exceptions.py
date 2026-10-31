"""Jerarquia de excepciones tipadas de FoundationCalc.

Permite al caller (desktop GUI, dashboard Streamlit, REST API, AI Copilot)
diferenciar la naturaleza del fallo y reaccionar apropiadamente.

Ejemplo:
    try:
        design_isolated_footing(inp)
    except GeotechError as exc:
        # parametros de suelo invalidos
    except ConvergenceError as exc:
        # iteracion no convergio (raise/lower tolerance)
    except CodeError as exc:
        # caso fuera de aplicabilidad de la norma
    except FoundationError as exc:
        # generico
"""
from __future__ import annotations


class FoundationError(Exception):
    """Base de todas las excepciones del paquete."""


class GeotechError(FoundationError):
    """Parametros geotecnicos invalidos o inconsistentes.

    Ejemplos: phi negativo, cohesion < 0, perfil con espesores incoherentes,
    nivel freatico bajo el bed-rock declarado, etc.
    """


class DesignError(FoundationError):
    """Falla en el diseno estructural RC de la cimentacion.

    Ejemplos: dimensiones imposibles, espaciamiento de barras no cumple,
    cuantia minima inviable para la seccion dada.
    """


class CodeError(FoundationError):
    """Caso fuera del rango de aplicabilidad de la norma seleccionada.

    Ejemplos: Mononobe-Okabe con phi-theta-beta <= 0 (EC8-5), capacidad por
    capacidad portante con W/D > 1.5 (EC7), etc.
    """


class ConvergenceError(FoundationError):
    """El solver iterativo (asentamiento consolidacion, p-y pile lateral,
    iteracion de capacidad estratificada) no convergio.

    Atributos:
        iteration: ultimo numero de iteracion alcanzado.
        residual: residuo numerico al fallar.
    """

    def __init__(self, message: str, *, iteration: int = -1,
                 residual: float = float("nan")) -> None:
        super().__init__(message)
        self.iteration = iteration
        self.residual = residual


class FastSAPBridgeError(FoundationError):
    """Falla en el puente bidireccional FastSAP (extraccion de reacciones,
    inyeccion de springs Winkler, etc.).
    """


class DependencyError(FoundationError):
    """Falta un paquete opcional (fastapi, hypothesis, rebardxf)."""


class ConfigurationError(FoundationError):
    """Parametro de configuracion invalido o incompatible."""


__all__ = [
    "FoundationError",
    "GeotechError",
    "DesignError",
    "CodeError",
    "ConvergenceError",
    "FastSAPBridgeError",
    "DependencyError",
    "ConfigurationError",
]
