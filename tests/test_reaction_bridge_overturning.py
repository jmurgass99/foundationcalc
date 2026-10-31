# -*- coding: utf-8 -*-
"""test_reaction_bridge_overturning.py — Pruebas de vuelco, deslizamiento y presión Meyerhof.

CAMPAÑA AG37 — Bloque 1: Cimentaciones bajo momento y cortante real.
Verifica que size_isolated_footing_from_reactions no ignore mx_kNm, my_kNm, fx_kN, fy_kN.
"""
from __future__ import annotations

import pytest
from foundationcalc.reaction_bridge import size_isolated_footing_from_reactions
from foundationcalc._common.model import Reaction


class TestReactionBridgeOverturningAndSliding:
    def test_overturning_moment_increases_footing_size(self) -> None:
        """Caso reproductor:

        N = 400.0 kN
        Mx = 120.0 kNm, My = 0.0
        qa = 200.0 kPa

        Implementación defectuosa previa:
          A_req = 400 / 200 = 2.00 m2 -> B = 1.45 m, status = 'OK'
          PERO: ey = 120 / 400 = 0.30 m > B/6 = 0.2417 m (¡DESPEGUE/VUELCO!)
          Meyerhof: L' = 1.45 - 2*0.30 = 0.85 m -> q_eff = 400 / (1.45 * 0.85) = 324.5 kPa >> 200 kPa

        Implementación corregida:
          Para cumplir núcleo central ey <= B/6: B >= 6 * 0.30 = 1.80 m
          A B = 1.80 m: L' = 1.80 - 0.60 = 1.20 m, B' = 1.80 m -> q_eff = 400 / (1.80 * 1.20) = 185.19 kPa <= 200 kPa
          B_m debe ser 1.80 m (no 1.45 m)
          status debe ser 'OVERTURNING_GOVERNS'
        """
        rx = Reaction(
            node_id="N_OVERTURN",
            case="SEISMIC_ULS",
            fx_kN=10.0,
            fy_kN=5.0,
            fz_kN=400.0,
            mx_kNm=120.0,
            my_kNm=0.0,
            mz_kNm=0.0,
        )

        res = size_isolated_footing_from_reactions(
            reactions=[rx],
            allowable_bearing_kPa=200.0,
            min_size_m=1.0,
            size_step_m=0.05,
        )

        r = res["N_OVERTURN"]
        # En la versión corregida debe crecer a 1.80 m
        assert r["B_m"] == pytest.approx(1.80, abs=1e-3)
        assert r["status"] == "OVERTURNING_GOVERNS"
        assert r["e_y_m"] == pytest.approx(0.30, abs=1e-3)
        assert r["e_y_m"] <= r["kern_limit_m"] + 1e-4

    def test_sliding_failure_detected(self) -> None:
        """Cortante horizontal excesivo Fh > mu * N / FS_sliding."""
        rx = Reaction(
            node_id="N_SLIDE",
            case="WIND_ULS",
            fx_kN=80.0,
            fy_kN=0.0,
            fz_kN=200.0,
            mx_kNm=0.0,
            my_kNm=0.0,
            mz_kNm=0.0,
        )

        # mu = 0.35, FS = 1.5 -> Capacidad = 0.35 * 200 / 1.5 = 46.67 kN < 80.0 kN
        res = size_isolated_footing_from_reactions(
            reactions=[rx],
            allowable_bearing_kPa=200.0,
            friction_coef=0.35,
            sliding_fs=1.50,
        )

        r = res["N_SLIDE"]
        assert r["status"] == "SLIDING_GOVERNS"
        assert r["sliding_dcr"] > 1.0

    def test_meyerhof_bearing_governs(self) -> None:
        """Momento moderado que cabe en el núcleo central pero eleva la presión de Meyerhof."""
        rx = Reaction(
            node_id="N_BEARING",
            case="ULS1",
            fx_kN=10.0,
            fy_kN=5.0,
            fz_kN=450.0,
            mx_kNm=10.0,
            my_kNm=20.0,
            mz_kNm=0.0,
        )

        # Sin momentos: 450 / 150 = 3.0 m2 -> B = 1.75 m
        # Con Meyerhof: ex = 20/450 = 0.0444 m, ey = 10/450 = 0.0222 m
        # B = 1.75 m da q_eff = 158.8 kPa > 150 kPa
        # B = 1.80 m da q_eff = 149.8 kPa <= 150 kPa
        # ey, ex <= 1.80/6 = 0.30 m (dentro del núcleo)
        res = size_isolated_footing_from_reactions(
            reactions=[rx],
            allowable_bearing_kPa=150.0,
            min_size_m=1.0,
            size_step_m=0.05,
        )

        r = res["N_BEARING"]
        assert r["B_m"] == pytest.approx(1.80, abs=1e-3)
        assert r["status"] == "BEARING_GOVERNS"
        assert r["q_act_kPa"] <= 150.0

    def test_pure_axial_stays_ok(self) -> None:
        """Sin momentos ni cortantes, la zapata se dimensiona limpiamente a compresión simple."""
        rx = Reaction(
            node_id="N_AXIAL",
            case="GRAV",
            fx_kN=0.0,
            fy_kN=0.0,
            fz_kN=400.0,
            mx_kNm=0.0,
            my_kNm=0.0,
            mz_kNm=0.0,
        )

        # 400 / 100 = 4.0 m2 -> B = 2.00 m
        res = size_isolated_footing_from_reactions(
            reactions=[rx],
            allowable_bearing_kPa=100.0,
            min_size_m=1.0,
            size_step_m=0.05,
        )

        r = res["N_AXIAL"]
        assert r["B_m"] == pytest.approx(2.00, abs=1e-3)
        assert r["status"] == "OK"
        assert r["e_x_m"] == 0.0
        assert r["e_y_m"] == 0.0
