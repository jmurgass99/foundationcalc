"""B48: cinco sitios de FoundationDesignJm que inventan o descartan un dato (§8).

§8.2  integration/foundation_chain._resolve_reactions (rama de dicts)
    fz_kN=float(r.get("Fz", r.get("FZ", 0.0)))   ... y las otras cinco igual
    (a) un Fz AUSENTE sale igual que un Fz = 0 MEDIDO: los dos acaban NO_LOAD;
    (b) la cabecera CSI F1..M3 --declarada en `etabs/client.py:140-145`-- no se
        reconoce: una fila COMPLETA sale con las seis componentes a 0.0;
    (c) un None revienta con TypeError sin nombrar el nudo;
    (d) un DataFrame entra y sale como lista VACIA, en silencio.
    Los momentos/cortantes ausentes SIGUEN a 0.0 --rechazarlos es la pregunta
    PARADA en §7-quinquies-quater-- pero ya no en silencio.

§8.7  codes/aisc_360_connections.design_base_plate (copia de FoundationDesignJm;
    la de fastsap se arreglo en B44 y las dos siguen identicas).

§8.18 reaction_bridge: la envolvente de DESLIZAMIENTO solo recorria las
    combinaciones con Fz > 0. Un nudo {Fz 500, Fx 10} + {Fz 0.0, Fx 300} firmaba
    CALCULADO_CUMPLE, y el mismo con Fz = +1 (estrictamente MENOS
    desfavorable) daba FALLA: no era monotono. Una base sin axil no genera
    rozamiento; la formula es la del propio docstring (F_h <= mu*N/FS).

§8.19 design/reinforcement.design_footing_flexure recibia Mx_Ed/My_Ed y NO LOS
    USABA: armaba con la presion MEDIA. Y la cadena ni siquiera se los pasaba.
    Con e_x = L/6 el plano salia con la mitad del momento (16O16 donde la regla
    del propio paquete --`q_flex = q_max`, services/footings.py:168-- da 30O16).

§8.29 analysis/cpt_to_design.soil_profile_from_cpt
    cu = s.c_u_kPa or 40.0
    Un c_u = 0.0 MEDIDO se convertia en 40 kPa inventados (el esquema lo admite:
    ge=0). Medido: bearing_ok pasaba de False a True.
"""
from __future__ import annotations

import math

import pandas as pd
import pytest


# =========================================================================== #
# §8.2 _resolve_reactions
# =========================================================================== #

def _resolver(filas):
    from foundationdesignjm.integration.foundation_chain import _resolve_reactions
    return _resolve_reactions(filas)


def test_un_Fz_AUSENTE_no_es_un_Fz_cero_medido() -> None:
    with pytest.raises(ValueError, match="C1"):
        _resolver([{"joint": "C1", "case": "U", "Mx": 0.0, "My": 0.0}])


def test_GUARDA_un_Fz_cero_MEDIDO_sigue_entrando() -> None:
    (r,) = _resolver([{"joint": "C1", "case": "U", "Fz": 0.0}])
    assert r.fz_kN == 0.0


def test_la_cabecera_CSI_F1_a_M3_se_reconoce() -> None:
    (r,) = _resolver([{"joint": "C1", "case": "U", "F1": 30.0, "F2": 20.0,
                       "F3": 800.0, "M1": 150.0, "M2": 120.0, "M3": 5.0}])
    assert (r.fx_kN, r.fy_kN, r.fz_kN) == (30.0, 20.0, 800.0)
    assert (r.mx_kNm, r.my_kNm, r.mz_kNm) == (150.0, 120.0, 5.0)


def test_un_None_no_revienta_sin_nombrar_el_nudo() -> None:
    with pytest.raises(ValueError, match="C7"):
        _resolver([{"joint": "C7", "case": "U", "Fz": None}])


def test_un_DataFrame_no_desaparece_en_silencio() -> None:
    reacciones = _resolver(pd.DataFrame([{"joint": "C1", "case": "U", "Fz": 800.0}]))
    assert len(reacciones) == 1 and reacciones[0].fz_kN == 800.0


def test_los_momentos_ausentes_se_DECLARAN_asumidos() -> None:
    from foundationdesignjm.integration.foundation_chain import foundation_chain_from_etabs
    res = foundation_chain_from_etabs([{"joint": "C1", "case": "U", "Fz": 800.0}],
                                      {"allowable_bearing_kPa": 200.0})
    asumidas = set(res.design_summary["C1"].get("assumed_zero", ()))
    assert {"MX", "MY", "FX", "FY"} <= asumidas, res.design_summary["C1"]


