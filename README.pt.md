# foundationcalc — dimensionamento de fundações em Python: EN 1997-1, EN 1992-1-1, ACI 318, muros, estacas, ensoleiramentos e sapatas

[Español](README.md) · [English](README.en.md) · **Português** · [Italiano](README.it.md)

Cálculo geotécnico e estrutural de fundações superficiais e profundas: capacidade resistente ao carregamento completa segundo a EN 1997-1 Anexo D (abordagens DA1, DA2 e DA3, área efetiva de Meyerhof, drenada e não drenada), pressões de contacto com descolamento, assentamentos elásticos de Steinbrenner e consolidação 1D de Terzaghi, correlações CPT e SPT, flexão de sapatas e punçoamento biaxial segundo o Eurocódigo 2 (§6.4 perímetros de controlo dentro de 2d) e a ACI 318-19 (§22.6 momento desequilibrado γ_v e J_c), sapatas combinadas e vigas de equilíbrio (NSR-10 / EC8), sapatas para gruas-torre, muros em consola, de cave, de gravidade, de contrafortes, cortinas e terra armada (MSE), estacas axiais (α, β, fatores de correlação ξ e normas EN/AASHTO/AS 2159), curvas p-y por diferenças finitas, grupos rígidos, ensoleiramentos Mindlin sobre fundação de Winkler e API REST com FastAPI. Dependências: `pydantic`, `reportlab`.

