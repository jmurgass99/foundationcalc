# FoundationDesignJm - Testing Guide

## Filosofia

FoundationDesignJm es **safety-critical**: sus resultados gobiernan
decisiones de seguridad estructural reales. Por eso:

- **Coverage gate inicial: 70%** (mas alto que otros satelites).
- **Tests safety-critical**: validan contra valores conocidos de bibliografia
  (Bowles, Coduto, EC7 worked examples) con tolerancia <= 10%.
- **Property-based tests**: hypothesis genera casos extremos para detectar
  fallas en formulas que pasarian tests deterministas.
- **Examples como tests**: los 15 ejemplos del manual UPC corren como
  subprocess; si la docs miente, CI lo detecta.

## Markers

| Marker | Aplicar cuando |
|---|---|
| `unit` | Test rapido sin dependencias externas (<100ms) |
| `integration` | Requiere multiples modulos o scipy heavy |
| `slow` | Duracion > 5s |
| `fastsap` | Requiere puente FastSAP funcional (omitir si no hay SAP) |
| `safety_critical` | Comparado contra valor publicado |
| `examples` | Ejecuta examples/*.py como subprocess |
| `property` | Property-based con hypothesis |

## Comandos

```bash
# Suite rapida diaria
pytest -m "not slow and not examples and not gpu and not fastsap"

# Suite completa pre-release
pytest -m "not gpu"

# Solo safety-critical (validacion rigurosa)
pytest -m safety_critical

# Coverage con HTML
.\scripts\run_coverage.ps1 -Open
```

## Gate

`pyproject.toml`: `fail_under = 70`. Subir incrementalmente.

## Property-based

Strategies en `tests/test_property_invariants.py`:
- `valid_phi`: 15-45 grados
- `valid_cohesion`: 0-200 kPa
- `valid_gamma`: 14-22 kN/m3
- ... etc.

Invariantes verificadas:
- `qu > 0` para todo suelo valido
- `qu_seismic <= qu_static` para mismo suelo
- `K_AE >= Ka_static` para Mononobe-Okabe
- `q_avg = N/Ag` para zapatas axial puro
