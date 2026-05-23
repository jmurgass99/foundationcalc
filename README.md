# FoundationDesignJm

[![CI](https://github.com/jmurgass99/foundationdesignjm/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/foundationdesignjm/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-80.38%25-brightgreen?style=flat)](https://github.com/jmurgass99/foundationdesignjm)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Proprietary-red)]()

Eurocode-based foundation design library for Python. Re-implements the theory
of the *Foundation Structures* course (UPC, Master in Structural and
Construction Engineering) with a modern, modular API:

- **Eurocode 7 (EN 1997-1)**: full Design Approach support (DA-1 C1/C2, DA-2,
  DA-2*, DA-3) with switchable National Annex profiles (EU default, Spain).
- **Bearing capacity** per EC7 Annex D — Brinch-Hansen, Meyerhof, Vesic and
  Chen / EC7 N_γ formulae, with shape, depth, inclination and base-tilt
  factors; drained and undrained cases.
- **Lateral earth pressure**: at-rest (Jaky / Mayne-Kulhawy), Rankine and
  Coulomb (active + passive), tension crack, heel-width check.
- **Mononobe-Okabe** seismic earth pressure (EC8-5), liquefaction screening
  (EC8 §4.1.4), reinforced-earth wall external stability.
- **Pressure under footings**: Navier with `e > L/6` handling (uniaxial
  triangular pressure) + biaxial corner pressures.
- **Concrete design (EC2)**: punching shear at the 2·d perimeter, flexural
  reinforcement, strut-and-tie for rigid pad footings and pile caps (2, 3,
  4+ piles).
- **Sliding / overturning** stability checks for shallow foundations and
  retaining walls.
- **Strap beams** (statics + EC8 seismic tie-beam forces by ground type).
- **Piles**: pile, pile group, pile-cap rigid-distribution, calculation-method
  axial capacity (drained + undrained).
- Layered **SoilProfile** with WT splitting and effective-stress calculations.

## Theory and references

The full theory base used by the library is in `docs/theory/`:

| # | Document |
|---|----------|
| 01 | Introduction to foundation structures |
| 02 | Geotechnical Design according to Eurocode 7 |
| 03 | Shallow Foundations (structural design) |
| 04 | EC7 worked examples |
| 05 | Deep Foundations (piles & pile caps) |
| 06 | Retaining Walls |
| 07 | Seismic design of foundations |
| 08 | Strengthening of existing foundations |

Each module's docstring points to the document it relies on.

## Quick start

```python
from foundationdesignjm import (
    BasePressureAnalysis, Column, CombinationEntry, DesignApproach,
    LimitState, LoadCombination, LoadType, PointLoad,
    RectangularFoundation, SoilLayer, SoilType,
    drained_bearing_capacity, get_partial_factors, utilization_ratio,
)

# 1. Geometry
fdn = RectangularFoundation(length=2500, width=1500, thickness=500, embedment_depth=500)
col = Column(length=400, width=400, pos_x=1250, pos_y=750)

# 2. Loads (G + Q)
g = PointLoad(fz=800, load_type=LoadType.PERMANENT)
q = PointLoad(fz=450, load_type=LoadType.IMPOSED)

# 3. Soil (dry sand)
sand = SoilLayer(
    name="dry_sand", thickness=10, soil_type=SoilType.COHESIONLESS,
    friction_angle=35, cohesion=0, unit_weight=18,
)

# 4. Pick a Design Approach + Limit State
pf = get_partial_factors(DesignApproach.DA1_C2, LimitState.GEO)

# 5. Bearing capacity
res = drained_bearing_capacity(
    foundation=fdn, soil=sand,
    gamma_Rv=pf.resistance.gamma_Rv,
    gamma_phi=pf.soil.gamma_phi,
)
print(f"q_ult = {res.q_ult:.1f} kPa, phi_d = {res.phi_d_deg:.1f}°")
```

See [`examples/example_usage.py`](examples/example_usage.py) and
[`examples/retaining_wall_example.py`](examples/retaining_wall_example.py)
for full runs that reproduce the numerical results of the EC7 worked
examples.

## Tests

60 unit tests are included and validate the implementation against the
numerical examples from the reference course PDFs (pad footing on dry sand,
cantilever wall on clay, Mononobe-Okabe, liquefaction screening, etc.):

```bash
python -m pytest tests/
```

## Project layout

```
foundationdesignjm/
├── core/            # Geometry, materials, soil profile, piles, loading
├── codes/           # Eurocode 7 partial factors and DA selectors
├── analysis/        # Bearing capacity, base pressure, stability,
│                    # earth pressure, seismic, pile capacity
└── design/          # Reinforcement, punching shear, strap beams, pile caps

tests/               # 60 pytest cases validating against the PDF examples
examples/            # End-to-end use cases (footing + retaining wall)
docs/theory/         # Theory extracted from the UPC course PDFs
```

## Ecosystem

This project is part of the **jmurgass99 structural engineering ecosystem**:

- [fastsap](https://github.com/jmurgass99/fastsap) - orquestador SAP2000/ETABS
- [dynamicsjmpro](https://github.com/jmurgass99/dynamicsjmpro) - SaaS frontend + backend
- [dynamicsjm](https://github.com/jmurgass99/dynamicsjm) - motor dinamico
- [foundationdesignjm](https://github.com/jmurgass99/foundationdesignjm) - cimentaciones
- [windloadjm](https://github.com/jmurgass99/windloadjm) - cargas de viento
- [seismicrecordsjm](https://github.com/jmurgass99/seismicrecordsjm) - records sismicos
- [slopestabilityjm](https://github.com/jmurgass99/slopestabilityjm) - estabilidad de taludes
- [steelconnectionjm](https://github.com/jmurgass99/steelconnectionjm) - conexiones de acero
- [steeloptimizerjm](https://github.com/jmurgass99/steeloptimizerjm) - optimizacion GA
- [coldformedjm](https://github.com/jmurgass99/coldformedjm) - acero conformado en frio
- [fatiguejm](https://github.com/jmurgass99/fatiguejm) - analisis de fatiga
- [firesteeljm](https://github.com/jmurgass99/firesteeljm) - analisis termico al fuego
- [dxfstructuraljm](https://github.com/jmurgass99/dxfstructuraljm) - generacion DXF
