"""Tests para items pendientes de IDEAS_20 (grupos A/B/C)."""
import pytest


def test_muro_contencion_memoria():
    from foundationcalc.memos.muro_contencion import (
        MuroContencionInput, memoria_muro, rankine_ka, coulomb_ka,
    )
    Ka = rankine_ka(30)
    assert 0.30 < Ka < 0.36
    Kc = coulomb_ka(30, 20)
    assert 0.25 < Kc < 0.32
    res = memoria_muro(MuroContencionInput(H_m=4.0, phi_deg=30))
    assert res.Ea_rankine_kN_m > 0
    assert "Coulomb" in res.markdown


def test_muro_contencion_con_sobrecarga():
    from foundationcalc.memos.muro_contencion import MuroContencionInput, memoria_muro
    res = memoria_muro(MuroContencionInput(H_m=3.0, q_surch_kPa=10))
    assert res.Ea_rankine_kN_m > 0


def test_nsr10_titulo_h_estatica():
    from foundationcalc.memos.nsr10_titulo_h import NSR10HInput, memoria_nsr10_h
    res = memoria_nsr10_h(NSR10HInput(B_m=2, L_m=2, Df_m=1.5, Q_kN=400))
    assert res.q_ult_kPa > 0
    assert res.FS == 3.0
    assert "NSR-10" in res.markdown


def test_nsr10_sismica_fs2():
    from foundationcalc.memos.nsr10_titulo_h import NSR10HInput, memoria_nsr10_h
    res = memoria_nsr10_h(NSR10HInput(B_m=2, L_m=2, Df_m=1.5, Q_kN=400, es_sismica=True))
    assert res.FS == 2.0


def test_consolidacion_1d():
    from foundationcalc.analysis.consolidacion_1d import (
        ConsolidationInput, consolidate, U_from_Tv,
    )
    res = consolidate(ConsolidationInput(
        H_layer_m=4, sigma_v0_kPa=100, delta_sigma_kPa=80, Cc=0.3, code="EU"
    ))
    assert res.Sc_mm > 0
    assert res.t_50_days > 0
    assert 0.4 < U_from_Tv(0.197) < 0.6


def test_consolidacion_codigo_invalido():
    from foundationcalc.analysis.consolidacion_1d import ConsolidationInput, consolidate
    with pytest.raises(ValueError):
        consolidate(ConsolidationInput(H_layer_m=4, sigma_v0_kPa=100,
                                        delta_sigma_kPa=80, Cc=0.3, code="ZZ"))


def test_boussinesq_punto():
    from foundationcalc.analysis.boussinesq import (
        BoussinesqPoint, sigma_z_point, BoussinesqRect, sigma_z_rect_center,
        stress_profile,
    )
    sz = sigma_z_point(BoussinesqPoint(P_kN=1000, z_m=2, r_m=0))
    assert sz > 0
    sr = sigma_z_rect_center(BoussinesqRect(qo_kPa=100, B_m=2, L_m=2, z_m=1, code="EU"))
    assert 0 < sr <= 100
    prof = stress_profile(100, 2, 2, 10, n=5, code="US")
    assert len(prof) == 5


def test_boussinesq_decae_con_profundidad():
    from foundationcalc.analysis.boussinesq import BoussinesqRect, sigma_z_rect_center
    s1 = sigma_z_rect_center(BoussinesqRect(qo_kPa=100, B_m=2, L_m=2, z_m=1))
    s5 = sigma_z_rect_center(BoussinesqRect(qo_kPa=100, B_m=2, L_m=2, z_m=5))
    assert s5 < s1


def test_friccion_negativa():
    from foundationcalc.analysis.friccion_negativa import (
        Layer, FriccionNegativaInput, downdrag,
    )
    inp = FriccionNegativaInput(
        pile_diameter_m=0.6,
        layers=(
            Layer(0, 5, 18, 0.30, True),
            Layer(5, 15, 19, 0.25, False),
        ),
        z_neutro_m=10,
        Q_dead_kN=500,
        code="EU",
    )
    res = downdrag(inp)
    assert res.Q_neg_kN > 0
    assert res.Q_total_servicio_kN > 500


def test_suelo_expansivo():
    from foundationcalc.analysis.suelo_expansivo import ExpansiveInput, expansive_assessment
    res = expansive_assessment(ExpansiveInput(PI=40, w_natural_pct=15, w_final_pct=35, code="US"))
    assert res.risk in {"BAJO", "MEDIO", "ALTO", "MUY ALTO"}
    assert res.swelling_pressure_kPa > 0


def test_pilote_excentrico():
    from foundationcalc.analysis.pilote_excentrico import (
        PiloteExcentricoInput, evaluar,
    )
    res = evaluar(PiloteExcentricoInput(
        D_m=0.6, L_m=10, N_kN=500, H_kN=50, M_kNm=100, code="EU",
    ))
    assert res.H_admisible_kN > 0
    assert res.interaction_ratio > 0


def test_quantities():
    from foundationcalc.quantities import QuantitiesInput, quantities
    res = quantities(QuantitiesInput(B_m=2, L_m=3, H_m=0.5, code="EU"))
    assert res.volumen_hormigon_m3 == pytest.approx(3.0)
    assert res.masa_acero_kg == pytest.approx(240.0)


def test_dxf_armado_no_dxfjm():
    from foundationcalc.integration.dxf_armado import (
        ArmadoZapataDXF, export_armado_zapata,
    )
    arm = ArmadoZapataDXF(B_m=2, L_m=2, H_m=0.5, n_x=6, n_y=6, db_x_mm=12, db_y_mm=12)
    # No falla aunque DXFStructuralJm no este
    result = export_armado_zapata(arm, "test.dxf")
    assert isinstance(result, bool)


def test_fastsap_winkler_dry_run():
    from foundationcalc.integration.fastsap_winkler import (
        WinklerSpring, FastSAPWinklerExporter,
    )
    springs = [WinklerSpring(f"J{i}", 1000, 1000, 5000) for i in range(3)]
    exp = FastSAPWinklerExporter(dry_run=True)
    res = exp.export(springs)
    assert res["dry_run"] is True
    assert res["n_applied"] == 3


def test_fastsap_winkler_mock():
    from unittest.mock import MagicMock
    from foundationcalc.integration.fastsap_winkler import (
        WinklerSpring, FastSAPWinklerExporter,
    )
    mock = MagicMock()
    exp = FastSAPWinklerExporter(client=mock, dry_run=False)
    res = exp.export([WinklerSpring("J1", 1000, 1000, 5000)])
    assert res["n_applied"] >= 0
