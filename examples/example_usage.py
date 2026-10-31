"""Quick example — central pad footing on dry sand, EC7 DA1 and DA2 checks."""

from foundationcalc import (
    BasePressureAnalysis,
    Column,
    CombinationEntry,
    DesignApproach,
    LimitState,
    LoadCombination,
    LoadType,
    PointLoad,
    RectangularFoundation,
    SoilLayer,
    SoilType,
    drained_bearing_capacity,
    get_partial_factors,
    utilization_ratio,
)


# 1. Geometry --------------------------------------------------------------
fdn = RectangularFoundation(
    length=2500.0, width=1500.0, thickness=500.0, embedment_depth=500.0
)
col = Column(length=400.0, width=400.0, pos_x=1250.0, pos_y=750.0)

# 2. Loads -----------------------------------------------------------------
g = PointLoad(name="G", fz=800.0, load_type=LoadType.PERMANENT)
q = PointLoad(name="Q", fz=450.0, load_type=LoadType.IMPOSED)

# 3. Soil (dry sand) -------------------------------------------------------
sand = SoilLayer(
    name="dry_sand",
    thickness=10.0,
    soil_type=SoilType.COHESIONLESS,
    friction_angle=35.0,
    cohesion=0.0,
    unit_weight=18.0,
)

print("=" * 70)
print("FoundationCalc - Pad footing on dry sand (EC7 example)")
print("=" * 70)
print(f"Footing: {fdn.length/1000:.1f} x {fdn.width/1000:.1f} x {fdn.thickness/1000:.2f} m")
print(f"  embedment depth: {fdn.depth_m:.2f} m, area: {fdn.area:.2f} m2")
print(f"Loads: G_k = {g.fz:.0f} kN, Q_k = {q.fz:.0f} kN  (centred)")
print(f"Soil: phi_k = {sand.friction_angle:.0f} deg, gamma_k = {sand.unit_weight:.0f} kN/m3")
print()

# 4. Run all three Design Approaches ---------------------------------------
for da in [DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2, DesignApproach.DA3]:
    pf = get_partial_factors(da, LimitState.GEO)

    # Self weight of the footing (γ_c = 25 kN/m³)
    W_Gk = fdn.area * fdn.thickness_m * 25.0

    combo = LoadCombination(
        name=f"ULS_{da.value}",
        entries=[
            CombinationEntry(load=g, factor=pf.actions.gamma_G_unfav),
            CombinationEntry(
                load=PointLoad(name="W_Gk", fz=W_Gk, load_type=LoadType.PERMANENT),
                factor=pf.actions.gamma_G_unfav,
            ),
            CombinationEntry(load=q, factor=pf.actions.gamma_Q_unfav),
        ],
    )
    V_d = combo.total_fz
    q_Ed = V_d / fdn.area

    res = drained_bearing_capacity(
        foundation=fdn,
        soil=sand,
        gamma_Rv=pf.resistance.gamma_Rv,
        gamma_phi=pf.soil.gamma_phi,
        gamma_c=pf.soil.gamma_c,
        gamma_gamma=pf.soil.gamma_gamma,
    )
    q_Rd = res.q_ult / pf.resistance.gamma_Rv
    util = utilization_ratio(q_Ed, q_Rd)

    print(f"--- {da.value} ---")
    print(f"  V_d         = {V_d:8.1f} kN")
    print(f"  q_Ed        = {q_Ed:8.1f} kPa")
    print(f"  phi_d       = {res.phi_d_deg:8.2f} deg")
    print(f"  N_q, N_c, N_g = {res.Nq:5.1f}, {res.Nc:5.1f}, {res.Ngamma:5.1f}")
    print(f"  s_q, s_c, s_g = {res.sq:5.2f}, {res.sc:5.2f}, {res.sgamma:5.2f}")
    print(f"  q_ult       = {res.q_ult:8.1f} kPa")
    print(f"  q_Rd        = {q_Rd:8.1f} kPa")
    print(f"  Utilization = {util*100:8.1f} %  {'OK' if util <= 1 else 'NOT OK'}")
    print()

# 5. Contact pressures (for a DA1-C1 load combo) ---------------------------
pf = get_partial_factors(DesignApproach.DA1_C1, LimitState.GEO)
combo = LoadCombination(
    name="ULS_DA1_C1",
    entries=[
        CombinationEntry(load=g, factor=pf.actions.gamma_G_unfav),
        CombinationEntry(load=q, factor=pf.actions.gamma_Q_unfav),
    ],
)
bpa = BasePressureAnalysis(fdn, col)
press = bpa.calculate_pressures(combo)
print("Contact pressures under DA1-C1:")
print(f"  q1, q2, q3, q4 = {press.q1:.1f}, {press.q2:.1f}, {press.q3:.1f}, {press.q4:.1f} kPa")
print(f"  q_max = {press.q_max:.1f} kPa,  regime = {press.regime.value}")
