# foundationcalc

Diseño de cimentaciones según EN 1997-1, EN 1998-5, ACI 318 y NSR-10: capacidad portante drenada y no drenada con factores parciales por enfoque de diseño, presiones en la base, asientos y consolidación, zapatas aisladas, combinadas y con viga centradora, losas de cimentación (Winkler), capacidad de pilotes y grupos, encepados, muros de contención en ménsula, de sótano, con contrafuertes, de tierra armada y pantallas, punzonamiento, armado, flotación, cimentaciones de grúas, diseño inverso desde CPT y SPT, refuerzo de cimentaciones existentes, memorias de cálculo e informes PDF, y aplicaciones de escritorio y tablero.

[![CI](https://github.com/jmurgass99/foundationcalc/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/foundationcalc/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Paquete independiente. Dependencias: `pydantic`, `reportlab`.

## Instalación

```bash
pip install git+https://github.com/jmurgass99/foundationcalc.git
```

Extras: `numeric` (numpy, scipy, pandas), `plot` (matplotlib, plotly), `desktop`, `dashboard` (Streamlit), `api` (REST), `memos` (handcalcs), `examples` (PyNite), `test`.

```bash
foundationcalc-desktop      # aplicación de escritorio
foundationcalc-dashboard    # tablero Streamlit
```

## Inicio rápido

Zapata aislada en arena seca con enfoque de diseño DA1-C2 de EC7:

```python
from foundationcalc import (
    Column, DesignApproach, LimitState, LoadType, PointLoad, RectangularFoundation,
    SoilLayer, SoilType, drained_bearing_capacity, get_partial_factors,
)

fdn = RectangularFoundation(length=2500, width=1500, thickness=500, embedment_depth=500)   # mm
col = Column(length=400, width=400, pos_x=1250, pos_y=750)
g = PointLoad(fz=800, load_type=LoadType.PERMANENT)      # kN
q = PointLoad(fz=450, load_type=LoadType.IMPOSED)
sand = SoilLayer(name="arena seca", thickness=10, soil_type=SoilType.COHESIONLESS,
                 friction_angle=35, cohesion=0, unit_weight=18)
pf = get_partial_factors(DesignApproach.DA1_C2, LimitState.GEO)
res = drained_bearing_capacity(foundation=fdn, soil=sand,
                               gamma_Rv=pf.resistance.gamma_Rv, gamma_phi=pf.soil.gamma_phi)
print(f"q_ult = {res.q_ult:.1f} kPa, φ_d = {res.phi_d_deg:.1f}°")
```

La carpeta `examples/` contiene 15 scripts ejecutables: diseño completo de zapata, zapata combinada, losa sobre Winkler, muro en ménsula y de sótano, cimentación de grúa, diseño desde CPT, diseño inverso y grupo de pilotes, EC8 e impedancias, zapata sísmica, refuerzo y generación de informes PDF.

## Módulos

| Paquete | Contenido |
|---|---|
| `core` | Geometría, cargas y combinaciones, materiales, suelo, pilotes |
| `codes` | `eurocode7`, `eurocode8`, `aci`, `asce`, FEMA P-58 |
| `analysis` | Capacidad portante, multicapa, presiones en la base, Boussinesq, asientos, consolidación, CPT y SPT, Winkler, losas, grupos de pilotes, pilotes laterales, sísmica, estabilidad, grúas, diseño inverso |
| `design` | Zapatas combinadas y con viga centradora, encepados, muros (ménsula, sótano, contrafuertes, MSE, pantalla, anclado), punzonamiento, armado, flotación, refuerzo |
| `pile_capacity_multi`, `crack_width_ec2`, `consolidacion_1d`, `excavations`, `dynamics` | Cálculos complementarios |
| `memos/`, `reports/`, `utils/` | Memorias, informes PDF (reportlab y matplotlib), exportación DXF |
| `services/`, `api/`, `jobs` | Servicios, REST y tareas |
| `desktop/`, `dashboard/` | Aplicaciones (extras `desktop` y `dashboard`) |
| `integration/` | Cadena de cimentación, puentes a terzaghi, seismodyn, rebardxf y fastsap (opcionales; sus tests se omiten si faltan) |

## Validación

Tests golden contra fichas resueltas (factores de capacidad portante W00675, Mononobe-Okabe W00678), punzonamiento ACI 318 con momento, viga de atado NSR-10, consolidación de Terzaghi, Boussinesq y Newmark, zapata combinada con solape, cambio automático a encepado, y tests marcados `safety_critical` con tolerancia frente a valores publicados (553 tests).

## Licencia

MIT. Consulta [LICENSE](LICENSE).

---

Parte del toolkit estructural de código abierto **Loadpath**, de [Jesús Murgas](https://github.com/jmurgass99).
