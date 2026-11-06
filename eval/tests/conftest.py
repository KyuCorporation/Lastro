"""Testes do harness (sem banco e sem API): `make test-eval`. Põe eval/ no caminho de importação."""

import sys
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL))
