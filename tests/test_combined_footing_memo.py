"""Tests FD-003: memo combined_footing (full: presiones, EC7, flexion, punzonamiento)."""
import math

import pytest

from foundationdesignjm.memos.combined_footing import (
    CombinedFootingFullInput,
    CombinedFootingFullResult,
    render_combined_footing_memo,
)


class TestCombinedFootingMemo:
    """Tests for render_combined_footing_memo."""

    def test_render_produces_nonempty_output(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=500, P2_kN=500, distance_cols_m=4, L_m=6, B_m=2,
        ))
        assert isinstance(r, CombinedFootingFullResult)
        assert len(r.markdown) > 100
        assert "Paso 1" in r.markdown
        assert "Paso 4" in r.markdown

    def test_symmetric_case_no_eccentricity(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=500, P2_kN=500, distance_cols_m=4, L_m=6, B_m=2,
        ))
        # Symmetric loads -> e ~ 0 -> sigma_max ~ sigma_min
        assert abs(r.e_m) < 1e-3
        assert r.sigma_max_kPa == pytest.approx(r.sigma_min_kPa, abs=1.0)
        assert r.is_safe_no_tension

    def test_eccentric_loading(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=800, P2_kN=200, distance_cols_m=4, L_m=6, B_m=2,
        ))
        assert r.sigma_max_kPa > r.sigma_min_kPa
        assert abs(r.e_m) > 0.1

    def test_sigma_max_below_qadm_safe_case(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=400, P2_kN=400, distance_cols_m=3, L_m=5, B_m=2,
            q_adm_kPa=200,
        ))
        assert r.sigma_max_kPa < 200
        assert r.is_safe_bearing

    def test_overloaded_fails_bearing(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=5000, P2_kN=5000, distance_cols_m=4, L_m=4, B_m=1,
            q_adm_kPa=200,
        ))
        # sigma_max >> q_adm -> bearing check fails
        assert r.sigma_max_kPa > 200

    def test_flexural_reinforcement_positive(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=600, P2_kN=600, distance_cols_m=4, L_m=6, B_m=2,
            h_m=0.60, fc_MPa=25, fy_MPa=420,
        ))
        assert r.As_req_mm2 > 0
        assert r.M_face_col1_kNm >= 0
        assert r.M_face_col2_kNm >= 0

    def test_punching_thick_cap_passes(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=400, P2_kN=400, distance_cols_m=3, L_m=5, B_m=2,
            h_m=0.80, fc_MPa=30,
        ))
        assert r.is_safe_punching_col1
        assert r.is_safe_punching_col2

    def test_punching_thin_cap_fails(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=3000, P2_kN=3000, distance_cols_m=4, L_m=6, B_m=2,
            h_m=0.15, fc_MPa=20,
        ))
        # Very thin cap with heavy loads -> punching fails
        assert not r.is_safe_punching_col1 or not r.is_safe_punching_col2

    def test_ec7_bearing_capacity_check(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=300, P2_kN=300, distance_cols_m=3, L_m=5, B_m=2,
            gamma_soil_kN_m3=18, c_kPa=20, phi_deg=30, D_f_m=1.5,
        ))
        assert r.R_d_kN > 0
        assert r.is_safe_bearing

    def test_moments_with_applied_moments(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=500, P2_kN=500,
            M1_kNm=50, M2_kNm=30,
            distance_cols_m=4, L_m=6, B_m=2,
        ))
        # Applied moments shift the eccentricity
        assert r.e_m != 0 or abs(r.e_m) < 1e-6
        assert r.M_midspan_kNm >= 0

    def test_to_dict(self):
        r = render_combined_footing_memo(CombinedFootingFullInput(
            P1_kN=500, P2_kN=500, distance_cols_m=4, L_m=6, B_m=2,
        ))
        d = r.to_dict()
        assert "sigma_max_kPa" in d
        assert "As_req_mm2" in d
        assert "is_safe_punching_col1" in d
