"""packages/FoundationDesignJm/tests/test_foundation_chain.py
===========================================================
Tests de la cadena completa de cimentaciones (Carril B):
ETABS → FoundationDesignJm → SAFE.

Verifica:
1. Resolución del defecto de signos: conservación de tracción/uplift y signos de momentos/cortantes.
2. Detección y reporte explícito de levantamiento (uplift) en dimensionado de zapatas.
3. Cadena integral en mock con N nudos y combinaciones múltiples.
4. Verificación cruzada de punzonamiento EC2 contra referencia analítica calculada.
5. Inyección mock en SafeClient con cargas y muelles.
"""
from __future__ import annotations

import math
from unittest.mock import MagicMock
import pytest

from foundationdesignjm.core.geometry import Column, RectangularFoundation
from foundationdesignjm.core.loading import PointLoad
from foundationdesignjm.design.punching_shear import punching_shear_check
from foundationdesignjm.integration.foundation_chain import (
    FoundationChainResult,
    foundation_chain_from_etabs,
)
from foundationdesignjm.reaction_bridge import (
    reaction_to_point_load,
    size_isolated_footing_from_reactions,
)
from jmstructural_common.model import Reaction


class TestFoundationChain:
    """Suite de validación de la cadena de cimentaciones."""

    def test_reaction_bridge_uplift_and_sign_preservation(self) -> None:
        """Verifica que reaction_to_point_load NO destruye los signos con abs()."""
        # Reacción de levantamiento / tracción con cortantes y momentos con signo
        rx_uplift = Reaction(
            node_id="C1",
            case="WIND_UPLIFT",
            fx_kN=-15.5,
            fy_kN=22.0,
            fz_kN=-180.0,  # Uplift: tracción hacia arriba
            mx_kNm=-45.0,
            my_kNm=60.0,
            mz_kNm=-5.0,
        )

        pt_load = reaction_to_point_load(rx_uplift)
        assert pt_load.fz == -180.0, "Fz negativo (uplift) debe preservarse sin abs()"
        assert pt_load.vx == -15.5
        assert pt_load.vy == 22.0
        assert pt_load.mx == -45.0
        assert pt_load.my == 60.0

    def test_isolated_footing_uplift_detection(self) -> None:
        """Verifica que size_isolated_footing_from_reactions detecta y reporta uplift."""
        reactions = [
            # Nudo 1: Compresión pura
            Reaction(node_id="1", case="ELU_GRAV", fz_kN=600.0),
            # Nudo 2: Tracción pura (uplift gobernante)
            Reaction(node_id="2", case="ELU_WIND", fz_kN=-250.0),
            # Nudo 3: Mixto (compresión en grav, tracción en sismo)
            Reaction(node_id="3", case="ELU_GRAV", fz_kN=400.0),
            Reaction(node_id="3", case="ELU_QUAKE", fz_kN=-120.0),
        ]

        sizing = size_isolated_footing_from_reactions(reactions, allowable_bearing_kPa=200.0)

        # Nudo 1
        assert sizing["1"]["status"] == "OK"
        assert sizing["1"]["has_uplift"] is False
        assert sizing["1"]["N_max_kN"] == 600.0
        assert sizing["1"]["B_m"] == pytest.approx(1.75)  # sqrt(600/200)=1.732 -> step 0.05 = 1.75

        # Nudo 2 (Tracción pura)
        assert sizing["2"]["status"] == "UPLIFT_GOVERNS"
        assert sizing["2"]["has_uplift"] is True
        assert sizing["2"]["uplift_max_kN"] == 250.0
        assert sizing["2"]["q_act_kPa"] == 0.0  # No aplica presión de compresión

        # Nudo 3 (Mixto)
        assert sizing["3"]["status"] == "OK_WITH_UPLIFT_WARNING"
        assert sizing["3"]["has_uplift"] is True
        assert sizing["3"]["uplift_max_kN"] == 120.0
        assert sizing["3"]["N_max_kN"] == 400.0

    def test_punching_shear_cross_check_reference(self) -> None:
        """Verificación cruzada de punzonamiento EC2 contra cálculo analítico de referencia."""
        foundation = RectangularFoundation(length=2500.0, width=2500.0, thickness=600.0)
        column = Column(length=400.0, width=400.0, pos_x=1250.0, pos_y=1250.0)
        d_eff = 0.55  # m
        N_sd = 800.0  # kN
        fck = 30.0    # MPa


        res = punching_shear_check(
            foundation=foundation,
            column=column,
            N_sd_kN=N_sd,
            fck_MPa=fck,
            rho_x=0.005,
            rho_y=0.005,
            d_eff_m=d_eff,
        )

        # Perímetro crítico u1 = 2*(0.4+0.4) + 4*pi*0.55 = 1.6 + 6.9115 = 8.5115 m
        assert res.u1 == pytest.approx(8.5115, rel=1e-3)
        # Resistencia a cortante de punzonamiento sin armadura tau_rd (kPa)
        # xi = 1 + sqrt(200/550) = 1.6030
        # tau_rd = 0.12 * 1.6030 * (100 * 0.005 * 30)^(1/3) * 1000 = 474.4 kPa
        assert res.tau_rd == pytest.approx(474.4, rel=1e-2)
        assert res.is_ok is True
        assert res.utilization < 0.10

    def test_foundation_chain_complete_mock(self) -> None:
        """Verifica la cadena completa desde reacciones fixture hasta spec SAFE."""
        reactions = [
            Reaction(node_id="C1", case="COMB_ELU", fz_kN=500.0, fx_kN=10.0, fy_kN=5.0, mx_kNm=20.0, my_kNm=15.0),
            Reaction(node_id="C1", case="COMB_ELS", fz_kN=350.0, fx_kN=7.0, fy_kN=3.0, mx_kNm=12.0, my_kNm=10.0),
            Reaction(node_id="C2", case="COMB_ELU", fz_kN=750.0, fx_kN=15.0, fy_kN=8.0, mx_kNm=30.0, my_kNm=25.0),
            Reaction(node_id="C2", case="COMB_ELS", fz_kN=520.0, fx_kN=10.0, fy_kN=5.0, mx_kNm=18.0, my_kNm=16.0),
        ]

        soil_params = {
            "allowable_bearing_kPa": 250.0,
            "subgrade_modulus_ks_kN_m3": 50000.0,
        }

        col_coords = {
            "C1": (0.0, 0.0),
            "C2": (6.0, 0.0),
        }

        res = foundation_chain_from_etabs(
            reactions,
            soil_params,
            footing_thickness_m=0.60,
            concrete_fck_MPa=30.0,
            column_dimensions=(0.45, 0.45),
            column_coordinates=col_coords,
        )

        assert isinstance(res, FoundationChainResult)
        assert len(res.design_summary) == 2
        assert len(res.winkler_springs) == 2
        assert len(res.punching_checks) == 2

        # Sizing de C1: N=500 con mx=20/my=15 induce excentricidad, y el
        # dimensionador la cuenta vía área efectiva de Meyerhof. Ya NO es el axial
        # puro sqrt(500/250)=1.414->1.45 (que ignoraba los momentos que este mismo
        # test pasa): el valor honesto es 1.50 m, con hundimiento gobernando.
        assert res.design_summary["C1"]["B_m"] == pytest.approx(1.50)
        # Sizing de C2: N=750 con mx=30/my=25 -> 1.85 m (no el axial 1.732->1.75).
        assert res.design_summary["C2"]["B_m"] == pytest.approx(1.85)

        # Muelles Winkler (kz = ks · B², con la B honesta ya dimensionada)
        s_c1 = next(s for s in res.winkler_springs if s.joint_name == "C1")
        expected_kz_c1 = 50000.0 * (1.50 * 1.50)
        assert s_c1.kz_kN_m == pytest.approx(expected_kz_c1)

        # Spec SAFE
        spec = res.safe_model_spec
        assert spec["n_footings"] == 2
        assert spec["n_loads"] == 4  # 2 nudos x 2 combinaciones
        assert len(spec["footings"]) == 2
        assert len(spec["column_loads"]) == 4

        # Cargas por combinación en spec
        c1_elu = next(l for l in spec["column_loads"] if l["point_name"] == "C1" and l["case"] == "COMB_ELU")
        assert c1_elu["P"] == 500.0
        assert c1_elu["Vx"] == 10.0
        assert c1_elu["Mx"] == 20.0

    def test_foundation_chain_live_injection_mock(self) -> None:
        """Verifica que cuando se provee safe_client, la inyección live se invoca correctamente."""
        reactions = [
            Reaction(node_id="C1", case="COMB1", fz_kN=400.0, mx_kNm=10.0, my_kNm=10.0),
        ]
        soil_params = {"allowable_bearing_kPa": 200.0, "subgrade_modulus_ks_kN_m3": 40000.0}

        mock_safe = MagicMock()

        res = foundation_chain_from_etabs(
            reactions,
            soil_params,
            safe_client=mock_safe,
        )

        assert res.safe_injection_status is not None
        assert res.safe_injection_status["success"] is True
        assert mock_safe.add_mat_slab.called
        assert mock_safe.add_winkler_springs.called
        assert mock_safe.add_column_load.called


