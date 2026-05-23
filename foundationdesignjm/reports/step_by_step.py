"""
step_by_step.py — Bloques narrados paso a paso para la memoria de cálculo.

Toma los outputs de los módulos `fastsap.codes.*` (cada uno expone un
dict / dataclass con un campo ``notes: list[str]`` que ya describe el
cálculo) y los traduce a estructuras estandarizadas para ser
renderizadas en el PDF de la memoria.

Patrón de uso típico::

    from fastsap.codes.aisc_358 import rbs_design
    from fastsap.reports.step_by_step import rbs_step_block, render_block_pdf

    rbs_result = rbs_design(Zx=3.21e6, Fy=345.0, d_beam=611.0, ...)
    block = rbs_step_block(rbs_result, element_id="BEAM-301")
    render_block_pdf(rep, block)        # rep es el Report del pdf_builder

Para integrarlo en la memoria maestra se pasa una lista de StepBlock al
``MemoriaBuilder.with_step_block(...)`` y ``build_master_memoria`` los
emite como sección 14.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

@dataclass
class StepRecord:
    """Una línea de cálculo paso-a-paso."""
    description: str       # qué se calcula
    formula:     str       # fórmula simbólica (texto)
    substitution: str      # sustitución numérica (texto)
    result:      str       # valor final (con unidades)
    code_ref:    str = ""  # sección normativa, ej. "ACI 18.7.5.4"
    status:      str = ""  # "OK", "FAIL", "INFO" (opcional)


@dataclass
class StepBlock:
    """Conjunto de StepRecord que componen un chequeo completo."""
    title:        str      # ej. "Conexión RBS — BEAM-301"
    code_ref:     str      # ej. "AISC 358-22 Ch. 5"
    inputs_kv:    list[tuple[str, str]] = field(default_factory=list)
    steps:        list[StepRecord] = field(default_factory=list)
    summary_table: Optional[pd.DataFrame] = None
    conclusion:   str = ""
    ok:           Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers de parseo
# ---------------------------------------------------------------------------

def _split_note(note: str) -> tuple[str, str, str]:
    """Heurística: parte una línea ``notes`` en (formula, substitution, result).

    Formato canónico esperado en nuestros módulos:
        "<formula> = <substitution> = <result>"
    Si no hay dos '=', devuelve (note, "", "").
    """
    if note.count("=") >= 2:
        left, mid, right = note.split("=", 2)
        return left.strip(), mid.strip(), right.strip()
    if "=" in note:
        left, right = note.split("=", 1)
        return left.strip(), "", right.strip()
    return note.strip(), "", ""


def _status_from_ok(ok: Optional[bool]) -> str:
    if ok is None:
        return "INFO"
    return "OK" if ok else "FAIL"


# ---------------------------------------------------------------------------
# Renderers específicos por tipo de cálculo
# ---------------------------------------------------------------------------

def rbs_step_block(result: dict, element_id: str = "RBS") -> StepBlock:
    """Renderiza el output de ``aisc_358.rbs_design`` como StepBlock."""
    inp = result.get("inputs", {})
    geom = result.get("geometry", {})
    inputs_kv = [
        ("Z_x viga (mm³)",       f"{inp.get('Zx', 0):.3e}"),
        ("F_y (MPa)",            f"{inp.get('Fy', 0):.0f}"),
        ("F_u (MPa)",            f"{inp.get('Fu', 0):.0f}"),
        ("R_y",                  f"{inp.get('Ry', 0):.2f}"),
        ("d viga (mm)",          f"{inp.get('d_beam', 0):.0f}"),
        ("bf viga (mm)",         f"{inp.get('bf_beam', 0):.0f}"),
        ("tf viga (mm)",         f"{inp.get('tf_beam', 0):.0f}"),
        ("L viga (mm)",          f"{inp.get('Lbeam', 0):.0f}"),
        ("V_gravity (N)",        f"{inp.get('Vgravity', 0):.0f}"),
    ]
    steps = [
        StepRecord(
            "Geometría RBS — distancia desde columna",
            "a = a_factor · b_f",
            f"a = 0.625 · {inp.get('bf_beam',0):.0f}",
            f"{geom.get('a', 0):.1f} mm",
            code_ref="AISC 358 §5.8 Step 1",
        ),
        StepRecord(
            "Longitud del corte RBS",
            "b = b_factor · d",
            f"b = 0.75 · {inp.get('d_beam',0):.0f}",
            f"{geom.get('b', 0):.1f} mm",
            code_ref="AISC 358 §5.8 Step 1",
        ),
        StepRecord(
            "Profundidad del corte",
            "c = c_factor · b_f",
            f"c = 0.20 · {inp.get('bf_beam',0):.0f}",
            f"{geom.get('c', 0):.1f} mm",
            code_ref="AISC 358 §5.8 Step 1",
        ),
        StepRecord(
            "Módulo plástico en el centro del corte",
            "Z_RBS = Z_x − 2 c t_f (d − t_f)",
            f"Z_RBS = {inp.get('Zx',0):.3e} − 2·{geom.get('c',0):.1f}·{inp.get('tf_beam',0):.1f}·({inp.get('d_beam',0):.0f}−{inp.get('tf_beam',0):.1f})",
            f"{result.get('Z_RBS', 0):.3e} mm³",
            code_ref="AISC 358 Eq. 5.8-4",
        ),
        StepRecord(
            "Factor C_pr",
            "C_pr = min((F_y+F_u)/(2F_y), 1.20)",
            f"C_pr = ({inp.get('Fy',0):.0f}+{inp.get('Fu',0):.0f})/(2·{inp.get('Fy',0):.0f})",
            f"{result.get('Cpr', 0):.3f}",
            code_ref="AISC 358 Eq. 2.4.3-2",
        ),
        StepRecord(
            "Momento probable en el centro del RBS",
            "M_pr = C_pr · R_y · F_y · Z_RBS",
            f"M_pr = {result.get('Cpr',0):.3f}·{inp.get('Ry',0):.2f}·{inp.get('Fy',0):.0f}·{result.get('Z_RBS',0):.3e}",
            f"{result.get('Mpr', 0)/1e6:.1f} kN·m",
            code_ref="AISC 358 Eq. 5.8-5",
        ),
        StepRecord(
            "Cortante en la rótula plástica",
            "V_h = 2 M_pr / L_h + V_g",
            f"V_h = 2·{result.get('Mpr',0)/1e6:.1f}·1000 / {geom.get('Lh',1):.0f} + {inp.get('Vgravity',0)/1e3:.1f}",
            f"{result.get('Vh', 0)/1e3:.1f} kN",
            code_ref="AISC 358 §5.8 Step 5",
        ),
        StepRecord(
            "Momento en la cara de la columna",
            "M_f = M_pr + V_h · S_h",
            f"M_f = {result.get('Mpr',0)/1e6:.1f} + {result.get('Vh',0)/1e3:.1f}·{geom.get('Sh',0)/1000:.3f}",
            f"{result.get('Mf', 0)/1e6:.1f} kN·m",
            code_ref="AISC 358 Eq. 5.8-6",
        ),
        StepRecord(
            "Verificación M_f ≤ M_pe (columna-fuerte / viga-débil)",
            "M_f / M_pe ≤ 1.0",
            f"{result.get('Mf_over_Mpe', 0):.3f} ≤ 1.0",
            "OK" if result.get('checks', {}).get('Mf_le_Mpe') else "FAIL",
            code_ref="AISC 358 §5.8",
            status="OK" if result.get('checks', {}).get('Mf_le_Mpe') else "FAIL",
        ),
    ]
    summary = pd.DataFrame([
        {"Magnitud": "M_pr", "Valor": f"{result.get('Mpr',0)/1e6:.1f} kN·m"},
        {"Magnitud": "V_h",  "Valor": f"{result.get('Vh',0)/1e3:.1f} kN"},
        {"Magnitud": "M_f",  "Valor": f"{result.get('Mf',0)/1e6:.1f} kN·m"},
        {"Magnitud": "M_pe", "Valor": f"{result.get('Mpe',0)/1e6:.1f} kN·m"},
        {"Magnitud": "M_f / M_pe", "Valor": f"{result.get('Mf_over_Mpe',0):.3f}"},
    ])
    return StepBlock(
        title=f"Conexión RBS — {element_id}",
        code_ref="AISC 358-22 Cap. 5",
        inputs_kv=inputs_kv,
        steps=steps,
        summary_table=summary,
        conclusion=("La conexión satisface los criterios de capacidad de "
                    "diseño de AISC 358-22 Cap. 5." if result.get('ok')
                    else "La conexión NO cumple uno o más chequeos; revisar."),
        ok=result.get('ok'),
    )


def asce7_base_shear_step_block(
    spectrum,
    cs_result,
    base_shear_result: dict,
    Ie: float = 1.0,
    Ta_s: Optional[float] = None,
) -> StepBlock:
    """Renderiza el cálculo de cortante basal ASCE 7-22 §11.4 + §12.8."""
    sp = spectrum
    cs = cs_result
    inputs_kv = [
        ("Ss (g)",          f"{sp.Ss:.2f}"),
        ("S1 (g)",          f"{sp.S1:.2f}"),
        ("Site Class",      sp.site_class),
        ("F_a",             f"{sp.Fa:.2f}"),
        ("F_v",             f"{sp.Fv:.2f}"),
        ("Importancia I_e", f"{Ie:.2f}"),
    ]
    if Ta_s is not None:
        inputs_kv.append(("T_a aproximado (s)", f"{Ta_s:.3f}"))

    steps = [
        StepRecord("Aceleración MCE_R corto período",
                   "S_MS = F_a · S_s",
                   f"S_MS = {sp.Fa:.2f}·{sp.Ss:.2f}",
                   f"{sp.SMS:.3f} g",
                   code_ref="ASCE 7-22 Eq. 11.4-1"),
        StepRecord("Aceleración MCE_R 1-segundo",
                   "S_M1 = F_v · S_1",
                   f"S_M1 = {sp.Fv:.2f}·{sp.S1:.2f}",
                   f"{sp.SM1:.3f} g",
                   code_ref="ASCE 7-22 Eq. 11.4-2"),
        StepRecord("Aceleración de diseño corto período",
                   "S_DS = (2/3) S_MS",
                   f"S_DS = (2/3)·{sp.SMS:.3f}",
                   f"{sp.SDS:.3f} g",
                   code_ref="ASCE 7-22 Eq. 11.4-3"),
        StepRecord("Aceleración de diseño 1-segundo",
                   "S_D1 = (2/3) S_M1",
                   f"S_D1 = (2/3)·{sp.SM1:.3f}",
                   f"{sp.SD1:.3f} g",
                   code_ref="ASCE 7-22 Eq. 11.4-4"),
        StepRecord("Coeficiente de respuesta sísmica",
                   "C_s (con caps y floors)",
                   f"governing: {cs.governing}",
                   f"{cs.Cs:.4f}",
                   code_ref="ASCE 7-22 §12.8.1.1"),
        StepRecord("Cortante basal",
                   "V = C_s · W",
                   f"V = {cs.Cs:.4f} · {base_shear_result.get('W_kN',0):.0f}",
                   f"{base_shear_result.get('V_kN',0):.1f} kN",
                   code_ref="ASCE 7-22 Eq. 12.8-1",
                   status="INFO"),
    ]
    summary = pd.DataFrame([
        {"Parámetro": "S_DS", "Valor": f"{sp.SDS:.3f} g"},
        {"Parámetro": "S_D1", "Valor": f"{sp.SD1:.3f} g"},
        {"Parámetro": "T_s",  "Valor": f"{sp.Ts:.3f} s"},
        {"Parámetro": "C_s",  "Valor": f"{cs.Cs:.4f}"},
        {"Parámetro": "V",    "Valor": f"{base_shear_result.get('V_kN',0):.1f} kN"},
    ])
    return StepBlock(
        title="Cortante basal sísmico (ASCE 7-22 §12.8)",
        code_ref="ASCE 7-22 §11.4 + §12.8",
        inputs_kv=inputs_kv,
        steps=steps,
        summary_table=summary,
        conclusion=(f"Cortante basal de diseño V = {base_shear_result.get('V_kN',0):.1f} kN, "
                    f"gobernado por {cs.governing}."),
        ok=True,
    )


def ec8_beam_capacity_step_block(result, element_id: str = "BEAM") -> StepBlock:
    """Renderiza ``ec8_capacity_design.beam_capacity_shear`` como StepBlock."""
    inputs_kv = [
        ("Clase de ductilidad",     result.ductility_class),
        ("γ_Rd",                    f"{result.gamma_Rd:.2f}"),
        ("V_gravity (kN)",          f"{result.V_gravity_kN:.1f}"),
    ]
    steps = [
        StepRecord("Cortante por sismo + dirección (+)",
                   "V_Ed,+ = γ_Rd·(M_Rb,L_pos + M_Rb,R_neg)/L_cl + V_g",
                   "(ver notas del cálculo)",
                   f"{result.V_Ed_pos_kN:.1f} kN",
                   code_ref="EN 1998-1 §5.4.2.2"),
        StepRecord("Cortante por sismo − dirección (−)",
                   "V_Ed,− = γ_Rd·(M_Rb,L_neg + M_Rb,R_pos)/L_cl + V_g",
                   "(ver notas del cálculo)",
                   f"{result.V_Ed_neg_kN:.1f} kN",
                   code_ref="EN 1998-1 §5.4.2.2"),
        StepRecord("Envolvente |V_Ed| de diseño",
                   "|V_Ed| = max(|V_Ed,+|, |V_Ed,−|)",
                   f"max({abs(result.V_Ed_pos_kN):.1f}, {abs(result.V_Ed_neg_kN):.1f})",
                   f"{result.V_Ed_envelope_kN:.1f} kN",
                   code_ref="EN 1998-1 §5.4.2.2",
                   status="INFO"),
    ]
    return StepBlock(
        title=f"V_Ed capacity-design — {element_id}",
        code_ref="EN 1998-1 §5.4.2.2",
        inputs_kv=inputs_kv,
        steps=steps,
        conclusion=("V_Ed de diseño obtenido por capacidad. "
                    "Se diseñará el refuerzo transversal para este valor."),
        ok=True,
    )


def aci_scwb_step_block(result: dict, joint_id: str = "JOINT") -> StepBlock:
    """Strong-column-weak-beam ACI 318 §18.7.3 — render."""
    inputs_kv = [
        ("Σ M_nc (kN·m)", f"{result['sum_Mnc_kNm']:.1f}"),
        ("Σ M_nb (kN·m)", f"{result['sum_Mnb_kNm']:.1f}"),
    ]
    steps = [
        StepRecord("Ratio columna/viga",
                   "Σ M_nc / Σ M_nb",
                   f"{result['sum_Mnc_kNm']:.1f}/{result['sum_Mnb_kNm']:.1f}",
                   f"{result['ratio']:.3f}",
                   code_ref="ACI 18.7.3.2"),
        StepRecord("Demanda mínima",
                   "Σ M_nc ≥ (6/5) Σ M_nb",
                   f"Σ M_nc ≥ 1.20 · {result['sum_Mnb_kNm']:.1f}",
                   f"{result['demand_kNm']:.1f} kN·m",
                   code_ref="ACI 18.7.3.2"),
        StepRecord("Verificación SCWB",
                   "ratio ≥ 1.20",
                   f"{result['ratio']:.3f} ≥ 1.20",
                   "OK" if result['ok'] else "FAIL",
                   code_ref="ACI 18.7.3.2",
                   status="OK" if result['ok'] else "FAIL"),
    ]
    return StepBlock(
        title=f"Columna-fuerte / viga-débil — {joint_id}",
        code_ref="ACI 318-19 §18.7.3",
        inputs_kv=inputs_kv,
        steps=steps,
        ok=result['ok'],
        conclusion=("El nudo cumple SCWB." if result['ok']
                    else "El nudo NO cumple SCWB; redimensionar columna o reducir refuerzo de viga."),
    )


def wall_shear_step_block(ws_result, lw_mm: float, h_mm: float,
                          wall_id: str = "MURO") -> StepBlock:
    """Render de ``aci318_ch18_walls.special_wall_shear``."""
    inputs_kv = [
        ("l_w (mm)", f"{lw_mm:.0f}"),
        ("h muro (mm)", f"{h_mm:.0f}"),
        ("α_c", f"{ws_result.alpha_c:.3f}"),
    ]
    steps = [
        StepRecord("Área cortante",
                   "A_cv = l_w · h",
                   f"A_cv = {lw_mm:.0f} · {h_mm:.0f}",
                   f"{ws_result.Acv_mm2:.0f} mm²",
                   code_ref="ACI 18.10.4"),
        StepRecord("Contribución concreto",
                   "V_c = α_c · λ · √f'c · A_cv",
                   f"V_c con α_c = {ws_result.alpha_c:.3f}",
                   f"{ws_result.Vc_N/1e3:.1f} kN",
                   code_ref="ACI 18.10.4.1"),
        StepRecord("Contribución acero",
                   "V_s = ρ_t · f_y · A_cv",
                   "(ver inputs)",
                   f"{ws_result.Vs_N/1e3:.1f} kN",
                   code_ref="ACI 18.10.4.1"),
        StepRecord("Resistencia nominal V_n",
                   "V_n = V_c + V_s (≤ 0.83·√f'c·A_cv)",
                   "(con cap §18.10.4.3)",
                   f"{ws_result.Vn_N/1e3:.1f} kN",
                   code_ref="ACI 18.10.4.1"),
        StepRecord("Resistencia de diseño",
                   "φV_n  (φ = 0.75)",
                   f"0.75 · {ws_result.Vn_N/1e3:.1f}",
                   f"{ws_result.phiVn_N/1e3:.1f} kN",
                   code_ref="ACI 21.2.4.1"),
        StepRecord("DCR",
                   "V_u / φV_n",
                   "(según demanda V_u)",
                   f"{ws_result.DCR:.3f}" if ws_result.DCR else "n/d",
                   code_ref="ACI 18.10.4.1",
                   status="OK" if ws_result.ok else "FAIL"),
    ]
    return StepBlock(
        title=f"Cortante en muro especial — {wall_id}",
        code_ref="ACI 318-19 §18.10.4",
        inputs_kv=inputs_kv,
        steps=steps,
        ok=ws_result.ok,
        conclusion=(f"DCR = {ws_result.DCR:.3f} ≤ 1.0; el muro cumple." if ws_result.ok
                    else f"DCR = {ws_result.DCR:.3f} > 1.0; aumentar espesor o ρ_t."),
    )


# ---------------------------------------------------------------------------
# Renderer genérico desde dict con notes
# ---------------------------------------------------------------------------

def generic_notes_block(
    title: str,
    code_ref: str,
    notes: Iterable[str],
    *,
    inputs_kv: Optional[list[tuple[str, str]]] = None,
    ok: Optional[bool] = None,
    conclusion: str = "",
) -> StepBlock:
    """Fallback: cualquier output con ``notes`` se renderiza como bloque
    con un StepRecord por línea de note."""
    steps = []
    for note in notes:
        f, sub, res = _split_note(note)
        steps.append(StepRecord(
            description=f or note,
            formula=f,
            substitution=sub,
            result=res,
            code_ref=code_ref,
        ))
    return StepBlock(
        title=title, code_ref=code_ref,
        inputs_kv=inputs_kv or [], steps=steps,
        ok=ok, conclusion=conclusion,
    )


# ---------------------------------------------------------------------------
# Renderizado en PDF (usando Report del pdf_builder)
# ---------------------------------------------------------------------------

def render_block_pdf(rep, block: StepBlock) -> None:
    """Inyecta un StepBlock en un ``Report`` (pdf_builder.Report)."""
    rep.add_subsection(block.title)
    rep.add_paragraph(f"Referencia normativa: {block.code_ref}")

    if block.inputs_kv:
        rep.add_paragraph("Datos de entrada:")
        rep.add_kv_table(block.inputs_kv)

    if block.steps:
        rep.add_paragraph("Cálculo paso a paso:")
        df = pd.DataFrame([
            {
                "Paso": i + 1,
                "Descripción": s.description,
                "Fórmula": s.formula,
                "Sustitución": s.substitution,
                "Resultado": s.result,
                "Status": s.status,
                "Ref.": s.code_ref,
            }
            for i, s in enumerate(block.steps)
        ])
        rep.add_dataframe(df)

    if block.summary_table is not None and not block.summary_table.empty:
        rep.add_paragraph("Resumen:")
        rep.add_dataframe(block.summary_table)

    if block.conclusion:
        status = _status_from_ok(block.ok)
        rep.add_paragraph(f"[{status}] {block.conclusion}")


def render_block_markdown(block: StepBlock) -> str:
    """Renderiza un StepBlock como markdown (útil para previews o tests)."""
    out = [f"## {block.title}", f"*{block.code_ref}*", ""]
    if block.inputs_kv:
        out.append("**Datos de entrada:**")
        out.append("")
        out.append("| Parámetro | Valor |")
        out.append("|---|---|")
        for k, v in block.inputs_kv:
            out.append(f"| {k} | {v} |")
        out.append("")
    if block.steps:
        out.append("**Paso a paso:**")
        out.append("")
        out.append("| # | Descripción | Fórmula | Sustitución | Resultado | Ref. |")
        out.append("|---|---|---|---|---|---|")
        for i, s in enumerate(block.steps, 1):
            out.append(
                f"| {i} | {s.description} | `{s.formula}` | `{s.substitution}` | "
                f"**{s.result}** | {s.code_ref} |"
            )
        out.append("")
    if block.conclusion:
        st = _status_from_ok(block.ok)
        out.append(f"**[{st}]** {block.conclusion}")
    return "\n".join(out)


__all__ = [
    "StepRecord", "StepBlock",
    "rbs_step_block",
    "asce7_base_shear_step_block",
    "ec8_beam_capacity_step_block",
    "aci_scwb_step_block",
    "wall_shear_step_block",
    "generic_notes_block",
    "render_block_pdf",
    "render_block_markdown",
]
