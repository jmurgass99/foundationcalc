# 04 — EC7 Examples: Footings, Retaining Walls, Piles

> Extracted from: *UPC – Foundation Structures — "Examples of geotechnical design according to Eurocode 7"*.

## 4.1 ULS for spread footings

Failure modes that must be checked:
- **Loss of stability** (EQU — overturning).
- **Bearing failure** (GEO).
- **Sliding** (GEO).
- **Structural failure** (STR).
- **Combined failure** in ground + structure.

`E_d ≤ R_d` ⇒ `q_Ed ≤ q_Rd`.

### Design bearing pressure
```
q_Ed = ΣV_d / A' = [γ_G·(V_Gk + W_Gk) + γ_Q·V_Qk,1] / A'
```
- V_Gk = imposed permanent vertical action.
- W_Gk = self-weight of the footing.
- A' = **effective area** under eccentric loading.

### Middle-third / effective area
To avoid loss of contact:
```
e_B ≤ B/6       and       e_L ≤ L/6
A' = B' × L' = (B − 2·e_B) × (L − 2·e_L)
```

## 4.2 Drained bearing resistance (Brinch-Hansen / EC7 triple-N)

```
q_ult = c'·N_c·s_c·d_c·i_c·g_c·b_c
      + q'·N_q·s_q·d_q·i_q·g_q·b_q
      + γ'·B·N_γ·s_γ·d_γ·i_γ·g_γ·b_γ / 2
```

### Bearing capacity factors
| Author | N_q | N_c | N_γ |
|---|---|---|---|
| Reissner-Prandtl | e^(π·tan φ) · tan²(45° + φ/2) | (N_q − 1)·cot φ | — |
| Brinch-Hansen | id. | id. | 1.5·(N_q − 1)·tan φ |
| Meyerhof | id. | id. | (N_q − 1)·tan(1.4·φ) |
| Vesic | id. | id. | 2·(N_q + 1)·tan φ |
| **Chen (EC7)** | id. | id. | **2·(N_q − 1)·tan φ**  *(when δ ≥ φ/2, rough base)* |

### Shape factors (rectangle B×L)
| Factor | c | q | γ |
|---|---|---|---|
| s_x | 1 + (N_q·B) / (N_c·L) | 1 + (B/L)·sin φ | 1 − k·(B/L), k=0.3 in EC7 (B/H ≤ 1); Brinch-Hansen & Vesic k=0.4 |

Depth `d_x`, ground inclination `g_x`: no equations in EC7. Load inclination `i_x` and base inclination `b_x`: per EN 1997-1 Annex D.

### Undrained bearing resistance
```
R / A' = (π + 2)·c_u·b_c·s_c·i_c·d_c·g_c + q
s_c    = 1 + 0.12·(B/L) + 0.17·√(D/B)
q_Rd   = R_v,d / A' = (R_v,k / γ_R,v) / A'
```

## 4.3 Worked example — Pad footing on dry sand (Limit State GEO)

| Datum | Value |
|---|---|
| L × B | 2.5 × 1.5 m |
| Depth d | 0.5 m |
| V_Gk | 800 kN (central) |
| V_Qk | 450 kN (central) |
| φ_k | 35° |
| c'_k | 0 kPa |
| γ_k (sand) | 18 kN/m³ |
| γ_ck (RC) | 25 kN/m³ |

Self-weight W_Gk = γ_ck · L · B · d = 46.9 kN.

### DA-1 (A1+M1+R1 and A2+M2+R1)

| Quantity | DA1-C1 | DA1-C2 |
|---|---:|---:|
| γ_G / γ_Q | 1.35 / 1.50 | 1.00 / 1.30 |
| V_d (kN) | 1 818.3 | 1 431.9 |
| q_Ed (kPa) | 484.9 | 381.8 |
| γ_φ | 1.0 | 1.25 |
| φ_d (°) | 35 | 29.3 |
| N_q | 33.3 | 16.9 |
| N_c | 46.1 | 28.4 |
| N_γ | 45.2 | 17.8 |
| s_q | 1.34 | 1.29 |
| s_c | 1.35 | 1.31 |
| s_γ | 0.82 | 0.82 |
| q_ult,overburden | 402.8 | 196.9 kPa |
| q_ult,cohesion | 0 | 0 |
| q_ult,self-wt | 500.7 | 197.5 kPa |
| **Σ q_ult (kPa)** | **903.5** | **394.4** |
| γ_R,v | 1.0 | 1.0 |
| **q_Rd (kPa)** | **903.5** | **394.4** |
| **Λ_GEO (%)** | **54** | **97** |

