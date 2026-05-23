"""Tower-crane foundation example - shows initial design fails OOS, then redesigns.

Typical input loads from manufacturer manual:
- Service:      N = 700 kN, M = 2400 kN.m, V = 60 kN
- Out-of-service (storm): N = 500 kN, M = 3200 kN.m, V = 130 kN
- Dynamic factor on the in-service hook load: 1.10

Soil: dense gravelly sand, phi_k = 36 deg, gamma_k = 19 kN/m3, 1.5 m of backfill above pad.
"""

from foundationdesignjm import (
    Column,
    Concrete,
    CraneLoadCase,
    CraneLoadState,
    DesignApproach,
    RectangularFoundation,
    SoilLayer,
    SoilType,
    crane_foundation_check,
)


# --- Soil & concrete ------------------------------------------------------
sand = SoilLayer(
    name="dense_gravelly_sand", thickness=12.0, soil_type=SoilType.COHESIONLESS,
    friction_angle=36.0, cohesion=0.0, unit_weight=19.0,
)
C30 = Concrete(name="C30/37", fck=30.0)

# --- Crane load cases (manufacturer's data) -------------------------------
service = CraneLoadCase(
    state=CraneLoadState.SERVICE, name="Service",
    N_kN=700.0, M_x_kNm=2400.0, M_y_kNm=0.0,
    V_x_kN=0.0, V_y_kN=60.0,
    is_wind_dominant=False, dynamic_factor=1.10,
)
oos = CraneLoadCase(
    state=CraneLoadState.OUT_OF_SERVICE, name="Out-of-service (storm)",
    N_kN=500.0, M_x_kNm=3200.0, M_y_kNm=0.0,
    V_x_kN=0.0, V_y_kN=130.0,
    is_wind_dominant=True, dynamic_factor=1.0,
)


def run_block(pad: RectangularFoundation, mast: Column, label: str) -> None:
    print(f"\n>>>>>>>>>>  {label}")
    print(f"           pad {pad.length/1000} x {pad.width/1000} x {pad.thickness/1000} m, "
          f"embedment {pad.embedment_depth/1000:.1f} m")
    pad_weight = pad.area * pad.thickness_m * C30.unit_weight
    soil_weight = pad.area * 1.5 * sand.unit_weight
    print(f"           W_pad = {pad_weight:.0f} kN, W_soil_overburden = {soil_weight:.0f} kN, "
          f"W_total = {pad_weight + soil_weight:.0f} kN")

    for lc in [service, oos]:
        print(f"\n  --- Load case: {lc.name} ---")
        print(f"    Inputs: N = {lc.N_kN} kN, M = {lc.M_resultant:.0f} kN.m, V = {lc.V_resultant:.0f} kN")
        e0 = lc.M_resultant / lc.N_kN
        regime_hint = "PARTIAL UPLIFT" if e0 > pad.length_m / 6.0 else "no uplift"
        print(f"    e0 (column base) = {e0:.2f} m  -> {regime_hint}")
        for da in [DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2]:
            res = crane_foundation_check(
                foundation=pad, column=mast, load_case=lc,
                soil=sand, concrete=C30,
                design_approach=da, drained=True, delta_factor=1.0,
                soil_overburden_depth_mm=1500.0,
                soil_unit_weight_overburden=sand.unit_weight,
            )
            flag = "OK" if res.all_ok else "FAILS"
            q_max_str = f"{res.q_max:6.1f}" if res.q_max != float("inf") else "  inf"
            print(f"    [{da.value:7s}]  bearing {res.bearing_utilization*100:6.1f}%  "
                  f"sliding {res.sliding_utilization*100:5.1f}%  "
                  f"toppling {res.overturning_utilization*100:5.1f}%  "
                  f"q_max = {q_max_str} kPa  "
                  f"regime = {res.regime:14s}  -> {flag}")


print("=" * 80)
print("FoundationDesignJm - Tower crane foundation design")
print("=" * 80)

# Initial design — too small for the storm case
pad_initial = RectangularFoundation(
    length=4500.0, width=4500.0, thickness=1400.0, embedment_depth=1500.0,
)
mast_initial = Column(length=2000.0, width=2000.0, pos_x=2250.0, pos_y=2250.0)
run_block(pad_initial, mast_initial, "Initial design (4.5 x 4.5 x 1.4 m)")

# Redesign — bigger pad to resist the storm overturning moment
pad_redesign = RectangularFoundation(
    length=6500.0, width=6500.0, thickness=1600.0, embedment_depth=1500.0,
)
mast_redesign = Column(length=2000.0, width=2000.0, pos_x=3250.0, pos_y=3250.0)
run_block(pad_redesign, mast_redesign, "Redesign (6.5 x 6.5 x 1.6 m)")
