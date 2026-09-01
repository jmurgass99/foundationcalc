"""Servicios de diseño de zapatas."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IsolatedFootingInput:
    """Inputs para diseño de zapata aislada.

    Unidades SI: m para dimensiones, kN para cargas, kPa para presiones.
    """
    L_x: float            # longitud zapata en X (m)
    L_y: float            # longitud zapata en Y (m)
    thickness: float      # peralte (m)
    depth: float = 1.0    # profundidad de cimentación (m)
    column_b: float = 0.4
    column_h: float = 0.4
    fc_MPa: float = 25.0
    fy_MPa: float = 420.0
    cover_mm: float = 50.0
    N: float = 1000.0     # axial (kN, + compresión)
    M_x: float = 0.0      # momento eje X (kN·m)
    M_y: float = 0.0      # momento eje Y (kN·m)
    V_x: float = 0.0
    V_y: float = 0.0
    q_allow_kPa: float = 200.0


@dataclass(frozen=True)
class FootingDesignResult:
    """Resultado del diseño de una zapata aislada."""
    pressures: dict       # {q_max, q_min, q_avg, biaxial corner pressures}
    punching: dict        # {Vu, Vc, DCR, perimeter, governs}
    flexure_x: dict       # {Mu, As_required, As_min, As_chosen, bar_spacing}
    flexure_y: dict
    settlements_mm: float | None = None
    notes: list[str] = field(default_factory=list)


def design_isolated_footing(inp: IsolatedFootingInput) -> FootingDesignResult:
    """Diseña una zapata aislada: presiones de contacto + punzonamiento + flexión.

    API pública del service layer (headless). Devuelve un ViewModel inmutable
    apto para JSON, HTML y reportes PDF. Implementación analítica directa
    (no depende de un módulo `design/isolated_footing.py`, que no existe):

    - **Presiones**: elástico con verificación de núcleo (kern). Si la
      excentricidad cae fuera del núcleo, se modela despegue (contacto parcial,
      sin tensión), no presiones negativas no físicas.
    - **Punzonamiento**: cortante bidireccional ACI 318-19 §22.6.5.2 (mínimo de
      las 3 ecuaciones de Vc, perímetro crítico a d/2, φ=0.75).
    - **Flexión**: voladizo en la cara de columna (estática), As por bloque
      rectangular ACI.
    """
    return _simplified_design(inp)


def _compute_pressures(inp: IsolatedFootingInput) -> tuple[dict, list[str]]:
    """Presiones de contacto suelo-zapata (nivel de servicio).

    Convención de ejes: ``e_x`` (excentricidad a lo largo de L_x) = M_y/N;
    ``e_y`` (a lo largo de L_y) = M_x/N.

    - Dentro del núcleo (|e_x|/L_x + |e_y|/L_y ≤ 1/6): contacto total, fórmula
      elástica biaxial q = (N/A)(1 ± 6e_x/L_x ± 6e_y/L_y); todas las esquinas en
      compresión, así que ``q_min`` es físicamente válido.
    - Fuera del núcleo con excentricidad uniaxial: despegue (lift-off). El bloque
      de presión es triangular: ``q_max = 2N/(3·B·(L/2 − e))``, ``q_min = 0``.
    - Fuera del núcleo biaxial: sin solución cerrada (problema sin tensión
      iterativo); se reporta ``q_max`` elástico con ``q_min`` recortado a 0 y una
      nota de advertencia para redimensionar.
    """
    Ag = inp.L_x * inp.L_y
    N = inp.N
    q_avg = N / Ag if Ag > 0 else 0.0
    e_x = (inp.M_y / N) if N > 0 else 0.0      # excentricidad a lo largo de L_x
    e_y = (inp.M_x / N) if N > 0 else 0.0      # excentricidad a lo largo de L_y
    ax, ay = abs(e_x), abs(e_y)
    tol = 1e-9
    notes: list[str] = []
    in_kern = (ax / inp.L_x + ay / inp.L_y) <= (1.0 / 6.0) + 1e-12

    if in_kern:
        q_max = q_avg * (1 + 6 * ax / inp.L_x + 6 * ay / inp.L_y)
        q_min = q_avg * (1 - 6 * ax / inp.L_x - 6 * ay / inp.L_y)
        contact = "full"
    elif ay <= tol < ax:
        # despegue uniaxial a lo largo de L_x (ancho resistente B = L_y)
        m = inp.L_x / 2.0 - ax
        q_max = (2 * N / (3 * inp.L_y * m)) if m > tol else float("inf")
        q_min, contact = 0.0, "partial-x"
        notes.append("Despegue uniaxial (e_x > L_x/6): bloque triangular de "
                     "presión, q_min = 0.")
    elif ax <= tol < ay:
        # despegue uniaxial a lo largo de L_y (ancho resistente B = L_x)
        m = inp.L_y / 2.0 - ay
        q_max = (2 * N / (3 * inp.L_x * m)) if m > tol else float("inf")
        q_min, contact = 0.0, "partial-y"
        notes.append("Despegue uniaxial (e_y > L_y/6): bloque triangular de "
                     "presión, q_min = 0.")
    else:
        # biaxial fuera del núcleo: aproximación conservadora + advertencia
        q_max = q_avg * (1 + 6 * ax / inp.L_x + 6 * ay / inp.L_y)
        q_min, contact = 0.0, "partial-biaxial"
        notes.append("Carga biaxial fuera del núcleo (despegue en esquina): el "
                     "modelo elástico no es válido; q_max es aproximado. "
                     "Redimensionar la zapata o usar análisis sin tensión.")
    if not (q_max < float("inf")):
        notes.append("Excentricidad ≥ L/2: resultante fuera de la base "
                     "(vuelco); presión no acotada.")
    return ({"q_max": q_max, "q_min": q_min, "q_avg": q_avg,
             "e_x": e_x, "e_y": e_y, "contact": contact}, notes)


def _punching_aci318(inp: IsolatedFootingInput, q_avg: float) -> dict:
    """Cortante bidireccional (punzonamiento), ACI 318-19 §22.6.5.2.

    Perímetro crítico ``bo`` a d/2 de la cara (columna interior, rectangular):
        bo = 2(c1 + d) + 2(c2 + d)
    Resistencia ``Vc`` = mínimo de las tres ecuaciones (λ=1, normalweight):
        a) 0.33·λ·√f'c·bo·d
        b) 0.17·(1 + 2/βc)·λ·√f'c·bo·d            βc = lado largo/corto col.
        c) 0.083·(2 + αs·d/bo)·λ·√f'c·bo·d         αs = 40 (interior)
    Demanda ``Vu`` = N − q·(c1+d)(c2+d) (cortante directo neto; NO incluye
    transferencia de momento desbalanceado γv·M). φ = 0.75 (ACI 21.2).
    Unidades internas: MPa, mm, N → se devuelven Vu/Vc/φVc en kN.
    """
    import math
    lam, alpha_s, phi = 1.0, 40.0, 0.75
    c1, c2 = inp.column_b, inp.column_h
    d = max(inp.thickness - inp.cover_mm / 1000.0, 1e-3)        # m
    d_mm = d * 1000.0
    bo_mm = (2 * (c1 + d) + 2 * (c2 + d)) * 1000.0             # mm
    beta_c = (max(c1, c2) / min(c1, c2)) if min(c1, c2) > 0 else 1.0
    sq = math.sqrt(max(inp.fc_MPa, 0.0))
    Vc_a = 0.33 * lam * sq * bo_mm * d_mm
    Vc_b = 0.17 * (1.0 + 2.0 / beta_c) * lam * sq * bo_mm * d_mm
    Vc_c = 0.083 * (2.0 + alpha_s * d_mm / bo_mm) * lam * sq * bo_mm * d_mm
    options = [
        ("two-way: basic 0.33·√f'c", Vc_a),
        ("two-way: beta_c 0.17·(1+2/βc)·√f'c", Vc_b),
        ("two-way: alpha_s 0.083·(2+αs·d/bo)·√f'c", Vc_c),
    ]
    governs, Vc_N = min(options, key=lambda kv: kv[1])
    Vc = Vc_N / 1000.0                                          # kN
    phiVc = phi * Vc
    A_crit = (c1 + d) * (c2 + d)                               # m² dentro de bo
    Vu = max(inp.N - q_avg * A_crit, 0.0)                     # kN
    return {
        "Vu": Vu, "Vc": Vc, "phiVc": phiVc, "phi": phi,
        "DCR": (Vu / phiVc) if phiVc > 0 else float("inf"),
        "bo_m": bo_mm / 1000.0, "d_m": d, "beta_c": beta_c,
        "alpha_s": alpha_s, "governs": governs,
    }


def _simplified_design(inp: IsolatedFootingInput) -> FootingDesignResult:
    """Diseño analítico de la zapata aislada (service layer headless).

    Combina :func:`_compute_pressures` (con chequeo de núcleo y despegue),
    :func:`_punching_aci318` (ACI 318-19) y :func:`_cantilever_flexure`. Trata
    ``N`` como axial mayorada (Pu), consistente con la convención de flexión
    (el voladizo produce un ``Mu`` directamente del ``q_max``).
    """
    pressures, p_notes = _compute_pressures(inp)
    punching = _punching_aci318(inp, pressures["q_avg"])
    q_flex = pressures["q_max"]                  # conservador para flexión
    flex_x = _cantilever_flexure(q_flex, width=inp.L_y, span=inp.L_x,
                                 col=inp.column_b, inp=inp)
    flex_y = _cantilever_flexure(q_flex, width=inp.L_x, span=inp.L_y,
                                 col=inp.column_h, inp=inp)
    notes = [
        "Diseño analítico: presión elástica con chequeo de núcleo (sin tensión), "
        "punzonamiento ACI 318-19 §22.6.5.2 (mín. de 3 ec. de Vc, φ=0.75), "
        "flexión = voladizo en cara de columna (bloque rectangular ACI).",
        "N tratado como axial mayorada (Pu); Vu de punzonamiento es cortante "
        "directo neto (sin transferencia de momento γv·M).",
        f"q_max = {pressures['q_max']:.1f} kPa (adm {inp.q_allow_kPa:.0f} kPa); "
        f"punching DCR = {punching['DCR']:.2f}.",
    ]
    if pressures["contact"] != "full":
        notes.append(
            "Flexión bajo despegue: Mu calculado con q_max en ambas caras "
            "(conservador; el lado de baja presión real produce menos momento). "
            "Refinar lado-a-lado en una iteración futura.")
    notes.extend(p_notes)
    return FootingDesignResult(
        pressures=pressures, punching=punching,
        flexure_x=flex_x, flexure_y=flex_y, notes=notes,
    )


def _cantilever_flexure(q_kPa: float, width: float, span: float, col: float,
                        inp: IsolatedFootingInput) -> dict:
    """Diseño a flexión de una franja de zapata en voladizo (ACI 318).

    El voladizo proyecta ``l = (span - col)/2`` desde la cara de columna; la
    presión ``q`` actúa hacia arriba sobre él. Momento en la cara de columna:
        Mu = q · width · l² / 2        [kN·m]   (estática, sin ambigüedad)
    As por bloque rectangular equivalente (φ=0.9); As_min ACI 7.6.1.1.
    Unidades internas N/mm/MPa; retorna Mu [kN·m] y As [mm²].
    """
    import math
    l = max((span - col) / 2.0, 0.0)                 # m, proyección del voladizo
    Mu = q_kPa * width * l * l / 2.0                 # kN·m
    b = width * 1000.0                               # mm, ancho de la franja
    h = inp.thickness * 1000.0                       # mm, peralte total
    d = max(h - inp.cover_mm, 1.0)                   # mm, peralte efectivo
    fc, fy, phi = inp.fc_MPa, inp.fy_MPa, 0.9
    As_req = 0.0
    if Mu > 0 and fc > 0 and fy > 0:
        Rn = (Mu * 1e6) / (phi * b * d * d)          # MPa
        disc = max(1.0 - 2.0 * Rn / (0.85 * fc), 0.0)  # <0 ⇒ sección chica; tope
        rho = (0.85 * fc / fy) * (1.0 - math.sqrt(disc))
        As_req = rho * b * d                         # mm²
    # As_min flexión (ACI 7.6.1.1 / temp. y retracción), escalado por fy.
    As_min = max(0.0018 * 420.0 / fy, 0.0014) * b * h if fy > 0 else 0.0
    As_chosen = max(As_req, As_min)
    # Espaciamiento con barras #5 (As=200 mm²), tope ACI = min(3h, 450 mm).
    n_bars = max(2, math.ceil(As_chosen / 200.0)) if As_chosen > 0 else 2
    clear = max(b - 2.0 * inp.cover_mm, 1.0)
    spacing_mm = min(clear / (n_bars - 1) if n_bars > 1 else clear, 3.0 * h, 450.0)
    return {
        "Mu": Mu,                                    # kN·m
        "As_required": As_req,                       # mm²
        "As_min": As_min,                            # mm²
        "As_chosen": As_chosen,                      # mm²
        "bar_spacing": spacing_mm / 1000.0,          # m
    }


@dataclass(frozen=True)
class FootingCandidate:
    L_x: float
    L_y: float
    thickness: float
    cost_eur: float
    passes_all: bool
    q_max_kPa: float
    q_allow_kPa: float
    punching_dcr: float
    flexure_x_As: float
    flexure_y_As: float
    failure_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FootingOptimizationResult:
    best_candidate: FootingCandidate
    all_evaluated_candidates: list[FootingCandidate]
    total_evaluated: int
    total_passed: int


def optimize_isolated_footing_discrete_grid(
    N_kN: float,
    q_allow_kPa: float,
    M_x_kNm: float = 0.0,
    M_y_kNm: float = 0.0,
    column_b: float = 0.40,
    column_h: float = 0.40,
    fc_MPa: float = 25.0,
    fy_MPa: float = 420.0,
    cover_mm: float = 50.0,
    L_x_grid: list[float] | None = None,
    L_y_grid: list[float] | None = None,
    thickness_grid: list[float] | None = None,
    unit_cost_concrete_eur_m3: float = 120.0,
    unit_cost_steel_eur_kg: float = 1.80,
    unit_cost_formwork_eur_m2: float = 35.0,
) -> FootingOptimizationResult:
    """Optimiza zapata aislada barriendo planta y canto en malla discreta al mínimo coste."""
    import math

    lx_vals = L_x_grid or [1.2, 1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0]
    ly_vals = L_y_grid or [1.2, 1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0]
    h_vals = thickness_grid or [0.40, 0.50, 0.60, 0.70, 0.80]

    all_candidates: list[FootingCandidate] = []
    best_candidate: FootingCandidate | None = None
    min_cost = float("inf")

    for lx in lx_vals:
        for ly in ly_vals:
            for h in h_vals:
                inp = IsolatedFootingInput(
                    L_x=lx,
                    L_y=ly,
                    thickness=h,
                    column_b=column_b,
                    column_h=column_h,
                    fc_MPa=fc_MPa,
                    fy_MPa=fy_MPa,
                    cover_mm=cover_mm,
                    N=N_kN,
                    M_x=M_x_kNm,
                    M_y=M_y_kNm,
                    q_allow_kPa=q_allow_kPa,
                )
                res = design_isolated_footing(inp)

                # Comprobaciones
                failures: list[str] = []
                # Acceso por clave, NO con .get(..., 0.0): un valor ausente se
                # convertia en 0.0 y por tanto en un estado limite APROBADO
                # (0 > q_adm es falso, 0 > 1.0 es falso). Si la clave faltase, un
                # KeyError ruidoso es infinitamente preferible a una zapata que
                # pasa las comprobaciones por no haberlas hecho. Hoy las tres
                # ramas de _compute_pressures y _punching_aci318 devuelven
                # siempre la clave, asi que esto no cambia ningun resultado: lo
                # que cambia es que dejaria de ser silencioso si algun dia
                # cambian.
                q_max = res.pressures["q_max"]
                if q_max > q_allow_kPa:
                    failures.append(f"Tensión excesiva: q_max={q_max:.1f} > q_adm={q_allow_kPa:.1f} kPa")

                p_dcr = res.punching["DCR"]
                if p_dcr > 1.0:
                    failures.append(f"Falla punzonamiento: DCR={p_dcr:.2f} > 1.0")

                as_x = res.flexure_x["As_chosen"]
                as_y = res.flexure_y["As_chosen"]

                # Cómputo de costes
                vol_conc = lx * ly * h
                area_form = 2.0 * (lx + ly) * h
                # Acero en kg con densidad 7850 kg/m³
                w_steel_kg = ((as_x * 1e-6 * (lx + 0.6)) + (as_y * 1e-6 * (ly + 0.6))) * 7850.0

                cost = (
                    vol_conc * unit_cost_concrete_eur_m3
                    + w_steel_kg * unit_cost_steel_eur_kg
                    + area_form * unit_cost_formwork_eur_m2
                )

                passes = len(failures) == 0
                cand = FootingCandidate(
                    L_x=lx,
                    L_y=ly,
                    thickness=h,
                    cost_eur=cost,
                    passes_all=passes,
                    q_max_kPa=q_max,
                    q_allow_kPa=q_allow_kPa,
                    punching_dcr=p_dcr,
                    flexure_x_As=as_x,
                    flexure_y_As=as_y,
                    failure_reasons=failures,
                )
                all_candidates.append(cand)

                if passes and cost < min_cost:
                    min_cost = cost
                    best_candidate = cand

    if best_candidate is None:
        raise ValueError("Ninguna combinación en la malla discreta satisface los chequeos de diseño.")

    passed_count = sum(1 for c in all_candidates if c.passes_all)
    return FootingOptimizationResult(
        best_candidate=best_candidate,
        all_evaluated_candidates=all_candidates,
        total_evaluated=len(all_candidates),
        total_passed=passed_count,
    )


__all__ = [
    "IsolatedFootingInput",
    "FootingDesignResult",
    "FootingCandidate",
    "FootingOptimizationResult",
    "design_isolated_footing",
    "optimize_isolated_footing_discrete_grid",
]

