"""Integração: a API de pé (HTTP de verdade), com o banco preparado por `make demo`
(migrations, seeds e `ingest todas --offline` a partir de data/fixtures).

Não usa TestClient nem troca dependências: é o mesmo caminho que o navegador faz.
"""

import os
import time
from collections.abc import Callable

import httpx
import pytest

from app.modules.catalogo.tests.conftest import _superusuario

URL = os.environ.get("LASTRO_API_URL", "")


@pytest.fixture(scope="session")
def http() -> httpx.Client:
    if not URL:
        pytest.fail("LASTRO_API_URL ausente: rode com `make test-integracao` (sistema de pé com `make demo`)")
    with httpx.Client(base_url=URL, timeout=30) as cliente:
        yield cliente


@pytest.fixture(scope="session")
def cabecalho(http) -> Callable[[str], dict[str, str]]:
    tokens: dict[str, str] = {}

    def de(email: str) -> dict[str, str]:
        if email not in tokens:
            r = http.post("/auth/login", json={"email": email, "senha": "demo123"})
            assert r.status_code == 200, r.text
            tokens[email] = r.json()["token"]
        return {"Authorization": f"Bearer {tokens[email]}"}

    return de


@pytest.fixture(scope="session")
def perguntar(http, cabecalho) -> Callable[[str, str], httpx.Response]:
    def enviar(email: str, pergunta: str) -> httpx.Response:
        """Respeita o limite de 30 consultas por minuto: no 429, espera o Retry-After e tenta de novo."""
        for _ in range(3):
            r = http.post("/consultas", json={"pergunta": pergunta}, headers=cabecalho(email))
            if r.status_code != 429:
                return r
            time.sleep(int(r.headers.get("Retry-After", "5")))
        return r

    return enviar


@pytest.fixture(scope="session")
def banco_superusuario():
    """Só para conferir o que a API gravou (auditoria encadeada, execuções). Nunca para preparar dados."""
    with _superusuario() as conn:
        yield conn
