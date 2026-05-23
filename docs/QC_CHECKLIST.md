# Checklist de Quality Control (QC)

> Adaptado de [Flocode Prompt Library](https://github.com/flocode/Flocode-Prompt-Library) (MIT)

Este checklist documenta el proceso de QC que **todo cálculo o función de diseño
de este satélite debe pasar** antes de merge a `main` o release.

## A. Unidades y dimensionalidad

- [ ] Todas las entradas/salidas tienen unidades documentadas en docstring (SI o imperial explícito).
- [ ] Conversiones entre unidades están encapsuladas en helpers, no inline.
- [ ] Tests verifican consistencia dimensional en al menos un caso por función pública.

## B. Cumplimiento normativo

- [ ] Cada función cita la norma + sección específica (e.g. "AISC §J3.6", "EC2 §5.8.8").
- [ ] Cuando aplica más de una norma, hay parámetro `standard` o módulos separados.
- [ ] Factores de minoración (φ, γ) son explícitos, no hardcoded sin contexto.

## C. Spot-checks contra bibliografía

- [ ] Al menos 1 test `@pytest.mark.safety_critical` por función pública compara
      contra un ejemplo numérico publicado (Bowles, Coduto, AISC examples, etc.).
- [ ] Tolerancia documentada en el test (típico ≤ 5% para cálculos exactos,
      ≤ 10% para métodos donde la norma admite variación).

## D. Validación de inputs

- [ ] Geometrías inválidas (espesores ≤ 0, ángulos fuera de tabla, etc.) lanzan
      `GeometryError` con mensaje claro.
- [ ] Materiales no soportados lanzan `CodeError` o `ConfigurationError` con la
      lista de soportados.
- [ ] Iteraciones que pueden no converger lanzan `ConvergenceError(iteration, residual)`.

## E. Convergencia numérica (si aplica)

- [ ] Solvers iterativos tienen `max_iter` y `tol` como parámetros configurables.
- [ ] Default `tol` documentado y razonable (≤ 1e-4 relativo).
- [ ] Log debug del progreso de iteración disponible (`log.debug` no `print`).

## F. Tests

- [ ] Coverage del módulo modificado ≥ gate del repo (ver `pyproject.toml`).
- [ ] Property tests con `hypothesis` cuando hay invariantes físicas obvias.
- [ ] Tests headless (sin SAP/ETABS/red) usando mocks o fixtures.

## G. Backward compatibility

- [ ] Funciones públicas existentes no cambian de firma sin warning de deprecación.
- [ ] Si se añade un parámetro nuevo, tiene default que preserva comportamiento anterior.
- [ ] Custom exceptions nuevas multi-heredan de `ValueError`/`ImportError` cuando reemplazan raises previos.

## H. Documentación

- [ ] Docstring en castellano con `Args:`, `Returns:`, `Raises:`.
- [ ] Ejemplos en `examples/` si la función es de API pública.
- [ ] Referencias bibliográficas en el docstring del módulo.

## I. Seguridad y datos sensibles

- [ ] Sin credenciales, tokens o paths absolutos del autor en el código.
- [ ] Sin datos de proyectos reales de clientes en `examples/` (usar sintéticos).
- [ ] `.gitignore` cubre `*.env`, `*.key`, `*.pem`.

## J. Review

- [ ] Pre-commit hooks pasan (`black`, `ruff`, `pytest`).
- [ ] CI verde en GitHub Actions.
- [ ] Self-review final: leer el diff completo antes de pushear.

---

**Cómo usar**: marca cada checkbox aplicable al PR/commit que estás haciendo.
Si alguno no aplica, anota la razón en el commit message.