def test_GUARDA_una_fila_completa_no_declara_nada() -> None:
    from foundationdesignjm.integration.foundation_chain import foundation_chain_from_etabs
    res = foundation_chain_from_etabs(
        [{"joint": "C1", "case": "U", "Fx": 30.0, "Fy": 30.0, "Fz": 800.0,
          "Mx": 150.0, "My": 150.0, "Mz": 0.0}],
        {"allowable_bearing_kPa": 200.0})
    assert not res.design_summary["C1"].get("assumed_zero")


# =========================================================================== #
# §8.7 placa base DG-1 (copia de FoundationDesignJm)
# =========================================================================== #

def test_DG1_FDJM_un_levantamiento_no_es_aplastamiento() -> None:
    from foundationdesignjm.codes.aisc_360_connections import design_base_plate
    r = design_base_plate(Pu=-150e3, fc=25.0, B=400.0, N=400.0, d=300.0,
                          bf=300.0, Fy_plate=250.0)
    assert r.ok is not True and "levantamiento" in (r.motivo_no_evaluado or "")


def test_DG1_FDJM_GUARDA_la_compresion_no_cambia() -> None:
    from foundationdesignjm.codes.aisc_360_connections import design_base_plate
    r = design_base_plate(Pu=150e3, fc=25.0, B=400.0, N=400.0, d=300.0,
                          bf=300.0, Fy_plate=250.0)
    assert r.ok is True and r.tp_req == pytest.approx(7.3030, abs=1e-3)


# =========================================================================== #
# §8.18 deslizamiento
# =========================================================================== #

def _zapata(*reacciones):
    from jmstructural_common.model import Reaction
    from foundationdesignjm.reaction_bridge import size_isolated_footing_from_reactions
    rx = [Reaction(node_id="N1", case=f"C{i}", **kw) for i, kw in enumerate(reacciones)]
    return size_isolated_footing_from_reactions(rx, allowable_bearing_kPa=200.0)["N1"]


def test_DESLIZAMIENTO_una_combinacion_sin_axil_con_cortante_gobierna() -> None:
    z = _zapata({"fz_kN": 500.0, "fx_kN": 10.0}, {"fz_kN": 0.0, "fx_kN": 300.0})
    assert z["status"] == "SLIDING_GOVERNS", z
    assert z["sliding_dcr"] > 1.0


def test_DESLIZAMIENTO_ya_es_monotono() -> None:
    """Fz = 0 no puede ser MAS favorable que Fz = +1 con el mismo cortante."""
    cero = _zapata({"fz_kN": 500.0, "fx_kN": 10.0}, {"fz_kN": 0.0, "fx_kN": 300.0})
    uno = _zapata({"fz_kN": 500.0, "fx_kN": 10.0}, {"fz_kN": 1.0, "fx_kN": 300.0})
    assert cero["sliding_dcr"] >= uno["sliding_dcr"]


def test_DESLIZAMIENTO_GUARDA_sin_cortante_nada_cambia() -> None:
    z = _zapata({"fz_kN": 500.0, "fx_kN": 10.0}, {"fz_kN": 0.0, "fx_kN": 0.0})
    assert z["status"] == "OK"
    assert z["sliding_dcr"] == pytest.approx(_zapata({"fz_kN": 500.0, "fx_kN": 10.0})["sliding_dcr"])


# =========================================================================== #
# §8.19 armado de la zapata
# =========================================================================== #

def _armar(**kw):
    from foundationdesignjm.design.reinforcement import design_footing_flexure_both_ways
    return design_footing_flexure_both_ways(B_m=3.0, L_m=3.0, h_m=0.5, **kw)


def test_ARMADO_los_momentos_que_recibe_ya_no_se_tiran() -> None:
    centrada = _armar(N_Ed_kN=1800.0)
    excentrica = _armar(N_Ed_kN=1800.0, My_Ed_kNm=900.0)       # e_x = L/6
    assert excentrica["X"].M_Ed_kNm > centrada["X"].M_Ed_kNm * 1.5, (
        "con e_x = L/6 la presion de borde es el DOBLE de la media: el momento "
        "tiene que subir, y antes salia identico"
    )