→ Critical: DA1-C2 at 97% utilization.

### DA-2 (A1+M1+R2)
γ_G=1.35, γ_Q=1.5, γ_φ=γ_c=1.0, γ_R,v = **1.4**.
V_d = 1 818.3 kN, q_Ed = 484.9 kPa. q_ult = 903.5 kPa, q_Rd = 903.5/1.4 = **645.3 kPa**. Λ_GEO,2 = **75 %** (over-designed → safer than DA-1).

### DA-3 ((A1 or A2)+M2+R3)
γ_G=1.35, γ_Q=1.5, γ_φ=γ_c=1.25, γ_R,v = 1.0.
V_d = 1 818.3 kN, q_Ed = 484.9 kPa, q_Rd = **394.4 kPa**. Λ_GEO,3 = **123 %** → design **unsafe**, re-design required.

> **Conclusion**: For this footing, DA-3 is more onerous; DA-1 governs in the critical Combination 2; DA-2 may over-design. This illustrates why the choice of Design Approach matters and why National Annexes differ.

## 4.4 Lateral earth pressures (retaining walls)

### At-rest
```
σ'_o = q + γ·z
σ_h  = K_o · σ'_o + u
K_o  = (1 − sin φ') · OCR^(sin φ')
```
OCR = preconsolidation pressure / present effective overburden.

### Rankine — frictionless wall

```
Active   : σ'_a = σ'_o · K_a − 2·c'·√K_a     K_a = tan²(45° − φ'/2)
Passive  : σ'_p = σ'_o · K_p + 2·c'·√K_p     K_p = tan²(45° + φ'/2)
Tension crack depth: z_c = 2·c' / (γ·√K_a)
P_a = (1/2)·K_a·γ·H²            P_p = (1/2)·γ·H²·K_p
```
Slip planes: ±(45 + φ/2) for active, ±(45 − φ/2) for passive.

### Coulomb — wall friction δ' considered
```
K_a,Coulomb = sin²(β + φ') / { sin²β · sin(β − δ') · [1 + √(sin(φ'+δ')·sin(φ'−α) / (sin(β−δ')·sin(α+β)))]² }
K_p,Coulomb = sin²(β − φ') / { sin²β · sin(β + δ') · [1 − √(sin(φ'+δ')·sin(φ'+α) / (sin(β+δ')·sin(β+α)))]² }
```
Geometry: β = back-face inclination, α = backfill slope, δ' = wall friction.

### Wall friction and adhesion
```
δ_d = k · φ_cv,d
```
- k = 2/3 for precast concrete walls.
- k = 1 for cast-in-place concrete walls.

### Passive resistance — favourable action or resistance
| Factor | DA-1 C1 | DA-1 C2 | DA-2 | DA-3 |
|---|---|---|---|---|
| γ_G,fav | 1.0 | 1.0 | 1.0 | 1.0 |
| γ_R,e | 1.0 | 1.0 | 1.4 | 1.0 |

### Cantilever wall — wide heel (Rankine valid)
Heel wide enough if `b ≥ h · tan(45° − φ/2)`. Then no wall friction along the virtual back, and P'_a is inclined at β to the horizontal.

If heel is narrow (`b < b_min`), the backfill inside the inclined virtual plane is considered part of the wall:
```
P'_ah = P'_a · cos(θ + δ)
P'_av = P'_a · sin(θ + δ)
θ      = arctan(b / h)
```

### Mass gravity wall (Coulomb only)
```
σ'_ah = K_aγ·(∫γdz − u) + K_aq·q − K_ac·c'
u     = γ_w · (z − d_w) ≥ 0
K_aγ  = K_n · cos β · cos(β − θ)
K_aq  = K_n · cos²β
K_ac  = (K_n − 1) · cot φ
```

