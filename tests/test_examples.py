"""Cada examples/*.py debe ejecutarse limpio (exit 0).

Validacion documentation-driven: si los ejemplos rompen, el manual UPC
esta mintiendo. Cada ejemplo corre como subprocess aislado.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

import pytest


# Ejemplos no aptos para CI (GUI bloqueante, etc.)
_SKIP_EXAMPLES: set[str] = set()


def _list_examples() -> list[Path]:
    root = Path(__file__).resolve().parents[1] / "examples"
    if not root.exists():
        return []
    return sorted(root.glob("*.py"))


_EXAMPLES = _list_examples()
_IDS = [p.name for p in _EXAMPLES]


@pytest.mark.examples
@pytest.mark.slow
@pytest.mark.parametrize("example_path", _EXAMPLES, ids=_IDS)
def test_example_runs_clean(example_path: Path) -> None:
    """Cada example.py debe terminar con exit 0 en <= 90s."""
    if example_path.name in _SKIP_EXAMPLES:
        pytest.skip(f"Marcado como no-CI: {example_path.name}")
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    env.setdefault("PYTHONUTF8", "1")
    try:
        result = subprocess.run(
            [sys.executable, str(example_path)],
            capture_output=True, text=True, timeout=90, env=env,
            cwd=str(example_path.parent.parent),
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"Timeout 90s: {example_path.name}")
    if result.returncode != 0:
        msg = (f"Example {example_path.name} exit={result.returncode}\n"
                f"STDOUT: {result.stdout[-500:]}\n"
                f"STDERR: {result.stderr[-500:]}")
        pytest.fail(msg)