def test_ARMADO_GUARDA_sin_momentos_el_armado_no_cambia() -> None:
    """Con Mx = My = 0, q_max = q_avg exacto: el caso centrado no se mueve."""
    from foundationdesignjm.design.reinforcement import design_footing_flexure_both_ways
    r = design_footing_flexure_both_ways(B_m=2.15, L_m=2.15, h_m=0.5, N_Ed_kN=1800.0)
    assert r["X"].M_Ed_kNm == pytest.approx(365.955, abs=0.05)


def test_ARMADO_un_levantamiento_no_se_publica_como_armado_comprobado() -> None:
    r = _armar(N_Ed_kN=0.0)
    for d in ("X", "Y"):
        assert r[d].status not in ("OK", "HOOK_REQUIRED"), r[d].status
        assert r[d].motivo_no_evaluado


def test_ARMADO_la_cadena_le_pasa_la_excentricidad() -> None:
    from foundationdesignjm.integration.foundation_chain import foundation_package
    base = [{"joint": "C1", "case": "U", "Fx": 0.0, "Fy": 0.0, "Fz": 1800.0,
             "Mx": 0.0, "My": 0.0, "Mz": 0.0}]
    exc = [{**base[0], "My": 900.0}]
    a = foundation_package(base, {"allowable_bearing_kPa": 400.0}, footing_thickness_m=0.5)
    b = foundation_package(exc, {"allowable_bearing_kPa": 400.0}, footing_thickness_m=0.5)
    # Antes la cadena no pasaba los momentos: el M_Ed de la zapata excentrica
    # (554.88, medido en el triage) era q_avg*B*vx^2/2, como si fuese centrada.
    # Con la regla del PROPIO paquete --q_flex = q_max en las DOS direcciones,
    # igual que services/footings.py:169-171-- sale 1109.76 kN*m, exactamente el
    # valor que el triage midio para esa regla (30O16). X e Y salen iguales por
    # diseno de esa regla (conservadora), no por el defecto.
    mx = b.flexure_reinforcement["C1"]["X"].M_Ed_kNm
    assert mx == pytest.approx(1109.76, abs=0.05), mx
    assert b.design_summary["C1"]["e_x_m"] > 0.0
    assert a.flexure_reinforcement["C1"]["X"].M_Ed_kNm < mx


# =========================================================================== #
# §8.29 CPT: c_u = 0.0 medido
# =========================================================================== #

def test_CPT_un_cu_cero_MEDIDO_no_se_convierte_en_40() -> None:
    from types import SimpleNamespace
    from foundationdesignjm.analysis import cpt_to_design as mod
    estrato = SimpleNamespace(c_u_kPa=0.0)
    assert mod._cu_del_estrato(estrato) == 0.0


def test_CPT_un_cu_AUSENTE_no_se_inventa() -> None:
    from types import SimpleNamespace
    from foundationdesignjm.analysis import cpt_to_design as mod
    with pytest.raises(ValueError, match="c_u"):
        mod._cu_del_estrato(SimpleNamespace(c_u_kPa=None, z_top_m=1.0, z_bot_m=2.0))


# =========================================================================== #
# Encontrado al arreglar §8.2: el MISMO 200 kPa inventado que B47 cerro en fastsap
# =========================================================================== #

def test_la_cadena_no_inventa_la_capacidad_del_suelo() -> None:
    from foundationdesignjm.integration.foundation_chain import foundation_chain_from_etabs
    with pytest.raises(ValueError, match="allowable_bearing_kPa"):
        foundation_chain_from_etabs([{"joint": "C1", "case": "U", "Fz": 800.0}], {})


def test_GUARDA_con_la_capacidad_declarada_la_cadena_funciona() -> None:
    from foundationdesignjm.integration.foundation_chain import foundation_chain_from_etabs
    res = foundation_chain_from_etabs([{"joint": "C1", "case": "U", "Fz": 800.0}],
                                      {"allowable_bearing_kPa": 200.0})
    assert res.design_summary["C1"]["qa_kPa"] == 200.0


def test_CPT_un_E_correlado_NULO_no_se_convierte_en_30_MPa() -> None:
    from types import SimpleNamespace
    from foundationdesignjm.analysis import cpt_to_design as mod
    with pytest.raises(ValueError, match="Robertson"):
        mod._E_del_estrato(SimpleNamespace(E_MPa=0.0, z_top=1.0, z_bot=3.0))


def test_CPT_GUARDA_un_E_medido_positivo_pasa_tal_cual() -> None:
    from types import SimpleNamespace
    from foundationdesignjm.analysis import cpt_to_design as mod
    assert mod._E_del_estrato(SimpleNamespace(E_MPa=12.5, z_top=1.0, z_bot=3.0)) == 12.5
