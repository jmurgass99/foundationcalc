"""Tests para ACI 318-19 Cap. 17 — anclajes a concreto."""
from __future__ import annotations

import pytest

from foundationdesignjm.codes.aci318_anchorage import (
    AnchorCondition,
    interaction,
    shear_capacity,
    tension_capacity,
)


class TestTension:
    def test_steel_typical(self):
        r = tension_capacity(
            Nu=20_000, Ase_N=157, futa=860,
            fc=28, hef=200, ca1=300, Abrg=400, cracked=True,
        )
        assert r.phi_Nn > 0
        assert r.governing in {"steel", "breakout", "pullout", "blowout"}
        assert 0 < r.utilization

    def test_uncracked_higher_breakout(self):
        cracked = tension_capacity(Nu=1, Ase_N=157, futa=860,
                                     fc=28, hef=200, ca1=300, Abrg=400,
                                     cracked=True)
        uncracked = tension_capacity(Nu=1, Ase_N=157, futa=860,
                                       fc=28, hef=200, ca1=300, Abrg=400,
                                       condition=AnchorCondition.B,
                                       cracked=False)
        assert uncracked.Ncb > cracked.Ncb

    def test_no_head_disables_pullout(self):
        r = tension_capacity(Nu=1, Ase_N=157, futa=860,
                              fc=28, hef=200, ca1=300, Abrg=0, cracked=True)
        assert r.Npn == float("inf")
        assert r.Nsb == float("inf")


class TestShear:
    def test_basic(self):
        r = shear_capacity(Vu=10_000, Ase_V=157, futa=860,
                            fc=28, hef=200, ca1=300, da=16)
        assert r.phi_Vn > 0
        assert r.governing in {"steel", "breakout", "pryout"}


class TestInteraction:
    def test_combined(self):
        r = interaction(Nu=20_000, phi_Nn=30_000,
                         Vu=10_000, phi_Vn=20_000)
        assert r.rule == "combined_5/3"
        assert r.interaction > 0

    def test_tension_only(self):
        r = interaction(Nu=20_000, phi_Nn=30_000,
                         Vu=100, phi_Vn=20_000)
        assert r.rule == "tension_only"

    def test_shear_only(self):
        r = interaction(Nu=100, phi_Nn=30_000,
                         Vu=10_000, phi_Vn=20_000)
        assert r.rule == "shear_only"
