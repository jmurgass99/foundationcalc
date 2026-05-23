"""End-to-end CPT → SSI → seismic dynamic → FEMA P-58 loss pipeline.

This example wires `FoundationDesignJm` and `DynamicsJm` together:

1. A CPT log defines the soil profile (FoundationDesignJm).
2. Gazetas 1991 → 6-DOF foundation impedance (FoundationDesignJm.dynamics).
3. Veletsos-Meek SSI period elongation (FoundationDesignJm.integration).
4. Newmark β dynamic response with / without base isolation
   (DynamicsJm.solvers).
5. FEMA P-58 SM1 model → expected repair cost in USD
   (DynamicsJm.risk, ported from EaRL).

Requires DynamicsJm to be importable. Add its parent folder to
PYTHONPATH or run with:

    PYTHONPATH=../DynamicsJm/DynamicsJm python -m examples.dynamicsjm_bridge_example

Run via:   python -m examples.dynamicsjm_bridge_example
"""

from __future__ import annotations

import os
import sys

import numpy as np

# Optional: locate DynamicsJm if not already on the path
_DEFAULT_DYNAMICSJM = os.path.join(
    os.path.dirname(__file__), "..", "..", "DynamicsJm", "DynamicsJm",
)
_DEFAULT_DYNAMICSJM = os.path.abspath(_DEFAULT_DYNAMICSJM)
if os.path.isdir(_DEFAULT_DYNAMICSJM) and _DEFAULT_DYNAMICSJM not in sys.path:
    sys.path.insert(0, _DEFAULT_DYNAMICSJM)

from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
from foundationdesignjm.core.geometry import RectangularFoundation
from foundationdesignjm.integration.dynamicsjm_bridge import (
    DYNAMICSJM_AVAILABLE,
    cpt_to_seismic_loss_pipeline,
)


def _build_cpt() -> CPTProfile:
    """Sand-clay-sand profile typical of a Mediterranean coastal site."""
    readings = []
    for d in [0.5, 1, 1.5, 2, 2.5, 3]:
        readings.append(CPTReading(depth=d, q_c_MPa=8.0, f_s_kPa=50))
    for d in [4, 5, 6, 7]:
        readings.append(CPTReading(depth=d, q_c_MPa=1.5, f_s_kPa=50, u_2_kPa=40))
    for d in [8, 10, 12, 15]:
        readings.append(CPTReading(depth=d, q_c_MPa=18.0, f_s_kPa=80))
    return CPTProfile(readings=readings, water_table_depth_m=3.0)


def _build_ground_motion():
    """Decaying sinusoidal pulse, peak ~ 0.5 g."""
    t = np.linspace(0, 10, 1000)
    ag = 0.5 * 9.81 * np.sin(2 * np.pi * 1.5 * t) * np.exp(-0.2 * t)
    return t, ag


def main() -> None:
    print("=" * 78)
    print("FoundationDesignJm + DynamicsJm: CPT -> SSI -> Dynamic -> FEMA P-58")
    print("=" * 78)

    if not DYNAMICSJM_AVAILABLE:
        print("\nDynamicsJm not importable from this Python session.")
        print(f"Add to PYTHONPATH: {_DEFAULT_DYNAMICSJM}")
        return

    # Bring the isolator class in only after we know DynamicsJm is on path
    from dynamicsjm.control.base_isolation import BilinearIsolator

    cpt = _build_cpt()
    pad = RectangularFoundation(length=3000, width=3000, thickness=500,
                                embedment_depth=1500)
    t, ag = _build_ground_motion()

    # ---------- Scenario A: no isolation ----------------------------------
    res_fix = cpt_to_seismic_loss_pipeline(
        cpt=cpt, foundation=pad,
        building_mass_kg=50000, building_height_m=3.0,
        building_T_fixed_s=0.40,
        ground_motion_t_s=t, ground_motion_a_g=ag,
        isolator=None,
    )
    # ---------- Scenario B: base-isolated (LRB) ---------------------------
    isolator = BilinearIsolator(k1=1e6, k2=0.1e6, q_y=50000, damping_ratio=0.10)
    res_iso = cpt_to_seismic_loss_pipeline(
        cpt=cpt, foundation=pad,
        building_mass_kg=50000, building_height_m=3.0,
        building_T_fixed_s=0.40,
        ground_motion_t_s=t, ground_motion_a_g=ag,
        isolator=isolator,
    )

    print(f"\nCPT-derived soil parameters:")
    print(f"  G_max (avg in 2B influence)  = {res_fix.impedance.G_MPa:.1f} MPa")
    print(f"  V_s (from G_max)             = {res_fix.impedance.V_s():.0f} m/s")

    print(f"\nSSI (Veletsos-Meek):")
    print(f"  T_fixed = {res_fix.ssi_fixed.T_fixed:.3f} s")
    print(f"  T_ssi   = {res_fix.ssi_fixed.T_ssi:.3f} s "
          f"(elongation x{res_fix.ssi_fixed.period_elongation:.3f})")
    print(f"  zeta_fixed = {res_fix.ssi_fixed.zeta_fixed},  "
          f"zeta_ssi = {res_fix.ssi_fixed.zeta_ssi:.4f}")

    print(f"\nBase isolation:")
    print(f"  T_iso = {res_iso.ssi_isolated.T_ssi:.3f} s "
          f"(period ratio T_iso / T_fix = "
          f"{res_iso.ssi_isolated.T_ssi / res_iso.ssi_fixed.T_fixed:.2f})")

    print(f"\nDynamic response (peak inter-story drift ratio):")
    print(f"  Fixed base (no isolator):  IDR = {res_fix.peak_idr_fixed:.4f}")
    print(f"  Base-isolated:             IDR = {res_iso.peak_idr_isolated:.4f}")

    print(f"\nFEMA P-58 SM1 expected repair cost (50th percentile):")
    print(f"  Fixed base:        ${res_fix.loss_fixed_USD:>12,.2f}")
    print(f"  Base-isolated:     ${res_iso.loss_isolated_USD:>12,.2f}")
    if res_iso.loss_reduction_pct is not None:
        print(f"  Loss reduction:    {res_iso.loss_reduction_pct:.1f} %")

    print()
    print("Loop closed: CPT data -> bearing capacity & settlement (existing) ")
    print("           + SSI dynamic properties (Gazetas)")
    print("           + dynamic response (DynamicsJm Newmark)")
    print("           + economic loss (FEMA P-58 via DynamicsJm.risk, from EaRL).")


if __name__ == "__main__":
    main()
