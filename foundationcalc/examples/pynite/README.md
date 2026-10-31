# Pynite cross-validation examples

Ejemplos adaptados de [Engineering-Fundamentals](https://github.com/flocode/Engineering-Fundamentals)
(Flocode, MIT) que sirven como **validación cruzada externa** contra
nuestros propios solvers.

## Examples

- **`beam_elastic_foundation.py`** — Viga sobre fundación elástica
  (resortes de Winkler) — valida nuestro modelo de
  `foundationcalc/analysis/winkler.py`.
- **`hydrostatic_loads.py`** — Patrón de carga hidrostática reusable
  en muros de contención y cimentaciones bajo nivel freático.

## Ejecutar

```bash
pip install -e ".[examples]"   # incluye PyniteFEA
python -m foundationcalc.examples.pynite.beam_elastic_foundation
python -m foundationcalc.examples.pynite.hydrostatic_loads
```

## Licencia / origen

Adaptado de https://github.com/flocode/Engineering-Fundamentals (MIT).
