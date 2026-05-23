"""Advanced foundation design example — uses current API (v0.2+)."""
from foundationdesignjm import (
    BasePressureAnalysis,
    Column,
    CombinationEntry,
    Concrete,
    LoadCombination,
    LoadType,
    PointLoad,
    RectangularFoundation,
    ReinforcingSteel,
    Soil,
    flexural_reinforcement,
    overturning_check,
    punching_shear_check,
)

# 1. Materials + soil
concrete = Concrete(fck=30)
steel = ReinforcingSteel(fyk=500)
soil = Soil(bearing_capacity=250, unit_weight=18, friction_angle=32)

# 2. Geometry (mm)
fdn = RectangularFoundation(length=2800, width=2800, thickness=700)
col = Column(length=450, width=450, pos_x=1400, pos_y=1400)

# 3. ULS loading
g_load = PointLoad(fz=1200, load_type=LoadType.PERMANENT)
q_load = PointLoad(fz=500, mx=80, my=40, load_type=LoadType.IMPOSED)
uls_combo = LoadCombination(
    name="ULS",
    entries=[
        CombinationEntry(load=g_load, factor=1.35),
        CombinationEntry(load=q_load, factor=1.5),
    ],
)

print("--- FoundationDesignJm: Advanced Design Report ---")

# A. Base pressures
pressures = BasePressureAnalysis(fdn, col).calculate_pressures(uls_combo)
print(f"Base pressures: q_max={pressures.q_max:.1f} kPa, q_min={pressures.q_min:.1f} kPa")

# B. Stability (overturning) — about the long edge of the footing
L_m = fdn.length / 1_000.0
ot = overturning_check(
    M_dst_d=abs(uls_combo.total_my) + abs(uls_combo.total_mx),
    M_stb_d=uls_combo.total_fz * L_m / 2.0,
    V_d=uls_combo.total_fz,
    B=L_m,
)
print(f"Overturning: util={ot.utilization:.2f} ({'PASS' if ot.is_ok else 'FAIL'})")

# C. Bending reinforcement at column face
L_eff_m = (fdn.length - col.length) / 2_000.0
M_Ed_kNm = pressures.q_max * L_eff_m ** 2 / 2 * (fdn.width / 1_000.0)
d_mm = fdn.thickness - 50
rebar = flexural_reinforcement(
    M_Ed_kNm=M_Ed_kNm, b_mm=fdn.width, d_mm=d_mm,
    concrete=concrete, steel=steel,
)
print(f"Bending: As_req={rebar.As_required:.0f} mm² (b={fdn.width} mm)")

# D. Punching shear at 2d
d_eff_m = d_mm / 1_000.0
ps = punching_shear_check(
    foundation=fdn, column=col,
    N_sd_kN=uls_combo.total_fz, fck_MPa=concrete.fck,
    rho_x=0.0015, rho_y=0.0015, d_eff_m=d_eff_m,
)
print(f"Punching: util={ps.utilization:.2f} ({'PASS' if ps.is_ok else 'FAIL'})")
print("--------------------------------------------------")