## 4.5 Worked example — Cantilever wall on clay (Limit State GEO, undrained)

| Datum | Value |
|---|---|
| Stem thickness t_s | 250 mm |
| Backfill height H | 3.0 m |
| Base width B | 2.7 m |
| Base thickness t_b | 300 mm |
| Toe length x | 0.5 m |
| Depth d | 0.5 m |
| γ_ck (RC) | 25 kN/m³ |
| Fill: φ_k=36°, c'_k=0, γ_k=18 kN/m³ | — |
| Clay below wall: c_uk,fdn=45 kPa, γ_k,fdn=22 kN/m³ | — |
| Surcharge q_Qk | 10 kPa |
| Unplanned excavation ΔH = min(10%H, 0.5m) | 0.30 m |

Design retained height H_d = H + ΔH = 3.3 m. Heel width b = B − t_s − x = 1.95 m.

### Self-weight resultants and moments (about toe)
| Item | W_Gk (kN/m) | Moment M_k (kN·m/m) |
|---|---:|---:|
| Wall base | 20.3 | 27.3 |
| Wall stem | 20.0 | 12.5 |
| Backfill over heel | 112.3 | 193.8 |
| **Total** | **152.6** | **233.6** |

### DA-1 results (A1+M1+R1 / A2+M2+R1)
| | DA1-C1 | DA1-C2 |
|---|---:|---:|
| φ_d | 36° | 30.2° |
| c'_d (fill) | 0 | 0 |
| c_ud,fdn (clay) | 45 | 32.1 kPa |
| b_min | 1.78 m | 2.01 m |
| K_a | 0.260 | 0.331 |
| V_d unfav | 239 | 181.2 kN/m |
| V_d fav | 152.6 | 152.6 kN/m |
| H_Ed total | 52.3 | 51.6 kN/m |
| M_Ed,dst | 68.9 | 69.0 kN·m/m |
| H_Rd (sliding) | 121.5 | 86.8 kN/m |
| e_B | 0.10 | 0.19 m |
| B' = B − 2·e_B | 2.50 | 2.32 m |
| i_c | 0.87 | 0.78 |
| q_ult | 204.8 | 133 kPa |
| q_Ed | 95.4 | 78 kPa |
| **Sliding Λ_GEO,1** | **43 %** | **59 %** |
| **Bearing Λ_GEO,1** | **47 %** | **59 %** |
| **Toppling Λ_GEO,1** | **30 %** | **30 %** |

### DA-2 / DA-3 summary
| | DA-2 | DA-3 |
|---|---:|---:|
| Sliding Λ | 47 % | 59 % |
| Bearing Λ | 65 % | 64 % |
| Toppling Λ | 30 % | 30 % |

→ Wall is safe for all three Design Approaches; DA-1 Combination 2 governs sliding+bearing.

## 4.6 ULS for piles

EC7 lists three design methods:
1. **Static or dynamic load tests** on working or trial piles.
2. **Calculation methods** — empirical or analytical.
3. **Observed performance** of comparable foundations.

Pile characteristic resistance:
```
R_bk = A_b · q_bk         (base)
R_sk = Σ A_s,i · q_sk,i   (shaft)
R_ck = R_bk + R_sk        (compression)
```

Use ξ factors (Annex A, tables A.9–A.11) to convert mean & min values from tests/profiles into characteristic value.

---

## Notes for `foundationdesignjm`

The example will be used as a **regression test** for the bearing-capacity module. Expected numbers for the pad footing on dry sand:
- DA1-C1: q_ult = 903.5 kPa, q_Rd = 903.5 kPa, Λ = 54 %.
- DA1-C2: q_ult = 394.4 kPa, q_Rd = 394.4 kPa, Λ = 97 %.
- DA-2: q_Rd = 645.3 kPa, Λ = 75 %.
- DA-3: q_Rd = 394.4 kPa, Λ = 123 % (fails).

For the cantilever wall example:
- DA1-C2 sliding: H_Ed = 51.6, H_Rd = 86.8, Λ = 59 %.
- DA1-C2 bearing: q_Ed = 78, q_Rd = 133, Λ = 59 %.
- DA-2 bearing: Λ = 65 %.
- DA-3 bearing: Λ = 64 %.
