"""Smoke tests para los modulos portados desde fastsap.

Cubre:
- aisc_360 (vigas/columnas) + aisc_360_db (catalogo)
- aisc_360_connections (placa base, soldadura, pernos)
- memoria_builder + reports (PDF maestra)
- fema_p58 (fragilidad lognormal)
"""
from __future__ import annotations

import os
import tempfile


# ---------------------------------------------------------------------------
# AISC 360 vigas/columnas + catalogo
# ---------------------------------------------------------------------------

class TestAISC360:
    def test_shape_from_catalog(self):
        from foundationdesignjm.codes.aisc_360 import SteelShape
        s = SteelShape.from_aisc("W14X90")
        for attr in ("A", "d", "bf", "tf", "tw", "Ix", "Iy",
                      "Zx", "Sx", "rx", "ry", "J", "Cw"):
            assert getattr(s, attr) > 0

    def test_beam_flexure(self):
        from foundationdesignjm.codes.aisc_360 import (
            SteelShape, design_beam_flexure,
        )
        s = SteelShape.from_aisc("W14X90")
        r = design_beam_flexure(s, Lb=2500.0, Fy=345.0, Mu=300e6)
        assert r.phi_Mn > 0
        assert r.regime in {"plastic", "inelastic_LTB", "elastic_LTB"}

    def test_column(self):
        from foundationdesignjm.codes.aisc_360 import (
            SteelShape, design_column,
        )
        s = SteelShape.from_aisc("W14X90")
        r = design_column(s, KL=3500.0, Fy=345.0, Pu=1500e3)
        assert r.phi_Pn > 0
        assert r.utilization > 0

    def test_interaction_H1(self):
        from foundationdesignjm.codes.aisc_360 import interaction_H1
        r = interaction_H1(Pu=1800e3, phi_Pn=2400e3,
                            Mux=400e6, phi_Mnx=600e6)
        assert r.formula in {"H1-1a", "H1-1b"}
        assert r.interaction > 0


# ---------------------------------------------------------------------------
# AISC 360 conexiones
# ---------------------------------------------------------------------------

class TestAISCConnections:
    def test_base_plate(self):
        from foundationdesignjm.codes.aisc_360_connections import (
            design_base_plate,
        )
        r = design_base_plate(Pu=500e3, fc=28, B=400, N=400,
                                d=300, bf=200, Fy_plate=250)
        assert r.tp_req > 0
        assert r.A1 == 400 * 400

    def test_fillet_weld(self):
        from foundationdesignjm.codes.aisc_360_connections import (
            fillet_weld_strength,
        )
        r = fillet_weld_strength(w=6, FEXX=485, theta_deg=0, Ru=500)
        assert r.phi_Rn_per_mm > 0

    def test_bolt_shear(self):
        from foundationdesignjm.codes.aisc_360_connections import (
            bolt_shear_capacity,
        )
        r = bolt_shear_capacity(Ab=285, Fnv=372, n_bolts=4, Vu=200e3)
        assert r.phi_Rn > 0


# ---------------------------------------------------------------------------
# Memoria maestra PDF
# ---------------------------------------------------------------------------

class TestMemoriaMaestra:
    def test_minimal_pdf(self):
        from foundationdesignjm.memoria_builder import MemoriaBuilder
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            p = f.name
        try:
            out = (MemoriaBuilder("Test FDJM", "Bogota", "JM")
                    .with_codes("EC7", "EC8")
                    .with_materials(fc=28, fy=420)
                    .with_seismic(code="EC8", I=1.0, R=3.0)
                    .with_conclusions("Cumple.")
                    .save(p))
            assert os.path.exists(out)
            with open(out, "rb") as fh:
                assert fh.read(4) == b"%PDF"
        finally:
            os.unlink(p)


# ---------------------------------------------------------------------------
# FEMA P-58 fragilidad
# ---------------------------------------------------------------------------

class TestFemaP58:
    def test_lognormal_fragility(self):
        from foundationdesignjm.codes.fema_p58.fragility import (
            LognormalFragility,
        )
        f = LognormalFragility(theta=0.01, beta=0.4)
        assert 0 < f.p_exceed(edp=0.005) < 0.5
        assert 0.5 < f.p_exceed(edp=0.020) < 1.0

    def test_monotonic(self):
        from foundationdesignjm.codes.fema_p58.fragility import (
            LognormalFragility,
        )
        f = LognormalFragility(theta=0.01, beta=0.4)
        assert f.p_exceed(0.005) < f.p_exceed(0.010) < f.p_exceed(0.020)
