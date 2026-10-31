"""Tests pile cap + consolidación 1D."""
import pytest

from foundationcalc.memos.pile_cap import (
    PileCapInput, render_pile_cap_memo,
)
from foundationcalc.consolidacion_1d import (
    ConsolidationInput, evaluate_consolidation,
)


class TestPileCap:
    def test_carga_baja_safe(self):
        r = render_pile_cap_memo(PileCapInput(
            P_kN=1000, n_piles=4, pile_diameter_m=0.6,
            cap_thickness_m=1.0,
        ))
        assert r.is_safe
        assert r.rebar_area_mm2 > 0

    def test_carga_alta_falla(self):
        r = render_pile_cap_memo(PileCapInput(
            P_kN=50_000, n_piles=4, pile_diameter_m=0.3,
            cap_thickness_m=0.5,
        ))
        assert not r.is_safe


class TestPileCapBromsMeyerhof:
    """FD-002: Broms / Meyerhof / group efficiency pile-cap memo."""

    def test_safe_case_clay(self):
        from foundationcalc.memos.pile_cap import (
            BromsMeyerhofInput, render_pile_cap_broms_meyerhof_memo,
        )
        inp = BromsMeyerhofInput(
            n_piles=4, n_rows=2, n_cols=2,
            pile_diameter_m=0.6, pile_length_m=15,
            pile_spacing_m=1.8,
            P_total_kN=3000, H_kN=200,
            Q_single_kN=1200,
            soil_type="clay", su_kPa=60,
            cap_h_m=1.0, fc_MPa=25,
        )
        r = render_pile_cap_broms_meyerhof_memo(inp)
        assert r.is_safe_axial
        assert r.is_safe_lateral
        assert r.eta_group > 0 and r.eta_group <= 1
        assert r.Q_group_kN > 0
        assert r.H_ult_single_kN > 0
        assert len(r.markdown) > 0

    def test_safe_case_sand(self):
        from foundationcalc.memos.pile_cap import (
            BromsMeyerhofInput, render_pile_cap_broms_meyerhof_memo,
        )
        r = render_pile_cap_broms_meyerhof_memo(BromsMeyerhofInput(
            n_piles=6, n_rows=2, n_cols=3,
            pile_diameter_m=0.8, pile_length_m=20,
            pile_spacing_m=2.4,
            P_total_kN=6000, H_kN=300,
            Q_single_kN=1500,
            soil_type="sand", phi_deg=32,
            gamma_soil_kN_m3=18,
        ))
        assert r.is_safe_axial
        assert r.eta_group > 0

    def test_overloaded_group_fails(self):
        from foundationcalc.memos.pile_cap import (
            BromsMeyerhofInput, render_pile_cap_broms_meyerhof_memo,
        )
        r = render_pile_cap_broms_meyerhof_memo(BromsMeyerhofInput(
            n_piles=2, P_total_kN=50000, Q_single_kN=500,
        ))
        assert not r.is_safe_axial

    def test_punching_thin_cap_fails(self):
        from foundationcalc.memos.pile_cap import (
            BromsMeyerhofInput, render_pile_cap_broms_meyerhof_memo,
        )
        r = render_pile_cap_broms_meyerhof_memo(BromsMeyerhofInput(
            n_piles=4, P_total_kN=8000, cap_h_m=0.20, fc_MPa=20,
        ))
        assert not r.is_safe_punching

    def test_markdown_not_empty(self):
        from foundationcalc.memos.pile_cap import (
            BromsMeyerhofInput, render_pile_cap_broms_meyerhof_memo,
        )
        r = render_pile_cap_broms_meyerhof_memo(BromsMeyerhofInput())
        assert "Broms" in r.markdown
        assert "Meyerhof" in r.markdown or "Punzonamiento" in r.markdown
        assert len(r.markdown) > 100

    def test_numerical_example(self):
        """Verify numerical values for a known configuration."""
        from foundationcalc.memos.pile_cap import (
            BromsMeyerhofInput, render_pile_cap_broms_meyerhof_memo,
        )
        r = render_pile_cap_broms_meyerhof_memo(BromsMeyerhofInput(
            n_piles=4, n_rows=2, n_cols=2,
            pile_diameter_m=0.6, pile_spacing_m=1.8,
            P_total_kN=3000, Q_single_kN=1000,
        ))
        # eta for 2x2 group, D/s = 0.6/1.8 = 1/3
        # theta = atan(1/3) ~ 18.43 deg
        # eta = 1 - 18.43*(1*2+1*2)/(90*4) ~ 0.795
        assert 0.7 < r.eta_group < 0.9
        assert r.Q_group_kN == pytest.approx(4 * 1000 * r.eta_group, rel=1e-6)


class TestConsolidacion:
    def test_basico(self):
        r = evaluate_consolidation(ConsolidationInput(
            H_layer_m=5, sigma_v_0_kPa=80, delta_sigma_kPa=50,
            Cc=0.20, e_0=0.8, cv_m2_per_year=2.0,
        ))
        assert r.Sc_mm > 0
        assert r.t_50pct_days < r.t_90pct_days

    def test_doble_drenaje_acelera(self):
        s = evaluate_consolidation(ConsolidationInput(
            H_layer_m=4, sigma_v_0_kPa=80, delta_sigma_kPa=40,
            Cc=0.2, drainage="single",
        ))
        d = evaluate_consolidation(ConsolidationInput(
            H_layer_m=4, sigma_v_0_kPa=80, delta_sigma_kPa=40,
            Cc=0.2, drainage="double",
        ))
        assert d.t_50pct_days < s.t_50pct_days
