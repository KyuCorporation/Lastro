"""Matriz de acesso (SPEC §6.4). Roda contra o Postgres real do Compose, conectado como lastro_app.

Requer os seeds de demo (make seed).
"""

import os
import re

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.db import sessao
from app.main import app

client = TestClient(app)

ROTAS_PUBLICAS = {"/health", "/auth/login"}
GIL_ID = "00000000-0000-0000-0000-0000000000a3"


def conectar() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5)


def token(email: str) -> str:
    r = client.post("/auth/login", json={"email": email, "senha": "demo123"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def negacoes_do_gil(ctx_auditor) -> int:
    sql = "select count(*) from auditoria where usuario_id = %s and evento = 'negado'"
    with sessao(ctx_auditor) as conn:
        return conn.execute(sql, (GIL_ID,)).fetchone()[0]


def test_caso_5_gestor_nao_consulta_e_a_negacao_vai_para_a_auditoria(ctx_caio):
    antes = negacoes_do_gil(ctx_caio)

    r = client.post(
        "/consultas",
        json={"pergunta": "Quanto o fornecedor recebeu?"},
        headers={"Authorization": f"Bearer {token('gil@alfa.demo')}"},
    )

    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "PERFIL_SEM_PERMISSAO"
    assert negacoes_do_gil(ctx_caio) == antes + 1
    with sessao(ctx_caio) as conn:
        detalhes = conn.execute(
            "select detalhes from auditoria where usuario_id = %s order by seq desc limit 1", (GIL_ID,)
        ).fetchone()[0]
    assert detalhes == {"motivo": "perfil_sem_permissao", "acao": "consultar", "perfil": "gestor"}


def test_caso_5_analista_passa_pela_permissao():
    r = client.post(
        "/consultas",
        json={"pergunta": "Quanto o fornecedor recebeu?"},
        headers={"Authorization": f"Bearer {token('ana@alfa.demo')}"},
    )
    assert r.status_code != 403


def _rotas_protegidas() -> list[tuple[str, str]]:
    """Todas as rotas da API (lidas do OpenAPI, então rota nova entra no teste sozinha), menos as públicas."""
    rotas = []
    for caminho, operacoes in app.openapi()["paths"].items():
        if caminho in ROTAS_PUBLICAS:
            continue
        concreto = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", caminho)
        rotas += [(metodo.upper(), concreto) for metodo in sorted(operacoes)]
    return rotas


def test_caso_6_existem_rotas_protegidas():
    assert ("POST", "/consultas") in _rotas_protegidas()
    assert ("GET", "/me") in _rotas_protegidas()


@pytest.mark.parametrize(("metodo", "caminho"), _rotas_protegidas())
def test_caso_6_sem_token_401_em_tudo(metodo, caminho):
    r = client.request(metodo, caminho, json={})
    assert r.status_code == 401
    assert r.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


@pytest.mark.parametrize("caminho", sorted(ROTAS_PUBLICAS))
def test_caso_6_rotas_publicas_nao_pedem_token(caminho):
    metodo = "POST" if caminho == "/auth/login" else "GET"
    r = client.request(metodo, caminho, json={"email": "ana@alfa.demo", "senha": "demo123"})
    assert r.status_code == 200


def test_caso_7_sem_contexto_nada_e_visivel():
    """Conexão como lastro_app sem set_config: select count(*) from contratos retorna 0."""
    with conectar() as conn:
        assert conn.execute("select current_user").fetchone() == ("lastro_app",)
        assert conn.execute("select count(*) from contratos").fetchone() == (0,)