[![CI](https://github.com/jmurgass99/foundationcalc/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/foundationcalc/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Que problema resolve

O dimensionamento de fundações liga a mecânica dos solos ao betão armado, dois mundos que costumam resolver-se em programas desligados: folhas de cálculo para a tensão admissível e programas de barras ou de elementos finitos para as armaduras. Nessa fronteira perdem-se verificações críticas: se a área efetiva de Meyerhof reduz a capacidade resistente com a excentricidade real, se o punçoamento em sapatas compactas exige varrer perímetros a distâncias inferiores a 2d segundo a EN 1992-1-1 §6.4.4(2), se o momento desequilibrado na ACI 318-19 ativa a fração γ_v sobre o perímetro crítico, ou se a estabilidade de um muro em DA1-C2 deve ser avaliada com o ângulo de atrito minorado tan(φ_d) = tan(φ)/1,25.

O `foundationcalc` implementa estas verificações de forma modular, transparente e reprodutível. Cada cálculo expõe os seus parâmetros intermédios e está ancorado em soluções fechadas, fichas resolvidas do mestrado (W00675 de capacidade resistente, W00678 de Mononobe-Okabe, W00681 de sapata contínua DA2) e exemplos normativos contrastados.

**Use-o quando**

- precisar da capacidade resistente analítica da EN 1997-1 Anexo D com todos os fatores de inclinação, forma e profundidade, avaliada segundo as abordagens DA1 (combinações 1 e 2), DA2 e DA3;
- calcular pressões de contacto elásticas com verificação estrita do núcleo central e resolução exata do diagrama triangular em caso de descolamento (sem tensões de tração artificiais);
- verificar o punçoamento de sapatas segundo a EN 1992-1-1 varrendo perímetros de controlo a distâncias a < 2d com a redução 2d/a, ou segundo a ACI 318-19 considerando a excentricidade e o momento polar J_c;
- dimensionar sapatas combinadas ou trapezoidais ajustando o centroide exatamente à resultante das cargas para anular excentricidades;
- dimensionar muros de suporte (consola, cave escorada, gravidade, contrafortes, estacas-pranchas ou terra armada MSE) com as combinações EQU, STR e GEO do Eurocódigo 7;
- avaliar estacas sob carga axial (fuste e ponta por estratos, fatores de correlação ξ_3 / ξ_4) ou curvas p-y laterais por diferenças finitas acopladas;
- preparar modelos de ensoleiramentos sobre molas elásticas de Winkler (placa de Mindlin) ou quiser orquestrar uma cadeia de cálculo automatizada por API REST.

**Não o use para**

- análise de estabilidade global de taludes pelo método das fatias (use o `slipcircle`);
- modelos geotécnicos tridimensionais elastoplásticos avançados com descontinuidades ou estados transitórios de escoamento de água (use PLAXIS ou FLAC);
- dimensionamento de estacas em rocha com fraturação complexa ou erosão hidráulica dinâmica não uniforme sem estudos específicos;
- interação solo-estrutura com degradação cíclica não linear avançada sem calibração experimental.

## Instalação

```bash
pip install git+https://github.com/jmurgass99/foundationcalc.git
```

Extras opcionais: `numeric` (NumPy, SciPy, Pandas), `plot` (Matplotlib, Plotly), `api` (FastAPI, Uvicorn, HTTPX), `memos` (Handcalcs), `test` (Pytest, Hypothesis). Para desenvolvimento:

```bash
git clone https://github.com/jmurgass99/foundationcalc.git
cd foundationcalc
pip install -e ".[test,api,numeric,memos]"
pytest -q
```

## Capacidades

| Capacidade | Módulos | Norma ou referência | Casos de uso |
|---|---|---|---|
| Capacidade resistente e tensões no terreno: equação completa da EN 1997-1 Anexo D (drenada e não drenada), área efetiva de Meyerhof, N_γ por autor (Vesić, Meyerhof, Hansen), abordagens DA1/DA2/DA3, Boussinesq (pontual, linha, faixa, retângulo) e Steinbrenner | `analysis.bearing_capacity`, `analysis.stress`, `analysis.consolidation`, `analysis.stability` | EN 1997-1:2004 Anexo D; Boussinesq (1885); Steinbrenner (1934); Vesić (1973); Meyerhof (1963) | [5 casos](#1-capacidade-resistente-e-tensões-no-terreno) |
| Assentamentos, consolidação e ensaios in situ: consolidação 1D de Terzaghi (séries U–T_v e aproximações), argilas OC e NC, perfis CPT (Robertson I_c, tipo de solo SBT, φ' e c_u) e correções de energia/sobrecarga SPT N_60 e N_1(60) | `analysis.consolidation`, `analysis.cpt`, `analysis.spt`, `analysis.cpt_to_design` | Terzaghi (1943); Robertson (1990, 2009); Kulhawy e Mayne (1990); Skempton (1986); Hatanaka e Uchida (1996) | [4 casos](#2-assentamentos-ensaios-in-situ-cptspt-e-consolidação) |
| Fundação superficial, flexão, punçoamento e sismo: núcleo e descolamento, flexão EC2, punçoamento EC2 (varrimento a < 2d) e ACI 318-19 (γ_v e J_c), sapatas combinadas, grua-torre, sismo EN 1998-5 (inércia do bloco) e vigas de equilíbrio/lintéis (NSR-10 / EC8) | `design.isolated_footing`, `design.punching_shear`, `design.reinforcement`, `design.combined_footing`, `design.crane_pad`, `analysis.seismic_footing`, `design.strap_footing` | EN 1992-1-1 §6.4 e §9.8; ACI 318-19 §22.6; EN 1998-5 §5.4; NSR-10 A.3.6.4.2 | [8 casos](#3-fundação-superficial-pressões-flexão-punçoamento-e-sismo) |
| Muros de suporte e impulsos: coeficientes de Rankine e Coulomb com tardoz inclinado, K_0 com OCR, muros em consola por DA1/DA2/DA3, muros de cave escorados e subpressão, muros de gravidade, contrafortes, cortinas com escoras/ancoragens e terra armada (MSE) | `analysis.earth_pressure`, `design.retaining_wall`, `design.basement_wall`, `design.gravity_wall`, `design.counterfort_wall`, `design.diaphragm_wall`, `design.mse_wall` | EN 1997-1 §9; Coulomb (1776); Rankine (1857); FHWA-NHI-10-024 (MSE); Bowles (1996) | [6 casos](#4-muros-de-suporte-e-impulsos) |
| Estacas e fundações profundas: capacidade axial EN 1997-1 (métodos α e β, fatores de correlação ξ_3/ξ_4), fatores de cálculo multinorma (AASHTO, AS 2159), microestacas Bustamante-Doix, atrito negativo, grupo rígido de Engesser e curvas p-y por diferenças finitas | `analysis.pile_capacity`, `analysis.pile_lateral`, `design.pile_group`, `pile_capacity_multi` | EN 1997-1 §7; AASHTO LRFD; AS 2159; Bustamante e Doix (1985); Matlock (1970); Reese (1974) | [5 casos](#5-estacas-e-fundações-profundas) |
| Ensoleiramentos, cadeia integral e API REST: ensoleiramento Mindlin sobre fundação de Winkler com descolamento elastoplástico, exportação SAFE/SAP2000, cadeia integral de dimensionamento e API REST FastAPI | `analysis.mat_foundation`, `integration.foundation_chain`, `api.app`, `services.footings` | Mindlin (1936); Winkler (1867); CSI SAFE/SAP2000; FastAPI | [2 casos](#6-ensoleiramentos-cadeia-integral-e-api-rest) |

Os 30 scripts de `examples/` são executados no CI como subprocessos isolados (`tests/test_examples.py`); a sua saída real em `examples/output/` é a que se transcreve a seguir.

## Casos de uso

As saídas reproduzem-se exatamente como os scripts as imprimem, em espanhol.

### 1. Capacidade resistente e tensões no terreno

#### Sapata sobre areia segundo a EN 1997-1 Anexo D: abordagens DA1, DA2 e DA3 face ao cálculo manual

<details><summary>Saída real de <code>python examples/bearing_capacity_en1997_annex_d_square_pad_on_sand_da1_da2_da3_partial_factors_vs_hand_calc.py</code></summary>

```text
Zapata 2.5 × 2.5 m a D = 1.0 m; arena φ'k = 32.0°, γ = 19.0 kN/m³; Gk = 1000 kN, Qk = 400 kN
A mano: N_q = 23.177, N_γ = 27.715, s_q = 1.5299, s_γ = 0.7; q_ult = 19.0·23.18·1.530 + ½·19.0·2.5·27.72·0.7 = 1134.5 kPa
Paquete: N_q = 23.177, N_γ = 27.715, q_ult = 1134.5 kPa (diferencia +0.0000 %)

Enfoque     γG    γQ    γφ   γRv  φd [°] q_ult [kPa]  R_d [kN]  V_d [kN]  V_d/R_d
DA1-C1    1.35  1.50  1.00  1.00   32.00      1134.5      7090      1950    0.275
DA1-C2    1.00  1.30  1.25  1.00   26.56       538.7      3367      1520    0.451
DA2       1.35  1.50  1.00  1.40   32.00      1134.5      5065      1950    0.385
DA3       1.35  1.50  1.25  1.00   26.56       538.7      3367      1950    0.579

Gobierna DA3 con V_d/R_d = 0.579: la zapata cumple en los cuatro enfoques.
DA1-C2 reduce φ a 26.56°: q_ult pasa a 0.47 veces el de DA1-C1, mientras la acción solo baja a 0.78 veces; por eso su relación (0.451) supera a la de DA1-C1 (0.275).

Perfil SPAIN del paquete (DA2, γ_R;v = 2.15): R_d = 3298 kN, V_d/R_d = 0.591. El valor 2,15 está tomado tal como lo trae el módulo y no se ha contrastado aquí con el anejo nacional.
Límites: un solo estrato en la cota de apoyo, sin nivel freático (γ' = γ) y sin factores de profundidad, como el Anexo D; para perfiles estratificados, `multi_layer_bearing_capacity` (heurística declarada).
```

</details>

#### Argila não drenada com carga inclinada e excêntrica: área efetiva e comparação dos fatores N_γ

<details><summary>Saída real de <code>python examples/bearing_capacity_undrained_clay_inclined_eccentric_load_effective_area_and_ngamma_by_author.py</code></summary>

```text
Zapata 2.0 × 3.0 m, D = 1.2 m, c_u = 60.0 kPa; V = 900 kN, H = 80 kN, e = 0.15 m
A mano: B' = 2.00 m, L' = 2.70 m, A' = 5.40 m², s_c = 1.1481, i_c = 0.9339; q_ult = 5,1416·60·1.1481·0.9339 + 22.8 = 353.6 kPa
Paquete: A' = 5.40 m², s_c = 1.1481, i_c = 0.9339, q_ult = 353.6 kPa (diferencia +0.0000 %); R_k = 1909 kN, V/R_k = 0.471
  γ_R;v = 1.0: R_d = 1909 kN -> V/R_d = 0.471 (cumple)
  γ_R;v = 1.4: R_d = 1364 kN -> V/R_d = 0.660 (cumple)

Barrido de la carga horizontal (misma V y e):
   H [kN]  H/(A·c_u)    i_c q_ult [kPa]
        0      0.000  1.000       377.0
       80      0.247  0.934       353.6
      160      0.494  0.856       325.9
      240      0.741  0.755       290.1
      324      1.000  0.500       199.9
  Con H = A'·c_u el deslizamiento no drenado se agota e i_c llega a 0,5: a partir de ahí gobierna el deslizamiento.

N_γ según el autor (N_q común = e^(π·tan φ)·tan²(45° + φ/2)):
  φ [°]     N_q  EN1997 D   Hansen  Meyerhof   Vesić   máx. dif. a mano
     25   10.66      9.01     6.76      6.77   10.88   0.0e+00
     30   18.40     20.09    15.07     15.67   22.40   2.2e-16
     35   33.30     45.23    33.92     37.15   48.03   2.2e-16
     40   64.20    106.05    79.54     93.69  109.41   3.3e-16
  A 35° el mayor N_γ es el de vesic y el menor el de brinch_hansen (1.42 veces): el término de peso propio depende mucho del autor elegido.
```

</details>

#### Tensões de Boussinesq sob carga pontual, linear, em faixa, circular e retangular face à integração numérica

<details><summary>Saída real de <code>python examples/boussinesq_point_line_strip_circle_rectangle_stress_vs_numerical_integration_and_newmark_values.py</code></summary>

```text
Carga puntual P = 1000 kN: Δσ_z = 3·P·z³/(2·π·R⁵)
  z = 1.0 m, r = 0.0 m:   477.46 kPa (a mano   477.46)
  z = 2.0 m, r = 0.0 m:   119.37 kPa (a mano   119.37)
  z = 2.0 m, r = 1.0 m:    68.33 kPa (a mano    68.33)
  z = 4.0 m, r = 2.0 m:    17.08 kPa (a mano    17.08)

Faja flexible B = 2.0 m, q = 100 kPa, z = 2.0 m (integración de 20000 cargas lineales):
   x [m]  paquete  integral      dif.
     0.0   54.982    54.982  -0.0000 %
     0.5   51.050    51.050  -0.0000 %
     1.0   40.915    40.915  -0.0000 %
     2.0   18.484    18.484  +0.0000 %
     3.0    7.059     7.059  +0.0000 %
  Bajo el eje: 0.550·q (tabla de Das para z/b = 2: 0,550·q)

Círculo flexible R = 1.5 m, q = 100 kPa, bajo el centro (integral de anillos de carga puntual):
  z = 0.5 m:  96.838 kPa (integral  96.838)
  z = 1.5 m:  64.645 kPa (integral  64.645)
  z = 3.0 m:  28.446 kPa (integral  28.446)
  z = 6.0 m:   8.692 kPa (integral   8.692)

Factor de Newmark bajo la esquina, I(m, n) con m = B/z, n = L/z:
     m    n   stress boussinesq  integral
   1.0  1.0   0.1752     0.1752    0.1752
   0.5  2.0   0.1350     0.1350    0.1350
   2.0  3.0   0.2378     0.2378    0.2378
   0.2  0.2   0.0179     0.0179    0.0179
  Tabla de Newmark/Fadum: I(1, 1) = 0,1752.

Zapata 2.0 × 3.0 m con q = 200 kPa: bajo el centro frente a la regla 2:1 (q·B·L/((B+z)(L+z))):
  z [m] Boussinesq     2:1 2:1/Bous.  esquina
    0.5      190.3   137.1      0.72     49.6
    1.0      154.9   100.0      0.65     47.6
    2.0       85.7    60.0      0.70     38.7
    3.0       49.0    40.0      0.82     29.0
    5.0       20.7    21.4      1.04     16.0
  Cerca de la base la regla 2:1 infravalora el incremento bajo el centro; en profundidad converge.
```

</details>

#### Assentamentos elásticos: fatores de influência de Steinbrenner no canto e no centro face à integração numérica

<details><summary>Saída real de <code>python examples/elastic_settlement_steinbrenner_influence_factor_corner_centre_vs_numerical_integration_l_over_b_1_to_10.py</code></summary>

```text
  L/B  esquina  integral   centro 2×integral fórmula anterior
  1.0   0.5611    0.5608   1.1222     1.1216           1.1222
  1.5   0.6788    0.6784   1.3576     1.3567           1.5389
  2.0   0.7659    0.7653   1.5317     1.5306           2.1444
  3.0   0.8915    0.8907   1.7830     1.7814           3.6814
  5.0   1.0523    1.0509   2.1046     2.1018           7.4872
 10.0   1.2721    1.2694   2.5443     2.5388          19.1508
La integral de malla queda entre 0.06 % y 0.22 % por debajo de la fórmula (la singularidad 1/r de la esquina se integra con error de malla); la fórmula anterior solo acertaba en L/B = 1.

Zapata flexible 2.0 × 3.0 m, q = 150 kPa, E = 25 MPa, ν = 0.3:
  a mano: I_s,centro = 1.3576; s = 150·2.0·(1 − 0.3²)/25000·1.3576 = 14.82 mm
  paquete: centro 14.82 mm, esquina 7.41 mm (la esquina es la mitad del centro: 0.500).
Límite: semiespacio homogéneo de espesor infinito; con un estrato rígido a poca profundidad el asiento es menor (factores de Steinbrenner con H/B, no implementados aquí).
```

</details>

#### Deslizamento e derrubamento de sapata superficial: betão in situ face a pré-fabricado e critérios de rotura

<details><summary>Saída real de <code>python examples/sliding_overturning_cast_in_situ_vs_precast_two_thirds_phi_undrained_and_vesic_failure_mode.py</code></summary>

```text
Deslizamiento drenado: N = 1200 kN, H_d = 300 kN, A' = 6.0 m², φ'k = 30.0°
  Enfoque base             γφ   γRh  δ_d [°] H_Rd [kN]   a mano H_d/H_Rd
  DA1-C1  in situ        1.00  1.00    30.00     692.8    692.8    0.433
  DA1-C1  prefabricada   1.00  1.00    20.00     436.8    436.8    0.687
  DA1-C2  in situ        1.25  1.00    24.79     554.3    554.3    0.541
  DA1-C2  prefabricada   1.25  1.00    16.53     356.1    356.1    0.842
  DA2     in situ        1.00  1.10    30.00     629.8    629.8    0.476
  DA2     prefabricada   1.00  1.10    20.00     397.1    397.1    0.756
  Gobierna DA1-C2 con base prefabricada: H_d/H_Rd = 0.842 (cumple).
  Con 2/3 sobre la tangente (antes de la 1.1.0) δ_d habría sido 21.05° en vez de 20.00° (+5.8 % de resistencia).
No drenado DA1-C2: H_Rd = 40/1.4·6.0/1.0 = 171.4 kN, H_d/H_Rd = 1.75 (no cumple)
No drenado DA2: H_Rd = 40/1.0·6.0/1.1 = 218.2 kN, H_d/H_Rd = 1.38 (no cumple)

Vuelco: B = 2.5 m, V = 1200 kN, M_dst = 900 kN·m: e_B = 1.25 − (1500 − 900)/1200 = 0.750 m; M_dst/M_stb = 0.600; tercio central (B/6 = 0.417 m): no, hay despegue

Modo de rotura de Vesić bajo una zapata de 2 × 2 m a 5 m en arena suelta (φ' = 30°, q' = 95 kPa, ν = 0,3):
  E [MPa]  G [kPa] I_r a mano      I_r   I_rc modo               ζ_q
        4     1538       28.0     28.0   69.6 local_shear      0.472
        8     3077       56.1     56.1   69.6 local_shear      0.642
       30    11538      210.4    210.4   69.6 general_shear    1.000
  I_rc(30°) = ½·exp(2,85·cot 30°) = 69.6 (paquete 69.6). Con I_r < I_rc el diseño desde CPT multiplica q_ult por ζ_q. La constante 2,85 y ζ_q sin término de forma B/L son las del módulo; la dependencia de B/L de la formulación de Vesić no se ha contrastado aquí.
```

</details>

### 2. Assentamentos, ensaios in situ (CPT/SPT) e consolidação

#### Consolidação 1D de Terzaghi: série analítica U–T_v face a aproximações e assentamentos OC/NC

<details><summary>Saída real de <code>python examples/terzaghi_consolidation_u_tv_series_vs_approximations_oc_nc_settlement_and_time_to_90_percent.py</code></summary>

```text
   T_v  U serie  √(4T/π)  1−8/π²·e
 0.010   0.1128   0.1128    0.2092
 0.050   0.2523   0.2523    0.2835
 0.100   0.3568   0.3568    0.3667
 0.197   0.5003   0.5008    0.5015
 0.300   0.6132   0.6180    0.6134
 0.500   0.7640   0.7979    0.7640
 0.848   0.9000   1.0391    0.9000
 1.200   0.9580   1.2361    0.9580
Inversa (Casagrande/Taylor): T_v(50 %) = 0.1963, T_v(90 %) = 0.8480 (referencias 0,197 y 0,848)

Arcilla H = 4.0 m (doble drenaje), e0 = 1.1, Cc = 0.35, Cr = 0.05, σ'0 = 60, σ'p = 90, Δσ = 80 kPa
  a mano: 4.0·0.05/2.10·log(90/60) + 4.0·0.35/2.10·log(140/90) = 144.7 mm
  paquete: 144.7 mm
  con Δσ = 20 kPa (sin llegar a σ'p): 11.9 mm
  con Δσ = 200 kPa (muy por encima de σ'p): 323.9 mm
  si fuese normalmente consolidada: 245.3 mm (1.7 veces más)

H_dr = 2.0 m: t50 = T_v50·H_dr²/cv = 0.1963·2.0²/2.0 = 0.393 años (143 días); t90 = 1.696 años (619 días)
  t = 0.00 a: 4 mm  t = 0.25 a: 58 mm  t = 0.50 a: 81 mm  t = 0.75 a: 98 mm  t = 1.00 a: 111 mm  t = 1.25 a: 120 mm  t = 1.50 a: 126 mm  t = 1.75 a: 131 mm  t = 2.00 a: 135 mm

Dos módulos duplicados (NC): analysis.consolidacion_1d S_c = 245.3 mm, t90 = 619 d; consolidacion_1d S_c = 245.3 mm, t90 = 620 d (el segundo usa 365,25 días/año y el primero 365). Asiento NC a mano: 245.3 mm.
```

</details>

#### Registo CPTu estratificado: classificação SBT de Robertson, I_c, φ' e c_u derivados

<details><summary>Saída real de <code>python examples/cpt_log_robertson_ic_soil_behaviour_type_kulhawy_mayne_phi_dr_and_cu_from_qt_stratified_profile.py</code></summary>

```text
CPTu de 75 lecturas cada 0,2 m, nivel freático a 2.0 m

z [m] q_t [MPa]    σv0 σ_v0_eff    Q_t  F_r %   I_c zona SBT          
  1.0     6.300   18.0   18.0  349.0   0.64  1.38 SAND              
  2.6     6.780   47.4   41.5  162.2   0.59  1.60 SAND              
  4.0     0.846   74.0   54.4   14.2   2.33  2.81 SILT_MIX_CLAY     
  6.0     0.910  112.0   72.8   11.0   2.26  2.89 SILT_MIX_CLAY     
  8.0    16.312  150.0   91.1  177.3   0.68  1.61 SAND              
 12.0    17.520  226.0  127.9  135.2   0.64  1.69 SAND              

A mano en z = 4,0 m (arcilla) y z = 12,0 m (arena):
  z = 4.0: σv0 = 18·2 + 19·2 = 74.0 kPa, u = 19.6, σ'v0 = 54.4; q_t = 0.8459 MPa; Q_t = 14.19, F_r = 2.33 %, I_c = 2.809 (paquete 2.809)
    c_u = (845.9 − 74.0)/14 = 55.1 kPa (paquete 55.1)
  z = 12.0: σv0 = 18·2 + 19·10 = 226.0 kPa, u = 98.1, σ'v0 = 127.9; q_t = 17.5196 MPa; Q_t = 135.21, F_r = 0.64 %, I_c = 1.685 (paquete 1.685)
    Q_tn = 154.9: φ' = 17,6 + 11·log Q_tn = 41.7° (paquete 41.7°), D_R = √(Q_tn/305) = 71 % (paquete 71 %)

Estratificación en 5 bandas iguales (`stratify`):
  z_top z_bot q_t medio   I_c zona                 phi_eff [deg] c_u [kPa]  E [MPa]
    0.2   3.2      6.07  1.52 SAND                 40.1         —     30.2
    3.2   6.1      0.87  2.84 SILT_MIX_CLAY           —      55.6      1.6
    6.1   9.1     12.21  1.96 SAND                 40.9         —     60.6
    9.1  12.0     17.10  1.66 SAND                 41.8         —     84.9
   12.0  15.0     18.00  1.71 SAND                 41.6         —     89.3
Límites: bandas de igual espesor (no se detectan contactos), I_c con Q_t (exponente n = 1), E = α·(q_t − σ'_v0) con α fijo (5 en arena, 2 en arcilla; el docstring del módulo cita una α variable con I_c que no se aplica) y N_kt = 14 sin calibrar.
```

</details>

#### Correções de energia e de sobrecarga SPT: N_60, N_1(60), correlações de φ' e c_u

<details><summary>Saída real de <code>python examples/spt_energy_and_overburden_corrections_n60_n1_60_phi_hatanaka_uchida_jra_dr_skempton_cu_stroud.py</code></summary>

```text
z [m] suelo   N σ_v0_eff    N60  N1(60)  φ H-U  φ JRA  φ PHT D_R %    c_u E Schm. E Bowles
  1.5 sand    8    27   9.33   17.96   39.0   31.4   29.9    55      —     7.1     12.2
  3.0 sand   14    50  16.33   23.10   41.5   33.6   31.9    62      —    12.5     15.7
  6.0 sand   22    80  25.67   28.70   44.0   35.7   34.4    69      —    19.7     20.3
  9.0 sand   31   110  36.17   34.48   46.3   37.7   37.2    76      —    27.7     25.6
 12.0 clay   12   140  14.00   11.83      —      —      —     —   63.0     4.5      5.6
 15.0 clay   16   170  18.67   14.32      —      —      —     —   84.0     6.0      7.5

A mano, 6 m: N60 = 22·70/60 = 25.667; C_N = √(100/80) = 1.1180; N1(60) = 28.696
  φ' (H-U) = √(20·28.696) + 20 = 43.96°; D_R = √(28.696/60) = 69.2 %; E = 0,766·25.67 = 19.66 MPa (paquete 19.66)
  Las tres correlaciones de φ' en 6 m van de 34.4° a 44.0°: 9.5° de dispersión entre autores para el mismo golpeo.
Límites: C_N de Liao y Whitman sin corrección por diámetro, varillaje ni tomamuestras; correlaciones empíricas sin calibración local; E de Schmertmann para arena se aplica igual a arena seca y saturada.
```

</details>

#### Dimensionamento de sapata a partir de um perfil CPT: punçoamento de estrato brando e varrimento de dimensões

<details><summary>Saída real de <code>python examples/footing_design_from_cpt_log_layered_bearing_punch_through_settlement_and_minimum_square_footing_search.py</code></summary>

```text
Perfil derivado del CPT (4 bandas):
   0.00– 3.90 m  cohesionless φ' = 42.9°       E =  59.8 MPa
   3.90– 7.60 m  cohesive     c_u = 58.0 kPa   E =   1.7 MPa
   7.60–11.30 m  cohesionless φ' = 42.3°       E =  89.6 MPa
  11.30–15.00 m  cohesionless φ' = 41.6°       E =  89.4 MPa

Zapata cuadrada a D = 1.0 m, N = 1500 kN, DA2, asiento admisible 75 mm
B [m]   q_Ed  q_ult   q_Rd  util.  s_inm  s_cons veredicto 
 1.50  666.7   1000    714   0.93   14.5     0.0 cumple    
 2.00  375.0    853    609   0.62    9.8    43.1 cumple    
 2.50  240.0    764    546   0.44    7.0    65.0 cumple    
 3.00  166.7    706    504   0.33    5.2    74.8 no cumple 
 3.50  122.4    663    474   0.26    4.0    73.2 no cumple 
 4.00   93.8    632    451   0.21    3.2    65.7 cumple    
 4.50   74.1    607    434   0.17    2.6    58.0 cumple    
 5.00   60.0    588    420   0.14    2.1    50.4 cumple    
 5.50   49.6    572    408   0.12    1.7    42.8 cumple    
 6.00   41.7    558    399   0.10    1.3    35.5 cumple    

Con B = 2,5 m gobierna «punching_through_strong_to_weak»: q_ult del estrato de apoyo 5758 kPa, de la arcilla sola 411 kPa y con punzonamiento a través de la arena 764 kPa; q_Rd = 764·1.00/1,4 = 546 kPa.

Bisección del optimizador (9 evaluaciones): B = 1.518 m (asiento 17.9 mm).
Barrido completo: el primer lado que cumple es B = 1.50 m.
  El veredicto NO es monótono con B: fallan [3.0, 3.5] m aunque lados menores cumplen (el asiento de consolidación crece mientras la zona de influencia 2B entra en la arcilla y luego baja con q).
  Aquí la bisección acierta: su primer punto medio (B = 3.75 m) cumplía y desde ahí solo exploró lados menores. Con otros límites de búsqueda podría caer en la zona que falla y converger a otro lado: revisa siempre el barrido.
Límites: la consolidación usa Cc = 0,30, e0 = 0,8, Cr = 0,05 y cv = 2 m²/año FIJOS (el CPT no los da) y el t90 se calcula con el espesor de cada subcapa de 0,5 m; el asiento se corta a 2B; el punzonamiento entre estratos es una heurística con K_s = tan φ, no el ábaco de Meyerhof-Hanna; el optimizador no comprueba el canto.
```

</details>

### 3. Fundação superficial: pressões, flexão, punçoamento e sismo

#### Pressões de contacto sob sapata rígida: núcleo central, descolamento uniaxial e solução exata sem tração

<details><summary>Saída real de <code>python examples/base_pressure_rigid_footing_core_uniaxial_lift_off_biaxial_outside_core_vs_no_tension_solution.py</code></summary>

```text
Zapata 3.0 × 2.0 m, N = 1200 kN (sin peso propio), q_media = 200.0 kPa; núcleo L/6 = 0.500 m, B/6 = 0.333 m

Caso                            e_x    e_y régimen              q_max    q_min  A_act q_max a mano
centrada                      0.000  0.000 centred              200.0    200.0   6.00        200.0
M_y = 300 (en el núcleo)      0.250  0.000 centred              300.0    100.0   6.00        300.0
M_y = 900 (despegue en X)     0.750  0.000 outside_core         533.3      0.0   4.50        533.3
M_x = 500 (despegue en Y)     0.000  0.417 outside_core         457.1      0.0   5.25        457.1
M_x = 300, M_y = 700          0.583  0.250 outside_core         583.3   -183.3   6.00            —
M_y = 2000 (vuelco)           1.667  0.000 overturned               ∞      0.0   0.00            ∞

Biaxial fuera del núcleo (6·e_x/L + 6·e_y/B = 1.92 > 1):
  Navier del paquete: q_max = 583.3 kPa y q_min = -183.3 kPa (tracción imposible en el contacto).
  Solución sin tracciones (malla 200 × 200, residuo 1.9e-16): q_max = 632.3 kPa sobre 4.90 m² comprimidos.
  Navier da una q_max un 8 % menor que la real: queda del lado inseguro, y su q_min negativa no tiene sentido físico. En este régimen hay que redimensionar o comprobar con el área eficaz de EN 1997-1, no con la presión de Navier.
```

</details>

#### Flexão em ambas as direções segundo a EN 1992-1-1: seleção de varões comerciais e comprimento de amarração

<details><summary>Saída real de <code>python examples/footing_flexure_both_ways_ec2_eccentric_pressure_bar_selection_and_anchorage_length_hand_check.py</code></summary>

```text
Zapata 3.0 × 2.5 × 0.6 m, N = 1800 kN, M_y = 270 kN·m -> e_x = 0.150 m (L/6 = 0.50)
A mano (X): q_max = 240.0·(1 + 6·0.150/3.0) = 312.0 kPa; v = 1.360 m; M = 312.0·2.5·1.360²/2 = 721.3 kN·m
  d = 542 mm, K = 0.0327, z = 514.9 mm, A_s = 3222 mm², A_s,min = 2041 mm²

dir.    M_Ed  A_s,req  A_s,min barras           A_s,disp   l_bd l_disp estado        
X      721.3     3222     2041 17 Ø16 @ 150         3418    539   1250 OK            
Y      576.6     2654     2377 14 Ø16 @ 220         2815    539   1000 OK            
Diferencia con la mano en X: M +0.00e+00, A_s +0.00e+00

Anclaje Ø16 en buena adherencia, σ_sd = f_yd: f_bd = 2,25·0,7·2.896/1,5 = 3.041 MPa; l_b,rqd = (16/4)·434.8/3.041 = 572 mm (paquete 572)
  con σ_sd = f_yd·A_s,req/A_s,disp: l_bd = 539 mm frente a 1250 mm disponibles -> basta la longitud recta
Límites: q_max en las dos direcciones (en Y sobra armadura con excentricidad solo en X); sin comprobación de cortante en la sección a d de la cara; la separación máxima min(2,5h, 250 mm) es el criterio del módulo.
```

</details>

#### Punçoamento segundo a ACI 318-19: pilares interiores, de bordo e de canto com momento desequilibrado γ_v e J_c

<details><summary>Saída real de <code>python examples/punching_aci318_19_interior_edge_corner_unbalanced_moment_gamma_v_jc_and_size_effect_hand_check.py</code></summary>

```text
Pilar interior 500 × 500 mm, d = 300 mm, V_u = 900 kN, M_u = 100 kN·m, f'c = 30 MPa
A mano: b0 = 3200 mm, A_c = 960000 mm², γ_v = 0.400, J_c = 1.0600e+11 mm⁴
  v = 0.9375 + 0.1509 = 1.0884 MPa; λ_s = 0.9535; v_c = 1.7234 MPa; φ·v_c = 1.2925 MPa -> 0.842
Paquete: v_ug,max = 1.0884 MPa, φ·v_c = 1.2925 MPa, DCR = 0.842 (cumple)

posición   b0 [mm]   γ_vx  v_dir  v_mom   φv_c    DCR
interior      3200  0.400  0.938  0.151  1.293  0.842
edge          2100  0.425  1.429  0.218  1.293  1.274
corner        1300  0.400  2.308  1.047  1.293  2.595
Con las mismas cargas la peor posición es «corner»: el perímetro se reduce a 3 o 2 lados.

Barrido del momento (pilar interior):
  M_u =     0 kN·m: v_max = 0.938 MPa, DCR = 0.725
  M_u =   100 kN·m: v_max = 1.088 MPa, DCR = 0.842
  M_u =   200 kN·m: v_max = 1.239 MPa, DCR = 0.959
  M_u =   300 kN·m: v_max = 1.390 MPa, DCR = 1.076
  M_u =   400 kN·m: v_max = 1.541 MPa, DCR = 1.192
  M_u =   500 kN·m: v_max = 1.692 MPa, DCR = 1.309
  Primer momento del barrido que agota: 300 kN·m.
Límites: el perímetro de borde y esquina se toma con el borde libre normal a X; sin armadura de punzonamiento; el momento sobre Y se suma con el mismo criterio (v_max en la esquina más cargada).
```

</details>

#### Punçoamento na base de pilar segundo a EN 1992-1-1: varrimento de perímetros de controlo dentro de 2d em sapatas compactas

<details><summary>Saída real de <code>python examples/punching_ec2_column_base_control_perimeters_within_2d_scan_vs_basic_perimeter_and_compact_footing.py</code></summary>

```text
k = 1.6325; v_Rd,c = max(0,12·k·(100ρ·fck)^(1/3), v_min) = 454.6 kPa

Zapata 3.0 × 3.0 m, N = 800 kN, pilar interior (β = 1.15):
    a/d  a [m]  u [m] F_red [kN] v_Ed [kPa] v_Rd·2d/a v_Ed/v_Rd
   0.25  0.125  2.385      763.6      736.3    3637.0     0.202
   0.50  0.250  3.171      732.8      531.5    1818.5     0.292
   0.75  0.375  3.956      693.2      403.0    1212.3     0.332
   1.00  0.500  4.742      644.9      312.8     909.3     0.344
   1.25  0.625  5.527      587.8      244.6     727.4     0.336
   1.50  0.750  6.312      522.0      190.2     606.2     0.314
   2.00  1.000  7.883      364.3      106.3     454.6     0.234
  Paquete: gobierna a = 0.513 m (a/d = 1.03), u = 4.822 m, v_Ed = 305.0 kPa, v_Rd(a) = 886.5 kPa -> 0.344 (PASS)
  Comprobación a mano en ese a: 0.3440. Solo a 2d (antes): 0.234; el perímetro crítico da un 47 % más de utilización.

Otros casos:
  3 × 3 m, N = 2500 kN, interior         β = 1.15, compacta no, a = 0.513 m, v_Ed/v_Rd = 1.075 -> FAIL
  compacta 1,4 × 1,4 m, N = 600 kN       β = 1.15, compacta sí, a = 0.223 m, v_Ed/v_Rd = 0.148 -> PASS
  3 × 3 m, N = 800 kN, pilar en borde    β = 1.40, compacta no, a = 0.513 m, v_Ed/v_Rd = 0.419 -> PASS
  3 × 3 m, N = 800 kN, pilar en esquina  β = 1.50, compacta no, a = 0.513 m, v_Ed/v_Rd = 0.449 -> PASS
Límites: presión del terreno uniforme N/A (sin momento) y perímetro de pilar interior aunque el pilar esté en borde o esquina: β (1,4/1,5) es la única corrección; sin armadura de punzonamiento.
```

</details>

#### Sapata combinada retangular e trapezoidal: centroide coincidente com a resultante e momento negativo

<details><summary>Saída real de <code>python examples/combined_footing_rectangular_and_trapezoidal_resultant_on_centroid_hogging_moment_and_memo.py</code></summary>

```text
Caso A: P1 = 900, P2 = 1300 kN, s = 5.0 m, d = 0.5 m, c = 0.45 m, q_adm = 200 kPa
  a mano: x_R = 1300·5.0/2200 = 2.9545 m desde el pilar 1; L = 2·(0.725 + 2.9545) = 7.3591 m; B = 2200/200/7.3591 = 1.4947 m
  paquete: forma rectangular, L = 7.3591 m, B = 1.4947 m, A = 11.000 m² (requerida 11.000)
  Viga invertida: w = 2200/7.3591 = 298.95 kN/m hacia arriba, pilares hacia abajo.
  Entre pilares el cortante se anula en x = P1/w = 3.0105 m: M = w·x²/2 − P1·(x − 0.725) = -702.2 kN·m (tracción arriba); paquete M_neg = -702.2 kN·m
  Bajo el pilar 2: M = w·5.725²/2 − P1·5.0 = 399.1 kN·m (tracción abajo); paquete M_pos = 399.1 kN·m
  Armadura total en el ancho B = 1.495 m (d = 520 mm): superior 3283 mm² para 702 kN·m, inferior 1858 mm² para 399 kN·m. Antes de la 1.1.0 el momento entre pilares no se recogía y la armadura superior salía de los 399 kN·m de bajo el pilar. q_avg = 200.0 kPa,  q_allow = 200.0 kPa

Caso B: pilar 1 en el lindero, P1 = 600, P2 = 1200 kN, s = 4 m, c = 0.4 m
  paquete: forma trapezoidal, L = 4.80 m, B1 = 0.781 m (lindero), B2 = 2.969 m, A = 9.000 m²
  centroide del trapecio = 2.8667 m; resultante desde el lindero = c/2 + x_R = 2.8667 m -> coinciden: presión uniforme
  con la fórmula anterior (sin c/2) el centroide habría ido a 2.6667 m, 20 cm corto.

Memoria (memos.combined_footing) con la planta del caso A redondeada y pilares centrados en la planta:
  σ_max = 275.0 kPa, σ_min = 126.3 kPa (e = -0.455 m); R_d = 7032 kN frente a 2200 kN -> cumple
  punzonamiento simplificado: v_Ed = 369 kPa frente a 0,33·√f'c = 1650 kPa
Límites: el diagrama de flectores usa la presión media aunque la planta sea trapezoidal; la memoria supone voladizos iguales (no el lindero) y su punzonamiento no descuenta la reacción del terreno ni lleva φ.
```

</details>

#### Sapata para grua-torre em serviço e em tempestade: quatro abordagens de cálculo e varrimento da dimensão mínima

<details><summary>Saída real de <code>python examples/tower_crane_pad_in_service_and_storm_cases_four_design_approaches_minimum_side_sweep.py</code></summary>

```text
Zapata 6.5 × 6.5 × 1.6 m con 1.5 m de relleno; mástil 2 × 2 m

caso      enfoque  e [m] régimen          q_max portante  desliz.  vuelco
servicio  DA1-C1   0.761 centred          195.5    0.044    0.031   0.316
servicio  DA1-C2   0.761 centred          144.8    0.077    0.029   0.234
servicio  DA2      0.761 centred          195.5    0.062    0.034   0.316
tormenta  DA1-C1   1.116 outside_core     220.2    0.056    0.079   0.463
tormenta  DA1-C2   1.305 outside_core     179.0    0.113    0.086   0.402
tormenta  DA2      1.116 outside_core     220.2    0.079    0.087   0.463

A mano, tormenta DA2: W = 42.25·(1.6·25 + 1.5·19) = 2894.1 kN; N_d = 1,35·(500 + 2894.1) = 4582.1 kN;
  M_d = 1,50·(3200 + 130·1.6) = 5112.0 kN·m; e = 1.1157 m (fuera del núcleo L/6 = 1.083 m); q_max = 220.2 kPa (paquete e = 1.1157 m, q_max = 220.2 kPa)

Barrido del lado (todos los enfoques y los dos casos):
  lado 4.50 m: peor relación ∞ (área eficaz nula: resultante en el borde) (tormenta, DA1-C2) -> no cumple
  lado 4.75 m: peor relación 1.925 (tormenta, DA1-C2) -> no cumple
  lado 5.00 m: peor relación 0.924 (tormenta, DA2) -> cumple
  lado 5.25 m: peor relación 0.815 (tormenta, DA2) -> cumple
  lado 5.50 m: peor relación 0.723 (tormenta, DA2) -> cumple
  lado 5.75 m: peor relación 0.643 (tormenta, DA2) -> cumple
  lado 6.00 m: peor relación 0.575 (tormenta, DA2) -> cumple
  lado 6.25 m: peor relación 0.515 (tormenta, DA2) -> cumple
  lado 6.50 m: peor relación 0.463 (tormenta, DA2) -> cumple
Lado mínimo que cumple todo: 5.00 m.
Límites: en servicio el momento del gancho se mayora con γ_G (criterio del módulo, no EN 1991-3); el vuelco se toma con el momento resultante sobre el lado menor y el canto no se comprueba estructuralmente.
```

</details>

#### Sapata superficial sob sismo segundo a EN 1998-5: inércia do bloco de betão e varrimento do fator de redução

<details><summary>Saída real de <code>python examples/seismic_spread_footing_en1998_5_pseudostatic_block_inertia_hand_check_and_r_factor_sweep.py</code></summary>

```text
Zapata 3.0 × 3.0 × 0.7 m a 1.2 m; N = 990 kN, H = 180 kN, M = 420 kN·m; a_g = 0,20 g, S = 1,15, r = 1
A mano: W = 157.5 kN; k_h = 0.230; H_in = 36.225 kN; N_tot = 990 + 157.5 − 0,5·0.230·157.5 = 1129.388 kN
        M_tot = 420 + 180·0.7 + 36.225·0.7/2 = 558.679 kN·m; e = 0.4947 m
Paquete: N_d = 1129.388 kN, M_d = 558.679 kN·m, e_y = 0.4947 m, régimen centred, q_max = 249.6 kPa

comprobación       E_d       R_d  E_d/R_d
portante         187.2      87.5    2.141   (kPa, área eficaz)
deslizam.        216.2     609.4    0.355   (kN)
vuelco           558.7    1694.1    0.330   (kN·m)
Veredicto: no cumple; resultante en el tercio central: sí.
Gobierna portante. Con DA3 φ_d = 28.35° y el factor sísmico del módulo (1 − k_h/tan φ_d)³ = 0.189 multiplica toda la q_ult: es lo que más pesa en la portante.

Barrido del factor r de EN 1998-5 (k_h = a_g·S/r):
     r    k_h  portante  desliz.  vuelco
   1.0  0.230     2.141    0.355   0.330
   1.5  0.153     1.069    0.333   0.326
   2.0  0.115     0.793    0.322   0.323
Límites: la reducción sísmica de la portante es el factor (1 − k_h/tan φ_d)³ del módulo, no la superficie de rotura del Anexo F de EN 1998-5; el vuelco se toma sobre el lado menor con el momento total.
```

</details>

#### Vigas de travamento e de equilíbrio segundo o EC8 e a NSR-10, e maciços de encabeçamento por escoras e tirantes (2 a 4 estacas)

<details><summary>Saída real de <code>python examples/strap_and_tie_beams_ec8_nsr10_tie_forces_and_pile_cap_strut_and_tie_two_three_four_piles.py</code></summary>

```text
Viga centradora: N1 = 1200, N2 = 1800 kN, L = 6 m, e = 0.4 m
  a mano: T = 0,03·3000 = 90 kN; M = 1800·0.4 + 10.0·6²/12 = 750 kN·m; V = M/L = 125 kN; canto = max(L/12, 350) = 500 mm
  paquete: T = 90 kN, M = 750 kN·m, V = 125 kN, 300 × 500 mm
  Nota: M toma la mayor de las dos cargas por la excentricidad; con la medianera en el pilar 1 la excentricidad la produce N1 (480 kN·m): el módulo queda del lado conservador.

Viga de atado, N_Ed = 1800 kN, α·S = 0.3:
  terreno A: ±0 kN
  terreno B: ±162 kN
  terreno C: ±216 kN
  terreno D: ±324 kN
  3 plantas sobre el sótano: sección mínima 250 × 400 mm
  5 plantas sobre el sótano: sección mínima 250 × 500 mm
  NSR-10 A.3.6.4.2: T = 0,25·0.25·1800 = 112.5 kN; 250 × 400 mm, A_s = max(298, 516) -> 6 barras de Ø12.7 (760 mm²)

Encepados (f_yd limitado a 400 MPa, a = 500 mm, d = 900 mm):
  2 pilotes, N_d = 1500 kN, v = 750 mm: T = 1500·(750 + 0,25·500)/(0,85·900) = 1715.7 kN (paquete 1715.7); A_s = 4289 mm²
  3 pilotes, N_d = 3000 kN, l = 1800 mm: T = 0,68·3000/900·(0,58·1800 − 0,25·500) = 2083.1 kN (paquete 2083.1); A_s = 5208 mm²
  4 pilotes, N_d = 3000 kN, l = 1800 mm: T = 3000/(0,85·900)·(0,5·1800 − 0,25·500) = 3039.2 kN por dirección (paquete 3039.2, 3039.2)
  Reparto rígido de V = 3000 kN, M_x = 400, M_y = 250 kN·m en 4 pilotes a ±0,9 m: 569.4, 708.3, 791.7, 930.6 kN (a mano 750 ± 400·0,9/3,24 ± 250·0,9/3,24 = 750 ± 111.1 ± 69.4)
Límites: las fórmulas de encepado y la de zapata rígida (`strut_and_tie_rigid_footing`) se toman tal como las trae el módulo, con la definición de N_d y v de cada una, y no se han contrastado aquí con la EHE-08; los coeficientes 0,3/0,4/0,6 y las secciones mínimas de EC8 tampoco.
```

</details>

### 4. Muros de suporte e impulsos

#### Coeficientes de impulso de terras de Rankine e Coulomb com aterro inclinado, repouso e fenda de tração

<details><summary>Saída real de <code>python examples/earth_pressure_coefficients_rankine_coulomb_inclined_backfill_at_rest_ocr_and_tension_crack.py</code></summary>

```text
φ [°] Ka Rankine Ka Coulomb δ=0  Ka Coulomb δ=⅔φ Kp Rankine   Kp Coulomb δ=⅓φ tan²(45−φ/2)
   25     0.4059         0.4059           0.3608      2.464             3.124       0.4059
   30     0.3333         0.3333           0.2973      3.000             4.143       0.3333
   35     0.2710         0.2710           0.2444      3.690             5.680       0.2710
   40     0.2174         0.2174           0.1998      4.599             8.147       0.2174

Rankine con relleno inclinado (φ = 30°): K_a y componente horizontal K_a·cos α
  α [°]     K_a  a mano K_a·cos α  vs α = 0
      0  0.3333  0.3333    0.3333     +0.0 %
     10  0.3495  0.3495    0.3442     +3.3 %
     20  0.4142  0.4142    0.3892    +16.8 %
     25  0.4936  0.4936    0.4473    +34.2 %
     30  0.8660  0.8660    0.7500   +125.0 %
  Antes de la 1.1.0 el muro en ménsula (trasdós virtual) usaba el K_a de α = 0 con cualquier talud.

Reposo K_0 = (1 − sen φ)·OCR^(sen φ), φ = 30°:
  OCR = 1.0: 0.5000 (a mano 0.5000)
  OCR = 2.0: 0.7071 (a mano 0.7071)
  OCR = 4.0: 1.0000 (a mano 1.0000)

Muro de 6.0 m, γ = 19.0, φ = 30.0°, q = 15.0 kPa:
  activo: P = ½·0.3333·19.0·6.0² + 0.3333·15.0·6.0 = 144.0 kN/m (paquete 144.0) a 2.208 m de la base
  reposo: P = 216.0 kN/m (1.50 veces el activo)
  con c' = 10.0 kPa: z_c = 2·10.0/(19.0·√0.3333) = 1.823 m; el módulo da P = ½K_aγH² − 2c√K_a·H = 44.7 kN/m; descontando la grieta (½·K_a·γ·(H − z_c)²) serían 55.2 kN/m.
Límites: con cohesión el módulo resta 2c√K_a·H sin la grieta (menor que el empuje con grieta) y no mueve el punto de aplicación; Coulomb pasivo con δ grande sobrestima K_p (conviene δ ≤ φ/3).
```

</details>

#### Muro em consola segundo a EN 1997-1 (DA1, DA2 e DA3): tardoz virtual, calcanhar e biqueira verificados à mão

<details><summary>Saída real de <code>python examples/cantilever_retaining_wall_en1997_da1_da2_da3_virtual_back_sloping_backfill_heel_toe_moments_hand_check.py</code></summary>

```text
talud enfoque  K_a,d    H_d    V_d      e portante desliz.  vuelco M_alzado M_talón M_punt.
    0 DA1-C1  0.2948  141.0  391.4  0.362    0.280   0.577   0.416    190.9   294.5    52.7
    0 DA1-C2  0.3689  134.6  386.4  0.350    0.558   0.697   0.416    183.2   168.8    56.1
    0 DA2     0.2948  141.0  391.4  0.362    0.391   0.634   0.416    190.9   294.5    52.7
    0 DA3     0.3689  176.4  391.4  0.544    1.008   0.902   0.416    236.9   344.0    64.0
   15 DA1-C1  0.3253  150.3  431.7  0.187    0.249   0.557   0.396    190.9   220.4    48.0
   15 DA1-C2  0.4189  147.6  425.9  0.197    0.529   0.693   0.396    183.2   101.7    52.8
   15 DA2     0.3253  150.3  431.7  0.187    0.349   0.613   0.396    190.9   220.4    48.0
   15 DA3     0.4189  193.5  443.2  0.327    0.865   0.873   0.396    236.9   255.7    59.7
Peor relación: 1.008 (talud 0°, DA3) -> el muro no cumple en algún caso.
Gobierna DA3 porque el módulo combina A1 (γ_G = 1,35) con el φ de cálculo M2 sobre el empuje; EN 1997-1 aplica A2 a las acciones geotécnicas en DA3, así que este resultado queda del lado conservador.

DA2 a mano: H_v = 5.55 m, K_a = 0.2948; H_d = 1,35·½·K_a·19·5.55² + 1,5·K_a·10·5.55 = 141.0 kN/m (paquete 141.0)
  presiones: q(puntera) = 153.6, q(cara puntera) = 126.0, q(cara talón) = 113.6, q(final talón) = 44.6 kPa (e = 0.362 m hacia la puntera)
  talón: M = 161.8·2,5²/2 − 2,5²·(q_a + 2q_b)/6 = 294.5 kN·m/m (paquete 294.5); puntera: M = (2q_0 + q_t)/6 − 39.1/2 = 52.7 kN·m/m (paquete 52.7)
  deslizamiento: H_Rd = V_d·tan 32°/γ_φ/γ_R;h = 391.4·0.6249/1.1 = 222.3 kN/m (paquete 222.3)
Límites: peso del relleno sobre el talón con superficie horizontal aunque haya talud; alzado con Coulomb sin componente cos δ; la portante sustituye el muro por una faja de 10 m; sin agua salvo `water_height`.
```

</details>

#### Muro de cave escorado: impulso em repouso, momentos em vão e apoio e verificação de subpressão UPL

<details><summary>Saída real de <code>python examples/basement_wall_at_rest_pressure_propped_cantilever_closed_form_moments_axial_envelope_and_uplift_of_basement_box.py</code></summary>

```text
K_0 = 1 − sen 30° = 0.500 (paquete 0.500); q(0) = 5.00 kPa, q(H) = 38.25 kPa

apoyos                R_cab a mano R_base a mano  M_base  a mano M_vano(21 p) M_vano exacto z [m]
cantilever             0.00   0.00  75.69  75.69  -98.51  -98.51            —             —     —
propped_cantilever    18.20  18.20  57.49  57.49  -34.81  -34.81        16.28         16.33  1.50
pinned_pinned         28.15  28.15  47.54  47.54   -0.00    0.00        33.62         33.64  1.96
  (M > 0 tracciona la cara interior, M < 0 la cara del terreno; momentos en kN·m/m)

Envolvente empotrado-apoyado con axil (e_1 = 5 cm en cabeza):
  triangular : q =  5.00…38.25 kPa, cara terreno M = -34.81 a z = 3.500 m, cara interior M =  20.74 a z = 1.400 m, V_max = 57.49 kN/m
  rectangular: q = 25.63…25.63 kPa, cara terreno M = -39.24 a z = 3.500 m, cara interior M =  26.85 a z = 1.225 m, V_max = 56.06 kN/m
  En cabeza N_max·e_1 = 150·0,05 = 7.50 kN·m/m tracciona la cara interior (envolvente en z = 0: 7.50).
  El diagrama rectangular (0,67·K_0·(γH + q)) es una regla de apuntes del módulo: con él la resultante es 1.19 veces la trapecial.

Comprobación global como muro libre (factores de seguridad, FS ≥ 1,5 del módulo):
  rankine : K_a = 0.3333, P =   50.5 kN/m, FS desliz. = 1.75 (≥ 1,5), FS vuelco = 2.15 (≥ 1,5)
  coulomb : K_a = 0.2973, P =   45.0 kN/m, FS desliz. = 2.27 (≥ 1,5), FS vuelco = 3.01 (≥ 1,5)
  A mano (Rankine): P = ½·0.3333·19·3,5² + 0.3333·10·3,5 = 50.5; FS desliz. = (W + N)·0,5/P = (26.25 + 150)·0,5/50.5 = 1.75

Flotación del vaso de sótano 20 × 15 m con el freático a 3,0 m sobre la cara inferior de la losa:
  W =   9000 kN, U = 9,81·3·300 = 8829 kN, W/U = 1.019 -> EU (≥ 1.111): falta lastre 810 kN; USA (≥ 1.500): falta lastre 4244 kN
  W =   9600 kN, U = 9,81·3·300 = 8829 kN, W/U = 1.087 -> EU (≥ 1.111): falta lastre 210 kN; USA (≥ 1.500): falta lastre 3644 kN
  W =  10500 kN, U = 9,81·3·300 = 8829 kN, W/U = 1.189 -> EU (≥ 1.111): cumple; USA (≥ 1.500): falta lastre 2744 kN
  W =  13500 kN, U = 9,81·3·300 = 8829 kN, W/U = 1.529 -> EU (≥ 1.111): cumple; USA (≥ 1.500): cumple
  Antes de la 1.1.0 el criterio europeo era W/U ≥ 1,10, por debajo de 1/0,9 = 1,111 (γ_G;stb = 0,9).
Límites: con agua el módulo suma γ_w·H_w a la ordenada de la base y la reparte linealmente en toda la altura además de usar γ total (del lado seguro); el diagrama sin axil sale con 21 puntos y el máximo de vano se queda corto; la comprobación global es de factores de seguridad, no EN 1997-1.
```

</details>

#### Muros de gravidade de betão simples e muros de contrafortes: impulso de cálculo e armadura do fuste

<details><summary>Saída real de <code>python examples/gravity_wall_mass_concrete_vs_gabion_coulomb_design_phi_and_counterfort_stem_slab_moments_hand_check.py</code></summary>

```text
Muro de gravedad H = 4,0 m, coronación 0.6 m, base 2.6 m (B/H = 0.65), q = 10 kPa
material       enfoque W [kN/m]  K_a,d    H_d    V_d  e [m] núcleo portante desliz. vuelco
mass_concrete  DA1-C1     153.6 0.2750   67.9  172.8  0.087     sí    0.257   0.883  0.325
mass_concrete  DA1-C2     153.6 0.3397   66.0  173.4  0.073     sí    0.611   1.039  0.318
mass_concrete  DA2        153.6 0.2750   67.9  172.8  0.087     sí    0.360   0.971  0.325
mass_concrete  DA3        153.6 0.3397   85.8  173.4  0.235     sí    1.487   1.351  0.408
gabion         DA1-C1     115.2 0.2771   62.3  143.4  0.071     sí    0.256   0.598  0.344
gabion         DA1-C2     115.2 0.3357   61.3  144.0  0.063     sí    0.622   0.732  0.341
gabion         DA2        115.2 0.2771   62.3  143.4  0.071     sí    0.358   0.658  0.344
gabion         DA3        115.2 0.3357   79.6  144.0  0.244     sí    1.805   0.951  0.437
  mass_concrete: peor relación 1.487 en DA3 -> NO cumple en algún enfoque
  gabion: peor relación 1.805 en DA3 -> NO cumple en algún enfoque

Ancho de base mínimo (pasos de 5 cm) para que portante, deslizamiento y vuelco cumplan:
  mass_concrete  DA1-C1 2.20 m (B/H 0.55); DA1-C2 2.75 m (B/H 0.69); DA2 2.50 m (B/H 0.62); DA3 3.90 m (B/H 0.98)
  gabion         DA1-C1 2.00 m (B/H 0.50); DA1-C2 2.40 m (B/H 0.60); DA2 2.15 m (B/H 0.54); DA3 2.90 m (B/H 0.72)
  En DA3 el módulo aplica A1 (γ_G = 1,35) al empuje junto con M2; EN 1997-1 usa A2 para las acciones geotécnicas en DA3, así que esa columna queda del lado conservador.

A mano: W = ½·(0.6 + 2.6)·4·24 = 153.6 kN/m (paquete 153.6); x_W = [s² − (s − a)²/3]/(a + s) = 1.6958 m desde la puntera (paquete 1.6958)
  DA2: φ_d = 32.00°, K_a(Coulomb, δ = ⅔φ_d) = 0.2750; H_d = 1.35·½·K·19·4²·cos δ + 1.5·K·10·4·cos δ = 67.9 kN/m (paquete 67.9)
  DA1-C2: φ_d = 26.56°, K_a(Coulomb, δ = ⅔φ_d) = 0.3397; H_d = 1.0·½·K·19·4²·cos δ + 1.3·K·10·4·cos δ = 66.0 kN/m (paquete 66.0)
  Con φ_k (antes de la 1.1.0) DA1-C2 tomaba K_a = 0.2750: 19 % menos empuje que con φ_d.

Muro de contrafuertes H = 8 m, alzado 0,35 m, contrafuertes de 0,40 m cada 3,0 m, puntera 1,5 m, talón 4,5 m:
  enfoque portante desliz. vuelco  p_base  M_apoyo  M_vano M_contraf.
  DA1-C1     0.268   0.572  0.402    65.5     49.1    24.6       2368
  DA1-C2     0.531   0.670  0.402    60.0     45.0    22.5       2192
  DA2        0.376   0.630  0.402    65.5     49.1    24.6       2368
  DA3        1.039   0.878  0.402    80.1     60.1    30.0       2897
  A mano (DA2): K_a(Coulomb, δ = 20°) = 0.2973; p = 1,35·K·19·8 + 1,5·K·10 = 65.5 kPa; M_apoyo = p·3²/12 = 49.1 (paquete 49.1), M_vano = p·3²/24 = 24.6 kN·m/m (paquete 24.6)
  El tirante del contrafuerte (T = P_h·tan δ = 305 kN) es una regla del módulo, no un modelo de bielas: dimensiona el tirante talón-alzado con un modelo propio.
Límites: vuelco con coeficientes GEO (no el juego EQU); en el muro de gravedad, agua con la presión hidrostática completa además del empuje con γ total, sin término de sobrecarga en la portante; el alzado toma la presión de la base como uniforme en toda la losa (del lado seguro).
```

</details>

#### Cortinas e estacas-pranchas: apoio livre, impulso aparente em escavações escoradas e ancoragens ao terreno

<details><summary>Saída real de <code>python examples/embedded_walls_diaphragm_free_earth_support_prop_force_moment_strut_loads_apparent_pressure_basal_heave_and_anchors.py</code></summary>

```text
Pantalla H = 10.0 m, φ' = 32.0°, γ = 20.0 kN/m³, puntal en cabeza, DA2 (γ_G = 1,35, γ_R;e = 1,4)
  ficha D   P_a,d   P_p,d F = M_p/M_a P_p,mob T puntal   M_max z(M_max)
      5.0   933.3   581.2       0.830   700.0    233.3    1167     7.50  <- ficha insuficiente (F < 1)
      6.0  1061.9   836.9       1.034   809.1    252.8    1316     7.81
      7.0  1198.8  1139.1       1.230   926.3    272.4    1472     8.10
      8.0  1343.9  1487.8       1.415  1051.8    292.2    1635     8.39
      9.0  1497.4  1883.0       1.588  1185.5    312.0    1804     8.67
  Ficha para F = 1,5 sobre valores de cálculo: D = 8.48 m (el 1,5 se suma a los coeficientes parciales: doble seguridad heredada del módulo)
  A mano (D = 7 m): K_a = 0.3073, K_p = 3.255, k = 1,35·K_a·γ = 8.296 kN/m³; P_a = 1198.8, M_a = 13586, P_p = 1139.1, F = 1.230; T = 1198.8 − 13586/14.667 = 272.4 kN/m; z0 = 8.10 m, M_max = ⅔·T·z0 = 1472 kN·m/m
  Fórmulas anteriores a la 1.1.0: T = P_a − P_p = 59.7 kN/m y M = T²/(2·k·(H + D)) = 12.6 kN·m/m
  DA1-C1: γ_φ = 1.0, γ_R;e = 1.0: F = 1.722, T = 272.4 kN/m, M_max = 1472 kN·m/m
  DA1-C2: γ_φ = 1.25, γ_R;e = 1.0: F = 1.503, T = 250.9 kN/m, M_max = 1356 kN·m/m
  DA3   : γ_φ = 1.25, γ_R;e = 1.0: F = 1.114, T = 338.8 kN/m, M_max = 1830 kN·m/m

Excavación apuntalada de 9 m, puntales a 1,5 / 4,5 / 7,5 m, separación horizontal 4 m:
  arena φ' = 34°: p = 0,65·K_a·γ·H = 0,65·0.2827·19·9 = 31.42 kPa; z = 1.5 m (0.0–3.0): 377 kN, z = 4.5 m (3.0–6.0): 377 kN, z = 7.5 m (6.0–9.0): 377 kN
  suma de puntales 1131 kN = p·H·s = 1131 kN (sin base: el último puntal recoge hasta el fondo)
  arcilla blanda c_u = 25 kPa: N_s = γH/c_u = 6.48, K = 1 − 0,4·4·c_u/(γH) = 0.753, p = 122.0 kPa; puntales 1464, 1464, 1464 kN
    levantamiento de fondo: zanja 12 × 60 m N_c = 5.14, FS = 0.75; recinto 12 × 12 m N_c = 6.84, FS = 0.99 -> insuficiente frente al FS = 1,5 habitual
  arcilla blanda c_u = 40 kPa: N_s = γH/c_u = 4.05, K = 1 − 0,4·4·c_u/(γH) = 0.605, p = 98.0 kPa; puntales 1176, 1176, 1176 kN
    levantamiento de fondo: zanja 12 × 60 m N_c = 5.14, FS = 1.20; recinto 12 × 12 m N_c = 6.84, FS = 1.59 -> insuficiente frente al FS = 1,5 habitual
  Ojo: N_c salta de 5.93 (L = 59,9 m) a 5.14 (L = 60 m = 5B) porque el módulo mezcla 5,7·(1 + 0,2B/L) con 5,14 de faja (sin contrastar).
  basal_heave_clay con N_c = 5,14: FS = 5,14·25/(18·9) = 0.793

Muro anclado de 8 m en arena (φ' = 32°, γ = 19, q = 10 kPa), dos niveles de anclajes activos a 2 y 5 m cada 2,5 m:
  P_total = 1,35·0,65·K_a·γ·H·H + 1,35·0,5·q·H = 381.9 kN/m (paquete 381.9)
  z = 2.0 m: T_d = 494 kN/anclaje (P/2·2,5/cos 15°), libre 4.50 m, bulbo 5.24 m, utilización 1.000, bloqueo 371 kN
  z = 5.0 m: T_d = 494 kN/anclaje (P/2·2,5/cos 15°), libre 4.50 m, bulbo 5.24 m, utilización 1.000, bloqueo 371 kN
  Los dos niveles reciben lo mismo aunque estén a 2 y 5 m, y la utilización del bulbo vale 1 por construcción: el módulo dimensiona, no verifica. Para reparto por áreas tributarias usa `strut_force`.
Límites: soporte libre con un puntal (con varios, reparto a partes iguales sin equilibrio de momentos); sin cohesión ni agua en la pantalla (el módulo ahora lo rechaza); envolvente de arcilla blanda rectangular desde coronación; q_s, γ_a = 1,5 y K = 0,5 de la sobrecarga del muro anclado sin contrastar.
```

</details>

#### Muro de terra armada (MSE): estabilidade externa (deslizamento, derrubamento, capacidade resistente) e tração/arranque das armaduras

<details><summary>Saída real de <code>python examples/mse_reinforced_soil_wall_external_stability_internal_tension_pullout_rankine_wedge_hand_check.py</code></summary>

```text
Estabilidad externa, bloque de 6,0 × 4,2 m:
  enfoque W [kN/m] P_h [kN/m]  e [m] desliz. vuelco portante  q_max
  DA1-C1     478.8      113.7  0.705   0.895  0.336    0.429  228.8
  DA1-C2     478.8      143.1  0.683   1.053  0.325    0.416  225.2  <- no cumple
  DA2        478.8      113.7  0.705   0.985  0.336    0.601  228.8
  DA3        478.8      143.1  0.887   1.383  0.423    0.569  263.2  <- no cumple
  A mano (DA2): K_a = tan²(45° − 17°) = 0.2827; W = 4,2·6·19 = 478.8; P_h = ½·K_a·19·6² + K_a·10·6 = 113.7 kN/m

Estabilidad interna (DA2), por capa:
  steel_strip:
    z [m]  T_max  T_adm tracción   L_a L necesaria arrancam.
    0.375   3.63   50.0    0.073  2.99        3.26     0.219
    1.125   6.65   50.0    0.133  2.59        2.86     0.165
    1.875   9.67   50.0    0.193  2.19        2.46     0.132
    2.625  12.70   50.0    0.254  1.79        2.06     0.110
    3.375  15.72   50.0    0.314  1.40        1.66     0.095
    4.125  18.74   50.0    0.375  1.00        1.26     0.083
    4.875  21.76   50.0    0.435  0.60        0.86     0.074
    5.625  24.78   50.0    0.496  0.20        0.46     0.066
    -> todas las capas cumplen
  geogrid_pet:
    z [m]  T_max  T_adm tracción   L_a L necesaria arrancam.
    0.375   3.63   60.0    0.061  2.99        3.15     0.131
    1.125   6.65   60.0    0.111  2.59        2.75     0.098
    1.875   9.67   60.0    0.161  2.19        2.35     0.079
    2.625  12.70   60.0    0.212  1.79        1.95     0.066
    3.375  15.72   60.0    0.262  1.40        1.55     0.056
    4.125  18.74   60.0    0.312  1.00        1.16     0.049
    4.875  21.76   60.0    0.363  0.60        0.76     0.044
    5.625  24.78   60.0    0.413  0.20        0.36     0.040
    -> todas las capas cumplen

A mano, capa superior de tira (z = 0.375 m): σ_v = 19·0.375 + 10 = 17.125 kPa, T = K_a·σ_v·S_v = 3.631 kN/m; L_a = (6 − 0.375)/tan 62° = 2.991 m, L_e = 4,2 − L_a = 1.209 m; arrancamiento 2·L_e·0,40·σ_v = 16.57 kN/m -> utilización 0.219
Límites: K_r = K_a en todas las capas y superficie de Rankine desde el pie para cualquier armadura (AASHTO distingue armaduras inextensibles con K_r/K_a > 1 y superficie bilineal, sin contrastar aquí); arrancamiento sin factor de escala ni coeficientes parciales; la utilización de arrancamiento de la capa superior es grande porque σ_v es pequeña cerca de coronación.
```

</details>

### 5. Estacas e fundações profundas

#### Capacidade axial segundo a EN 1997-1: fuste e ponta pelos métodos α e β, fatores de correlação ξ_3/ξ_4 e fatores parciais

<details><summary>Saída real de <code>python examples/pile_axial_capacity_en1997_alpha_beta_shaft_base_correlation_factors_xi3_xi4_and_partial_factors.py</code></summary>

```text
Pilote Ø800 mm, L = 18.0 m; perímetro 2.5133 m, área 0.5027 m²
  Fuste arcilla: 2.5133·8·0,5·50 = 502.7 kN
  Fuste arena:   2.5133·10·0,35·σ'v(13 m) = 2.5133·10·0,35·239 = 2102.4 kN
  Punta: N_q(34°) = 29.44; σ'v(18 m) = 334 kPa; R_b = 0.5027·29.44·334 = 4942.5 kN
  R_cal = 7547.6 kN

Paquete con ξ = 1: R_b = 4942.5, R_s = 2605.0, R_c = 7547.6 kN (diferencia +0.0000 %)

perfiles    ξ3    ξ4 R_c;k [kN] con min(ξ) (antes)
       1  1.40  1.40     5391.1             5391.1
       2  1.35  1.27     5590.8             5943.0
       3  1.33  1.23     5674.9             6136.2
       5  1.29  1.15     5850.8             6563.1
  (pares ξ3/ξ4 de la Tabla A.10 recomendada tal como suelen citarse; sin contrastar aquí)

conjunto               γ_b   γ_s   γ_t R_c;d [kN]   a mano
R1 perforado          1.25  1.00  1.00     4685.0   4685.0
R2 perforado          1.10  1.10  1.00     4901.0   4901.0
R4 perforado          1.60  1.30  1.00     3637.8   3637.8
solo γ_t = 1,5        1.00  1.00  1.50     3594.1   3594.1
La punta aporta el 65 % de R_cal; de los conjuntos probados el que más reduce es «solo γ_t = 1,5» (R_c;d = 3594 kN). Los valores de γ son los que suelen citarse para pilotes perforados (EN 1997-1 Tabla A.7), sin contrastar aquí.
Límites: N_q de punta de Prandtl-Reissner salvo que se pase otro; β = 0,3 por defecto si no se da; sin rozamiento negativo ni efecto de grupo; los γ_b/γ_s de la tabla anterior son los del ejemplo, no del paquete (sus conjuntos A/M/R de cimentación superficial no traen los de pilotes).
```

</details>

#### Fatores de resistência de estacas por norma (EN 1997-1, AASHTO, AS 2159) e microestacas Bustamante-Doix

<details><summary>Saída real de <code>python examples/pile_design_factors_by_code_en1997_aashto_as2159_and_micropile_bustamante_doix_group_capacity.py</code></summary>

```text
Capacidad última: fuste 2000 kN, punta 1500 kN
  código tipo    riesgo  f_fuste f_punta  Q_d [kN]   a mano
  EU     driven  medium    0.909   0.909    3181.8   3181.8
  EU     bored   medium    0.714   0.714    2500.0   2500.0
  US     driven  medium    0.550   0.500    1850.0   1850.0
  US     bored   medium    0.450   0.400    1500.0   1500.0
  AU     bored   low       0.700   0.700    2450.0   2450.0
  AU     bored   high      0.400   0.400    1400.0   1400.0
  Los factores son los del módulo y no se han contrastado aquí con las tablas de cada norma; los 1,10/1,40 del perfil EU no son los γ_b/γ_s de la Tabla A.6/A.7 de EN 1997-1 sino un coeficiente único por tipo.

Micropilote: d_eff = max(0,15; 1,2·0,15) = 0.180 m; R_k = π·0.180·8·80 = 361.9 kN (paquete 361.9); R_d = 361.9/(1,3·1,5) = 185.6 kN (paquete 185.6)
  con q_s = 120 kPa (ensayo o práctica local): R_d = 278.4 kN
  con q_s = 200 kPa (ensayo o práctica local): R_d = 464.0 kN

Grupo de 6 micropilotes, N_d = 1400 kN, R_d por pilote 185.6 kN:
  s/d = 2.0: E = 0.667, R_grupo = 742 kN, N/R = 1.89 -> no cumple
  s/d = 2.5: E = 0.833, R_grupo = 928 kN, N/R = 1.51 -> no cumple
  s/d = 3.0: E = 1.000, R_grupo = 1114 kN, N/R = 1.26 -> no cumple
  s/d = 4.0: E = 1.000, R_grupo = 1114 kN, N/R = 1.26 -> no cumple
  Con q_s = 80 kPa y s/d = 3 hacen falta 8 micropilotes (N/R = 0.94).
  Con q_s = 120 kPa y s/d = 3 hacen falta 6 micropilotes (N/R = 0.84).
Límites: q_s por defecto es el mínimo de la tabla del módulo (valores orientativos, no de Bustamante-Doix contrastados aquí); la eficiencia de grupo E = (s/d)/3 para s/d < 3 es una simplificación del módulo, no la fórmula de Converse-Labarre; sin resistencia por punta ni pandeo del micropilote.
```

</details>

#### Atrito negativo (downdrag) numa estaca por assentamento de estrato compressível e plano neutro

<details><summary>Saída real de <code>python examples/negative_skin_friction_downdrag_above_neutral_plane_beta_method_and_declared_heuristic_eccentric_pile.py</code></summary>

```text
Pilote Ø0.6 m; relleno 0–2 m (no consolida), arcilla 2–10 m (β = 0,25), plano neutro a 8 m
  a mano: σ'v(2 m) = 36, σ'v(8 m) = 84 kPa; Q_neg = 0,25·60·π·0.6·6 = 169.6 kN
  paquete: Q_neg = 169.6 kN; carga de servicio en el plano neutro = 900 + 169.6 = 1069.6 kN (19 % más)
  Plano neutro: 4 m -> 41 kN, 6 m -> 98 kN, 8 m -> 170 kN, 10 m -> 256 kN
  El paquete no calcula la posición del plano neutro (equilibrio de fuste y punta frente a asientos): hay que darla.

Heurística de pilote con carga excéntrica (no es Brinch Hansen):
  H =    50 kN, M =     0 kN·m: H_adm =  6126.5 kN, M_adm = 24506.1 kN·m, H/H_adm + M/M_adm = 0.008 -> cumple
  H =    50 kN, M =   100 kN·m: H_adm =  6126.5 kN, M_adm = 24506.1 kN·m, H/H_adm + M/M_adm = 0.012 -> cumple
  H =   120 kN, M =   200 kN·m: H_adm =  6126.5 kN, M_adm = 24506.1 kN·m, H/H_adm + M/M_adm = 0.028 -> cumple
  K_q(z = L/2) = (1 + tan 30°)²·(1 + 0,5·6/0,8) = 11.82; H_adm = 18·6·K_q·0,8·12/2 = 6127 kN: la capacidad lateral sale de un empuje medio sobre medio fuste, sin mecanismo de rotura ni momento de plastificación del pilote. Para pilotes con carga lateral usa `solve_pile_lateral`.
```

</details>

#### Grupo de estacas com maciço rígido: distribuição tridimensional de Engesser e eficiência de Converse-Labarre

<details><summary>Saída real de <code>python examples/pile_group_rigid_cap_engesser_distribution_converse_labarre_efficiency_and_closed_by_default_status.py</code></summary>

```text
Grupo 2 × 3, Ø800 mm a 2.4 m; V = 6000 kN, H_x = 600 kN, M_y = 2000 kN·m
A mano: Σx² = 23.04 m²; N = 1000.0 ± 2000·2,4/23.04 = 1000.0 ± 208.3 kN; θ = 18.435°, E = 0.7610; E_h = 0.750; H_i = 100.0/0.750 = 133.3 kN
Paquete: E = 0.7610, E_h = 0.750
  pilote     x     y   N [kN]  H [kN]
  P11     -2.4  -1.2    791.7   133.3
  P12      0.0  -1.2   1000.0   133.3
  P13      2.4  -1.2   1208.3   133.3
  P21     -2.4   1.2    791.7   133.3
  P22      0.0   1.2   1000.0   133.3
  P23      2.4   1.2   1208.3   133.3
Sin capacidades declaradas: estado NO_CALCULADO, faltan ['axial_capacity_kN', 'lateral_capacity_kN'], all_ok = False

Con capacidades por pilote (1600 compresión, 400 tracción, 180 lateral):
  axial 0.992 = 1208.3/(1600·0.7610); lateral 0.741; gobierna P13; estado CALCULADO_CUMPLE
  Con V = 1500 kN y M_y = 6000 kN·m hay tracción: N_min = -375.0 kN, util. tracción 0.94, estado CALCULADO_CUMPLE

Eficiencia de Converse-Labarre frente a s/d (grupo 2 × 3):
  s/d = 2.00: paquete 0.656, fórmula 0.656
  s/d = 2.50: paquete 0.717, fórmula 0.717
  s/d = 3.00: paquete 0.761, fórmula 0.761
  s/d = 3.50: paquete 0.793, fórmula 0.793
  s/d = 3.99: paquete 0.818, fórmula 0.818
  s/d = 4.00: paquete 1.000, fórmula 0.818
  s/d = 5.00: paquete 1.000, fórmula 0.853
  El módulo devuelve E = 1 para s/d ≥ 4 aunque la fórmula siga dando < 1 (salto en s/d = 4) y limita E ≥ 0,5: criterio del módulo, a revisar con la práctica local.
Límites: encepado rígido y pilotes verticales iguales; reparto lateral uniforme dividido por E_h; la E_h de Mokwa y Duncan es una aproximación lineal, no sus p-multiplicadores por fila.
```

</details>

#### Estaca sob carga lateral por diferenças finitas: contraste linear com um BVP analítico e curvas p-y não lineares

<details><summary>Saída real de <code>python examples/pile_lateral_p_y_finite_differences_linear_range_vs_bvp_and_matlock_reese_then_soft_clay_free_and_fixed_head.py</code></summary>

```text
Validación lineal: EI = 200000 kN·m², k = 20000 kN/m³ (Reese en arena con cargas diminutas), L = 20.0 m, T = 1.5849 m, L/T = 12.6
  caso                         y0 FD [m]  y0 BVP [m] Matlock-Reese     M0 FD    M0 BVP
  cabeza libre, H = 0,01      4.8463e-07  4.8354e-07    4.8470e-07   0.00000   0.00000
  cabeza libre, M = 0,01      2.0426e-07  2.0339e-07    2.0384e-07   0.01000   0.01000
  encepado, H = 0,01          1.8496e-07  1.8469e-07    1.8512e-07  -0.01472  -0.01469
  M0 del encepado según Matlock y Reese: −0,93·H·T = -0.01474 kN·m

Pilote Ø0.8 m, 20 m, EI = 600000 kN·m² en arcilla blanda (Matlock, c_u = 30 kPa), H = 150 kN:
  libre   : y0 =   16.0 mm, |M|max =  344.2 kN·m a  4.4 m, M en cabeza =     0.0 kN·m, primer cero de y a 7.6 m, p máx =  37.1 kN/m
  encepado: y0 =    4.3 mm, |M|max =  358.0 kN·m a  0.0 m, M en cabeza =  -358.0 kN·m, primer cero de y a 8.2 m, p máx =  28.0 kN/m
  Resistencia última de Matlock a 2 m: p_u = (3 + γ'z/c_u + J·z/D)·c_u·D = 114.8 kN/m (tope 9·c_u·D = 216)
Límites: curvas API en arena con A = 0,9 (cíclica) siempre y k aproximado; la curva de Reese es la envolvente hiperbólica simplificada; API en arcilla cíclica con reducción lineal propia del módulo.
```

</details>

### 6. Ensoleiramentos, cadeia integral e API REST

#### Ensoleiramento sobre fundação elástica (Mindlin): contraste com Hetényi, descolamento elastoplástico e exportação

<details><summary>Saída real de <code>python examples/mat_foundation_mindlin_plate_on_winkler_springs_uniform_load_rigid_limit_equilibrium_uplift_and_exports.py</code></summary>

```text
1) Carga uniforme q = 20 kPa, k_s = 20000 kN/m³: w = q/k_s = 1.000 mm
   paquete: w entre 1.000000 y 1.000000 mm; |M| máx = 1.96e-12 kN·m/m

2) Losa casi rígida (h = 3 m), ΣP = 7100 kN, resultante en (6.000, 5.246) m:
   sólido rígido sobre muelles: w0 = ΣP/(k_s·A) = 2.958 mm, giros 0.00e+00 y 8.75e-05 rad
   paquete: w medio 2.956 mm; diferencia máxima con el plano rígido 0.060 mm (2.0 % de w0)

3) Losa 12 × 10 × 0,7 m con peso propio 17.5 kPa y los 6 pilares:
   Σ reacciones de muelles = 9200.0 kN; ΣP + q·A = 9200.0 kN (cierre +0.000 %)
   pilar ( 3.0, 2.5) P =   900 kN: asiento  3.94 mm, presión   78.9 kPa
   pilar ( 6.0, 2.5) P =  1400 kN: asiento  4.88 mm, presión   97.7 kPa
   pilar ( 9.0, 2.5) P =   900 kN: asiento  3.94 mm, presión   78.9 kPa
   pilar ( 3.0, 7.5) P =  1100 kN: asiento  4.46 mm, presión   89.1 kPa
   pilar ( 6.0, 7.5) P =  1700 kN: asiento  5.49 mm, presión  109.9 kPa
   pilar ( 9.0, 7.5) P =  1100 kN: asiento  4.46 mm, presión   89.1 kPa
   asiento diferencial 4.00 mm; M_xx máx 388 y mín -1 kN·m/m; 1 iteración(es), despegue en 0 nudos

4) Pilar central de 3000 kN y tracción de 900 kN en la esquina (0,5; 0,5):
   261 nudos despegados tras 6 iteraciones (convergido: True); Σ reacciones = 2100.0 kN frente a ΣP = 2100 kN; w en la esquina traccionada -22.71 mm

Exportado: losa_12x10.json (156 kB) y losa_12x10.s2k (2484 líneas) en out/
Límites: cargas de pilar en el nudo más cercano (dependen de la malla), k_s único, sin interacción entre muelles; el .s2k es un punto de partida (no se ha abierto en SAFE desde este paquete) y su etiqueta de material es «C<fck>/37» sea cual sea la clase.
```

</details>

#### API REST FastAPI: endpoints de sapatas, muros, estacas, capacidade resistente e impulsos sísmicos

<details><summary>Saída real de <code>python examples/fastapi_rest_api_client_and_services_isolated_cantilever_and_piles.py</code></summary>

```text
C:\Users\jesus\AppData\Local\Temp\jmv\foundationcalc\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
=== foundationcalc v1.1.0 — API REST FastAPI ===

1. GET / -> Nombre: FoundationCalc
   Endpoints registrados: 6
     - /api/footings/isolated
     - /api/walls/cantilever
     - /api/piles/axial
     - /api/bearing/multilayer
     - /api/seismic/mononobe_okabe
     - /jobs/*

2. POST /api/footings/isolated (Zapata 2,5×2,5 m, N = 1500 kN):
   q_max = 316.80 kPa, q_min = 163.20 kPa, q_avg = 240.00 kPa
   Punzonamiento DCR = 0.422 (Vu = 1260.0 kN, Vc = 3976.5 kN)
   Armado flexión X: As_req = 1702 mm², elegido = 2268 mm²
   Armado flexión Y: As_req = 1702 mm², elegido = 2268 mm²
   [OK] Coincidencia exacta con footings.design_isolated_footing

3. POST /api/walls/cantilever (Muro ménsula H = 4,5 m):
   FS deslizamiento = 1.069
   FS vuelco        = 2.864
   bearing_FS       = None (sin evaluate_bearing no se evalúa)
   Fuste: M_stem = 107.1 kN·m/m, espesor mín = 350 mm
   [OK] Coincidencia exacta con walls.design_cantilever_wall
   Con evaluate_bearing = true: bearing_FS = q_Rd/q_Ed = 129.3/138.5 = 0.93 (EN 1997-1, resistencia y acción ya de cálculo: cumple si ≥ 1, no es un FS global de 3)

4. POST /api/piles/axial (Pilote Ø0,8 m, L = 15 m en arcilla):
   Q_skin      = 1256.6 kN
   Q_tip       = 361.9 kN
   Q_ultimate  = 1618.5 kN
   Q_allowable = 539.5 kN (FS = 3.0)
   [OK] Equilibrio de capacidad axial verificado

5. POST /api/bearing/multilayer (Zapata 2,5×2,5 m, estrato Vesić):
   qu = 1172.08 kPa, qa = 390.69 kPa (FS = 3.0)
   0.3 m de arena bajo la base sobre arcilla c_u = 25 kPa, method = vesic          : qu =   1975.1 kPa  (solo mira el estrato de apoyo)
   0.3 m de arena bajo la base sobre arcilla c_u = 25 kPa, method = meyerhof_hanna : qu =    194.8 kPa  (Punzonamiento Meyerhof-Hanna: q_punch = 194.8 kPa (estrato superior = 1946.5 kPa, inferior)

6. POST /api/seismic/mononobe_okabe (H = 5 m, kh = 0,15, kv = 0,05):
   K_AE = 0.3606, P_AE = 81.37 kN/m, theta = 8.97°

Límites documentados:
  - Los endpoints de la API delegan en los servicios predimensionadores.
  - /api/footings/isolated usa tensiones admisibles frente a ACI 318-19, no Eurocódigo 7.
  - /api/walls/cantilever devuelve bearing_FS nulo salvo con evaluate_bearing = true (CantileverWallDesigner, EN 1997-1).
  - /api/bearing/multilayer con el método por defecto solo mira el estrato de apoyo; con method = meyerhof_hanna comprueba el punzonamiento del inferior.
```

</details>

## Verificação

A bateria de testes consta de 75 testes executados automaticamente no GitHub Actions com Python 3.11, 3.12 e 3.13 em Ubuntu e Windows.

- **Testes de referência de capacidade resistente (`test_golden_w00675_bearing_factors.py`)**: ancorados na ficha W00675 do Eurocódigo 7, verificando os fatores N_q, N_c e N_γ contra os desenvolvimentos analíticos exatos de Prandtl, Reissner e Vesić.
- **Testes de referência de punçoamento (`test_golden_punching_compact.py`, `test_golden_aci318_punching_shear_moment.py`)**: verificam o varrimento de perímetros de controlo reduzidos dentro de 2d segundo a EN 1992-1-1 §6.4.4(2) e a transmissão de momento por excentricidade do esforço transverso γ_v segundo a ACI 318-19.
- **Testes de referência de impulsos sísmicos (`test_golden_w00678_mononobe_okabe.py`)**: contrastam o impulso dinâmico ativo K_AE com os exemplos numéricos da ficha W00678 do mestrado da UPC.
- **Testes de tensões de Boussinesq e de consolidação (`test_golden_boussinesq_newmark.py`, `test_golden_consolidacion_terzaghi.py`)**: validam as soluções fechadas de cargas retangulares e circulares face aos ábacos de Newmark e a integrais numéricos independentes.
- **Testes de vigas de travamento e de equilíbrio (`test_golden_nsr10_tie_beam.py`)**: verificam o esforço axial de cálculo sísmico 0,25·A_a·P e os requisitos de rigidez à flexão.
- **Testes de execução dos exemplos (`tests/test_examples.py`)**: executam os 30 casos de uso como processos independentes, garantindo que todo o código do manual termina com código de saída 0.

## Limitações

- **Capacidade resistente multicamada**: `services.bearing.bearing_capacity_multilayer` (e `/api/bearing/multilayer`) com o método por defeito só avalia o estrato de apoio, a via descontinuada; com `method="meyerhof_hanna"` delega em `analysis.multi_layer_bc` e verifica o punçoamento do estrato inferior (Meyerhof e Hanna, 1978), sem contrastar aqui com um caso publicado. O caso da API mostra a diferença: 1975 face a 195 kPa com 0,3 m de areia sobre argila mole.
- **Pré-dimensionamento de muros na API**: `/api/walls/cantilever` devolve `bearing_FS = null` salvo com `evaluate_bearing = true`, que passa por `CantileverWallDesigner` (EN 1997-1). Esse `bearing_FS` é q_Rd/q_Ed com valores já de cálculo: cumpre se for ≥ 1, não é um fator global comparável a 3. Os FS de deslizamento e derrubamento continuam a ser os globais de Rankine.
- **Sapatas combinadas**: o módulo atual dimensiona sapatas de dois pilares; configurações complexas de três ou mais pilares alinhados devem ser modeladas como vigas contínuas sobre fundação elástica ou como ensoleiramentos.
- **Diferenças finitas em estacas sob carga lateral**: a formulação implementada em `pile_lateral` modela estacas de secção constante; variações escalonadas de inércia ou estratigrafias com inversão brusca de rigidez devem ser discretizadas com malhas refinadas.
- **Ensoleiramento Mindlin**: a análise elastoplástica de descolamento em `analysis.mat_foundation` usa um esquema de rigidez secante nas molas de Winkler que converge para descolamentos moderados (< 30 % da área); descolamentos severos exigem análise não linear com contacto com atrito em software especializado.

## Normas e referências

- **EN 1997-1:2004 / Eurocódigo 7**: *Projeto geotécnico — Regras gerais*. Equação geral da capacidade resistente (Anexo D), coeficientes parciais (Anexo A) e impulsos de terras (§9).
- **EN 1992-1-1:2004 / Eurocódigo 2**: *Projeto de estruturas de betão — Regras gerais e regras para edifícios*. Flexão de sapatas (§9.8) e verificação do punçoamento com perímetros de controlo reduzidos (§6.4.4).
- **EN 1998-5:2004 / Eurocódigo 8**: *Projeto de estruturas para resistência aos sismos — Fundações, estruturas de suporte e aspetos geotécnicos*. Inércia do bloco de fundação e impulsos sísmicos de Mononobe-Okabe (Anexo E).
- **ACI 318-19**: *Building Code Requirements for Structural Concrete*. Punçoamento biaxial com transmissão de momento desequilibrado (§22.6 e §8.4) e dimensionamento de ancoragens ao betão (Capítulo 17).
- **NSR-10**: *Reglamento Colombiano de Construcción Sismo Resistente*. Requisitos para vigas de travamento e fundações superficiais (Título A e Título C).
- **AASHTO LRFD Bridge Design Specifications (9.ª Edição)**: Fatores de resistência para fundações profundas e sapatas.
- **Vesić, A. S. (1973)**: *Analysis of Ultimate Bearing Capacity of Shallow Foundations*. Journal of the Soil Mechanics and Foundations Division, ASCE.
- **Robertson, P. K. (1990, 2009)**: *Soil behaviour type from the CPT: an update*. Canadian Geotechnical Journal.
- **Bustamante, M., & Doix, B. (1985)**: *Une méthode pour le calcul des tirants et des micropieux injectés*. Bulletin de liaison des Laboratoires des Ponts et Chaussées.
- **Steinbrenner, W. (1934)**: *Tafeln zur Setzungsberechnung*. Die Strasse, 1, 121-124.

## Licença

Distribuído sob a licença [MIT](LICENSE).

---

Parte do **Loadpath**, a coleção de bibliotecas estruturais de código aberto de [Jesús Murgas](https://github.com/jmurgass99).
