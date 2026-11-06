"""Cliente da API com dependências fixas: data de hoje do catálogo, sem LLM (mock) e limite de taxa zerado."""

import json
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.limite_taxa import LimitadorJanela
from app.main import app
from app.modules.catalogo.tests.conftest import HOJE, dados_catalogo  # noqa: F401
from app.modules.consulta import dependencias
from app.modules.consulta.service import Ambiente


class ProvedorFalso:
    """LLM de mentira: `planos` responde ao planejador (json=True), `textos` ao redator."""

    nome = "falso"
    modelo = "falso-1"

    def __init__(self, plano: dict | None = None, texto: str | None = None) -> None:
        self.plano, self.texto = plano, texto
        self.chamadas: list[tuple[bool, str]] = []

    def gerar(self, prompt, *, json: bool = False, timeout_s, temperatura=0.0) -> str:
        self.chamadas.append((json, prompt))
        if json:
            return _json(self.plano)
        return self.texto or ""


def _json(dados) -> str:
    return json.dumps(dados)


@pytest.fixture
def com_ambiente() -> Iterator[Callable[..., None]]:
    """Troca o ambiente da rota. Sem chamar: modo mock com a data de hoje dos dados de teste."""

    def trocar(provedor=None, limite: int = 1000, timeout_s: float = 20.0) -> None:
        app.dependency_overrides[dependencias.ambiente] = lambda: Ambiente(
            provedor=provedor, hoje=lambda: HOJE, timeout_s=timeout_s
        )
        limitador = LimitadorJanela(limite, 60)
        app.dependency_overrides[dependencias.limitador_consultas] = lambda: limitador

    trocar()
    yield trocar
    app.dependency_overrides.clear()


@pytest.fixture
def api(com_ambiente, dados_catalogo) -> TestClient:  # noqa: F811
    return TestClient(app)


@pytest.fixture
def autenticar(api) -> Callable[[str], dict[str, str]]:
    def cabecalho(email: str) -> dict[str, str]:
        r = api.post("/auth/login", json={"email": email, "senha": "demo123"})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}

    return cabecalho
