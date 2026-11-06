"""Fixtures de teste. Nada aqui acessa a rede: HTTP usa `httpx.MockTransport`, dados vêm de data/fixtures."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import psycopg
import pytest

from lastro_pipeline.config import Settings
from lastro_pipeline.http import ClienteHttp, LimitadorTaxa

RAIZ_REPO = Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    candidatos = [os.environ.get("DATA_DIR"), RAIZ_REPO / "data", "/data"]
    for candidato in candidatos:
        if candidato and (Path(candidato) / "fixtures").is_dir():
            return Path(candidato)
    raise RuntimeError("data/fixtures não encontrado")


DATA_DIR = _data_dir()
FIXTURES = DATA_DIR / "fixtures"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings isolados: bronze e cache em diretório temporário, fixtures do repositório."""
    return Settings(
        database_url=os.environ.get("DATABASE_URL", ""),
        data_dir=tmp_path,
        pncp_ufs="AL",
        pncp_pe_fallback=False,
        pncp_data_inicial="20261001",
        pncp_data_final="20261031",
        tcepe_anos="2025",
        tcepe_esferas="E,M",
        tcepe_municipios="",
    )


@pytest.fixture
def cliente_falso() -> Callable[..., ClienteHttp]:
    """Fábrica de ClienteHttp com transporte simulado, sem espera real entre requisições."""

    def fabricar(
        rotas: Callable[[httpx.Request], httpx.Response], cache_dir: Path | None = None
    ) -> ClienteHttp:
        return ClienteHttp(
            "teste",
            cache_dir,
            transporte=httpx.MockTransport(rotas),
            limitador=LimitadorTaxa(1000, dormir=lambda _s: None),
            espera_minima=0,
            espera_maxima=0,
            tentativas=3,
        )

    return fabricar


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """Conexão como lastro_ingest dentro de uma transação desfeita no fim: o teste não deixa resíduo no banco."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL ausente: testes de banco rodam com `make test-pipeline` (Compose)")
    with psycopg.connect(url, autocommit=True) as conexao, conexao.transaction(force_rollback=True):
        yield conexao
