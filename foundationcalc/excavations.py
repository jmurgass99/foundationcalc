"""EN 1997-1 §12 — Excavaciones soportadas y heave de fondo.

Implementa los chequeos clasicos de excavaciones profundas soportadas
(braced/anchored cuts) recomendados por Eurocodigo 7 (EN 1997-1, Seccion 12
"Overall stability" y los anexos informativos sobre excavaciones):

* Factor de seguridad contra heave (basal heave / levantamiento de fondo)
  segun Terzaghi & Peck (1967).
* Diagramas de presion aparente para arcillas blandas/medias/rigidas y
  arenas (envolventes de Peck 1969 / Terzaghi-Peck 1967).
* Fuerzas en puntales (struts) por el metodo de areas tributarias.
* Chequeo especifico de basal heave en arcilla blanda con Nc = 5.14 (zanja
  larga) o 5.7·(1 + 0.2·B/L) (excavacion rectangular).

Referencias
-----------
* EN 1997-1:2004+A1:2013 Geotechnical design — Part 1, Section 12.
* Terzaghi, K. & Peck, R. B. (1967). *Soil Mechanics in Engineering
  Practice*, 2nd ed., Wiley, Chapter 11.
* Peck, R. B. (1969). "Deep excavations and tunneling in soft ground",
  State-of-the-Art Report, 7th ICSMFE, Mexico.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

from .exceptions import GeotechError

__all__ = [
    "terzaghi_peck_heave",
    "apparent_earth_pressure",
    "strut_force",
    "basal_heave_clay",
]


# ---------------------------------------------------------------------------
# 1. Heave de fondo — Terzaghi & Peck (1967)
# ---------------------------------------------------------------------------
def terzaghi_peck_heave(
    B: float,
    L: float,
    gamma: float,
    c_u: float,
    H: float | None = None,
    q_surcharge: float = 0.0,
) -> dict:
    """Factor de seguridad contra heave de fondo (Terzaghi & Peck 1967).

    Formulacion clasica para excavaciones soportadas en arcilla:

        FS = Nc · c_u / (gamma · H + q)

    con Nc dependiente de la geometria:

    * Nc = 5.14 para zanja larga (L >> B, plane-strain).
    * Nc = 5.7 · (1 + 0.2 · B/L) para excavacion rectangular/cuadrada
      (Terzaghi-Peck 1967, ec. 11.4).

    Parameters
    ----------
    B, L : float
        Ancho y largo de la excavacion en metros. Si L >= 5·B se usa
        Nc = 5.14 (caso zanja larga).
    gamma : float
        Peso especifico total del suelo retenido (kN/m^3).
    c_u : float
        Resistencia al corte no drenada (kPa). Debe ser > 0.
    H : float, optional
        Profundidad de la excavacion (m). Si se omite se asume H = B
        (valor de referencia cuando la geometria no es conocida).
    q_surcharge : float, default 0
        Sobrecarga uniforme en la superficie adyacente (kPa).

    Returns
    -------
    dict
        ``{"FS", "Nc", "geometry", "driving", "resisting"}``.

    Raises
    ------
    GeotechError
        Si c_u <= 0, gamma <= 0 o dimensiones no positivas.

    References
    ----------
    EN 1997-1 §12; Terzaghi & Peck (1967) §11.
    """
    if c_u <= 0:
        raise GeotechError(
            "c_u debe ser > 0 para evaluar heave en arcilla "
            "(Terzaghi & Peck 1967)."
        )
    if gamma <= 0:
        raise GeotechError("gamma debe ser > 0.")
    if B <= 0 or L <= 0:
        raise GeotechError("Dimensiones B, L deben ser positivas.")

    H_eff = float(H) if H is not None else float(B)
    if H_eff <= 0:
        raise GeotechError("H debe ser > 0.")

    if L >= 5.0 * B:
        Nc = 5.14
        geometry = "strip"
    else:
        Nc = 5.7 * (1.0 + 0.2 * B / L)
        geometry = "rectangular"

    driving = gamma * H_eff + q_surcharge
    resisting = Nc * c_u
    FS = resisting / driving

    return {
        "FS": FS,
        "Nc": Nc,
        "geometry": geometry,
        "driving": driving,
        "resisting": resisting,
        "H": H_eff,
    }


def basal_heave_clay(
    H: float,
    B: float,
    gamma: float,
    c_u: float,
    Nc: float = 5.14,
    q_surcharge: float = 0.0,
) -> dict:
    """FS especifico de basal heave para arcilla blanda (EN 1997-1 §12).

    Modelo simplificado:

        FS = Nc · c_u / (gamma · H + q_surcharge)

    con Nc por defecto 5.14 (zanja larga, Prandtl). Para excavaciones
    rectangulares pasar Nc = 5.7·(1+0.2·B/L).

    Parameters
    ----------
    H : float
        Profundidad de la excavacion (m).
    B : float
        Ancho de la excavacion (m) — usado en chequeos de geometria.
    gamma : float
        Peso especifico total (kN/m^3).
    c_u : float
        Resistencia no drenada (kPa).
    Nc : float, default 5.14
        Factor de capacidad portante para el heave.
    q_surcharge : float, default 0
        Sobrecarga uniforme (kPa).

    Returns
    -------
    dict
        ``{"FS", "Nc", "driving", "resisting"}``.

    Raises
    ------
    GeotechError
        Si parametros no fisicos.

    References
    ----------
    EN 1997-1 §12; Terzaghi & Peck (1967) §11.
    """
    if c_u <= 0:
        raise GeotechError("c_u debe ser > 0.")
    if H <= 0 or B <= 0 or gamma <= 0:
        raise GeotechError("H, B, gamma deben ser positivos.")
    if Nc <= 0:
        raise GeotechError("Nc debe ser > 0.")

    driving = gamma * H + q_surcharge
    resisting = Nc * c_u
    return {
        "FS": resisting / driving,
        "Nc": Nc,
        "driving": driving,
        "resisting": resisting,
    }


# ---------------------------------------------------------------------------
# 2. Diagramas de presion aparente — Peck 1969 / Terzaghi-Peck 1967
# ---------------------------------------------------------------------------
def apparent_earth_pressure(
    H: float,
    gamma: float,
    c_u: float = 0.0,
    soil_type: str = "sand",
    phi: float = 30.0,
    Ka: float | None = None,
) -> dict:
    """Diagramas de presion aparente para paredes soportadas (Peck 1969).

    Envolventes empiricas usadas para dimensionar puntales en cortes
    apuntalados / anclados. Recomendados por EN 1997-1 §12 (Anexo C
    informativo) y aplicados ampliamente en la practica.

    Tipos soportados (``soil_type``):

    * ``"sand"`` — Terzaghi & Peck 1967:
        envolvente rectangular ``p = 0.65 · Ka · gamma · H``.
        Si no se da Ka se calcula Ka = tan^2(45 - phi/2).
    * ``"soft_clay"`` / ``"medium_clay"`` — Peck 1969 para Ns = gamma·H/c_u > 4:
        envolvente rectangular ``p = Kp · gamma · H``,
        Kp = 1 - m · 4 · c_u/(gamma·H); m = 0.4 (soft) o 1.0 (medium).
    * ``"stiff_clay"`` — Peck 1969 para Ns < 4:
        envolvente trapezoidal con pico ``p = 0.2 · gamma · H`` a 0.4·gamma·H
        (se devuelve 0.3·gamma·H como valor representativo, rango
        0.2-0.4 segun rigidez).

    Returns
    -------
    dict
        ``{"shape", "p_max", "Ns", "soil_type", "envelope"}``
        donde ``envelope`` es una lista de pares (z, p) describiendo el
        diagrama.

    Raises
    ------
    GeotechError
        Si H, gamma no positivos, o tipo desconocido, o c_u no positivo
        cuando se requiere.

    References
    ----------
    EN 1997-1 §12; Peck (1969); Terzaghi & Peck (1967).
    """
    if H <= 0 or gamma <= 0:
        raise GeotechError("H y gamma deben ser positivos.")

    st = soil_type.lower().strip()

    if st == "sand":
        if Ka is None:
            if not (0 < phi < 90):
                raise GeotechError("phi fuera de rango (0, 90 deg).")
            Ka = math.tan(math.radians(45.0 - phi / 2.0)) ** 2
        p_max = 0.65 * Ka * gamma * H
        envelope = [(0.0, p_max), (H, p_max)]
        return {
            "shape": "rectangular",
            "p_max": p_max,
            "Ka": Ka,
            "Ns": None,
            "soil_type": "sand",
            "envelope": envelope,
        }

    if st in ("soft_clay", "medium_clay"):
        if c_u <= 0:
            raise GeotechError(
                "c_u > 0 requerido para envolvente en arcilla."
            )
        Ns = gamma * H / c_u
        m = 0.4 if st == "soft_clay" else 1.0
        Kp = max(0.0, 1.0 - m * 4.0 * c_u / (gamma * H))
        p_max = Kp * gamma * H
        envelope = [(0.0, p_max), (H, p_max)]
        return {
            "shape": "rectangular",
            "p_max": p_max,
            "Kp": Kp,
            "m": m,
            "Ns": Ns,
            "soil_type": st,
            "envelope": envelope,
        }

    if st == "stiff_clay":
        if c_u <= 0:
            raise GeotechError(
                "c_u > 0 requerido para envolvente en arcilla rigida."
            )
        Ns = gamma * H / c_u
        # Trapezoidal: 0 en cabeza y pie (zonas de 0.25H), constante en medio
        p_max = 0.3 * gamma * H  # rango Peck 0.2 - 0.4
        envelope = [
            (0.0, 0.0),
            (0.25 * H, p_max),
            (0.75 * H, p_max),
            (H, 0.0),
        ]
        return {
            "shape": "trapezoidal",
            "p_max": p_max,
            "Ns": Ns,
            "soil_type": "stiff_clay",
            "envelope": envelope,
        }

    raise GeotechError(
        f"soil_type desconocido: {soil_type!r}. "
        "Use 'sand', 'soft_clay', 'medium_clay' o 'stiff_clay'."
    )


# ---------------------------------------------------------------------------
# 3. Fuerzas en puntales — metodo tributario
# ---------------------------------------------------------------------------
def strut_force(
    pressure_diagram: dict,
    levels: Sequence[float],
    spacing: float = 1.0,
) -> list[dict]:
    """Fuerzas en puntales (struts) por el metodo de areas tributarias.

    Cada puntal recibe la carga del trozo de envolvente comprendido entre
    los puntos medios a sus vecinos (areas tributarias). Es el procedimiento
    recomendado por Peck (1969) y EN 1997-1 §12 para diseno preliminar.

    Parameters
    ----------
    pressure_diagram : dict
        Resultado de :func:`apparent_earth_pressure` con clave
        ``"envelope"`` = lista de pares ``(z, p)``.
    levels : sequence of float
        Profundidades (m) de los puntales medidas desde la cabeza de la
        pared (z = 0 arriba, z = H abajo). Deben estar ordenadas
        ascendentemente y dentro del rango [0, H].
    spacing : float, default 1.0
        Separacion horizontal entre paneles tributarios (m). La fuerza
        devuelta es por puntal individual.

    Returns
    -------
    list of dict
        Un dict por puntal: ``{"z", "z_top", "z_bot", "force"}``
        donde ``force`` esta en kN (si p en kPa y dimensiones en m).

    Raises
    ------
    GeotechError
        Si ``levels`` esta vacio, no es monotonico, o esta fuera de rango.

    References
    ----------
    EN 1997-1 §12; Peck (1969); Terzaghi & Peck (1967).
    """
    envelope = pressure_diagram.get("envelope")
    if not envelope:
        raise GeotechError("pressure_diagram sin 'envelope'.")
    lv = list(levels)
    if not lv:
        raise GeotechError("Se requiere al menos un nivel de puntal.")
    if any(lv[i] >= lv[i + 1] for i in range(len(lv) - 1)):
        raise GeotechError("levels debe ser estrictamente creciente.")

    H = max(z for z, _ in envelope)
    if lv[0] < 0 or lv[-1] > H:
        raise GeotechError("levels fuera del rango [0, H].")
    if spacing <= 0:
        raise GeotechError("spacing debe ser > 0.")

    # Limites tributarios: midpoints entre puntales; bordes 0 y H.
    bounds = [0.0]
    for i in range(len(lv) - 1):
        bounds.append(0.5 * (lv[i] + lv[i + 1]))
    bounds.append(H)

    results = []
    for i, z in enumerate(lv):
        z_top = bounds[i]
        z_bot = bounds[i + 1]
        area = _integrate_envelope(envelope, z_top, z_bot)
        force = area * spacing
        results.append(
            {
                "z": z,
                "z_top": z_top,
                "z_bot": z_bot,
                "force": force,
            }
        )
    return results


def _integrate_envelope(
    envelope: Sequence[tuple[float, float]],
    z_a: float,
    z_b: float,
) -> float:
    """Integra la envolvente p(z) entre z_a y z_b (regla del trapecio)."""
    if z_b <= z_a:
        return 0.0
    # Construir lista de nodos relevantes (vertices de la envolvente + z_a, z_b)
    pts = sorted({z for z, _ in envelope} | {z_a, z_b})
    pts = [z for z in pts if z_a <= z <= z_b]
    area = 0.0
    for i in range(len(pts) - 1):
        za, zb = pts[i], pts[i + 1]
        pa = _interp_envelope(envelope, za)
        pb = _interp_envelope(envelope, zb)
        area += 0.5 * (pa + pb) * (zb - za)
    return area


def _interp_envelope(
    envelope: Sequence[tuple[float, float]], z: float
) -> float:
    """Interpolacion lineal en una envolvente piecewise-linear."""
    pts = list(envelope)
    if z <= pts[0][0]:
        return pts[0][1]
    if z >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        z0, p0 = pts[i]
        z1, p1 = pts[i + 1]
        if z0 <= z <= z1:
            if z1 == z0:
                return p1
            t = (z - z0) / (z1 - z0)
            return p0 + t * (p1 - p0)
    return pts[-1][1]
