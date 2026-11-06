"""Tratadores de erro da API: tudo sai no formato do contrato, e banco fora do ar é 503, não 500."""

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import PoolTimeout

from app.core.errors import registrar_tratadores


def _app_que_levanta(erro: Exception) -> TestClient:
    app = FastAPI()
    registrar_tratadores(app)

    @app.get("/x")
    def rota() -> None:
        raise erro

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "erro",
    [
        psycopg.OperationalError("connection refused"),
        PoolTimeout("couldn't get a connection after 30.00 sec"),
        psycopg.errors.QueryCanceled("canceling statement due to statement timeout"),
    ],
    ids=["sem-conexao", "pool-esgotado", "tempo-esgotado"],
)
def test_banco_indisponivel_e_503_no_formato_do_contrato(erro):
    r = _app_que_levanta(erro).get("/x")
    assert r.status_code == 503
    corpo = r.json()["erro"]
    assert corpo["codigo"] == "FONTE_INDISPONIVEL"
    assert corpo["request_id"] == r.headers["X-Request-ID"]
    assert "connection" not in corpo["mensagem"]  # detalhe interno não vaza


def test_erro_inesperado_continua_500_sem_detalhe():
    r = _app_que_levanta(RuntimeError("segredo interno")).get("/x")
    assert r.status_code == 500
    assert r.json()["erro"]["codigo"] == "ERRO_INTERNO"
    assert "segredo" not in r.text