class TestPunchingApplicability:
    """Verificación de punzonamiento en zapatas compactas (EC2 §6.4.4(2)).
    
    El caso de zapata compacta donde 2d excede la planta pasa de declararse
    no aplicable a RESOLVERSE analizando perímetros a < 2d con tau_Rd escalado."""

    def test_compact_footing_resolves_via_reduced_perimeter(self) -> None:
        """1.2x1.2x0.50 con columna 0.40: A_u1=4.14 m2 > 1.44 m2 -> resuelto vía a < 2d."""
        from foundationdesignjm.core.geometry import Column, RectangularFoundation
        from foundationdesignjm.design.punching_shear import punching_shear_check

        res = punching_shear_check(
            foundation=RectangularFoundation(length=1200.0, width=1200.0, thickness=500.0),
            column=Column(length=400.0, width=400.0, pos_x=600.0, pos_y=600.0),
            N_sd_kN=281.1,
            fck_MPa=30.0,
            rho_x=0.005,
            rho_y=0.005,
            d_eff_m=0.45,
        )
        assert res.applicable is True
        assert res.is_compact is True
        assert res.verdict == "PASS"
        assert res.a_crit_m < 2.0 * 0.45
        assert res.is_ok is True

    def test_benchmark_footing_stays_applicable(self) -> None:
        """El benchmark AG13 (2.5x2.5, d=0.55): A_u1=5.72 < 6.25 -> aplicable y PASS."""
        from foundationdesignjm.core.geometry import Column, RectangularFoundation
        from foundationdesignjm.design.punching_shear import punching_shear_check

        res = punching_shear_check(
            foundation=RectangularFoundation(length=2500.0, width=2500.0, thickness=600.0),
            column=Column(length=400.0, width=400.0, pos_x=1250.0, pos_y=1250.0),
            N_sd_kN=800.0,
            fck_MPa=30.0,
            rho_x=0.005,
            rho_y=0.005,
            d_eff_m=0.55,
        )
        assert res.applicable is True
        assert res.is_compact is False
        assert res.verdict == "PASS"
        assert res.u1 == pytest.approx(8.5115, rel=1e-3)

    def test_memoria_reports_compact_footing_punching(self) -> None:
        """La memoria de la cadena reporta el chequeo EC2 6.4.4(2) para el caso compacto."""
        from jmstructural_common.model import Reaction
        from foundationdesignjm.integration.foundation_chain import foundation_chain_from_etabs, foundation_package
        import tempfile, os

        rx = [Reaction(node_id="1", case="ELU", fx_kN=0, fy_kN=0, fz_kN=281.1,
                       mx_kNm=0, my_kNm=0, mz_kNm=0)]
        with tempfile.TemporaryDirectory() as tmp:
            pkg = foundation_package(
                etabs_or_reactions=rx,
                soil_params={"allowable_bearing_kPa": 250.0,
                             "subgrade_modulus_ks_kN_m3": 40000.0,
                             "min_size_m": 1.2, "size_step_m": 0.05},
                footing_thickness_m=0.50,
                concrete_fck_MPa=30.0,
                column_dimensions=(0.40, 0.40),
                output_dir=tmp,
            )
            text = pkg.memoria_markdown
            assert "6.4" in text
