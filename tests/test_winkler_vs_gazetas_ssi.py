# -*- coding: utf-8 -*-
"""test_winkler_vs_gazetas_ssi.py — Comparación cuantitativa entre Winkler escalar y Gazetas (1991).

CAMPAÑA AG37 — Bloque 2c: Gazetas SSI ignorado frente a simplificación escalar Winkler.
Mide la discrepancia de rigidez lateral y rotacional entre:
  1. Winkler escalar (FoundationDesignJm/fastsap_winkler.py: Kx = Ky = 0.5 * Kz)
  2. Impedancias estáticas elásticas de Gazetas (1991) (GeoJm/ssi_springs.py)
"""
from __future__ import annotations

import pytest
from geojm.gazetas_springs import GazetasInput, evaluate_gazetas
from foundationdesignjm.integration.fastsap_winkler import WinklerSpring


class TestWinklerVsGazetasSSI:
    def test_winkler_scalar_vs_gazetas_discrepancy(self) -> None:
        """Cuantifica la desviación del modelo escalar Winkler (0.5*Kz) frente a Gazetas (1991).

        Caso de estudio:
          Zapata cuadrada rígida superficial B = 2.0 m, L = 2.0 m
          Suelo: Vs = 200 m/s, rho = 1900 kg/m³, nu = 0.35
          Módulo de cortante: G = rho * Vs² = 1900 * 200² = 76.0 MPa

        Resultados analíticos Gazetas (1991):
          Kz = 530 830.8 kN/m
          Kx = Ky = 414 545.5 kN/m  (Ratio Kx/Kz = 0.7809)
          Krx = 420 728.8 kNm/rad
          Kry = 435 236.7 kNm/rad

        Simplificación Winkler (Kx = 0.5 * Kz):
          Kz = 530 830.8 kN/m
          Kx = 0.5 * Kz = 265 415.4 kN/m
          Krx = 0.0 kNm/rad (resorte puntual en nudo)

        Discrepancia medida:
          Rigidez lateral: Delta_Kx = (265 415.4 - 414 545.5) / 414 545.5 = -35.97 %
          La simplificación 0.5*Kz subestima la rigidez lateral elástica en ~36 %,
          y omite por completo la rigidez rotacional por cabeceo (rocking) Krx.
        """
        B = 2.0
        L = 2.0
        Vs = 200.0
        rho = 1900.0
        nu = 0.35

        # 1. Evaluación analítica en semi-espacio elástico según Gazetas (1991)
        gazetas_inp = GazetasInput(L_m=L, B_m=B, Vs_m_per_s=Vs, rho_soil_kg_m3=rho, nu_soil=nu)
        g_res = evaluate_gazetas(gazetas_inp)

        assert g_res.G_soil_MPa == pytest.approx(76.0, rel=1e-3)
        assert g_res.Kz_kN_per_m == pytest.approx(530830.8, rel=1e-3)
        assert g_res.Kx_kN_per_m == pytest.approx(414545.5, rel=1e-3)

        ratio_kx_kz_gazetas = g_res.Kx_kN_per_m / g_res.Kz_kN_per_m
        assert ratio_kx_kz_gazetas == pytest.approx(0.7809, rel=1e-3)

        # 2. Resorte Winkler escalar simplificado (Kx = Ky = 0.5 * Kz)
        kz_equiv = g_res.Kz_kN_per_m
        kx_winkler = 0.5 * kz_equiv
        w_spring = WinklerSpring(joint_name="N_BASE", kx_kN_m=kx_winkler, ky_kN_m=kx_winkler, kz_kN_m=kz_equiv)

        assert w_spring.kx_kN_m == pytest.approx(265415.4, rel=1e-3)

        # 3. Medición rigurosa de la discrepancia
        discrepancia_kx_pct = ((w_spring.kx_kN_m - g_res.Kx_kN_per_m) / g_res.Kx_kN_per_m) * 100.0
        assert discrepancia_kx_pct == pytest.approx(-35.97, abs=0.1)

        # 4. Verificación de ausencia de rigidez rotacional en Winkler puntual
        # (WinklerSpring solo transporta traslaciones kx, ky, kz)
        assert not hasattr(w_spring, "krx_kNm_rad") or getattr(w_spring, "krx_kNm_rad", 0.0) == 0.0
        assert g_res.Krx_kNm_per_rad > 400000.0
