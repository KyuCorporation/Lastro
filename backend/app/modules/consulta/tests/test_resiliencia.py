"""SPEC §14.5: reinício no meio da consulta. Banco e API caem e voltam sem deixar consulta pela metade.

LLM fora do ar está em test_consulta_api.py (seção "LLM fora do ar"); fonte fora em pipeline/tests.
"""

from uuid import uuid4

from app.modules.catalogo.tests.conftest import _superusuario

VIGENTES = "Contratos vigentes do CNPJ 11.222.333/0001-81"

DERRUBAR_CONEXOES_DA_API = """
select count(pg_terminate_backend(pid)) from pg_stat_activity
 where usename = 'lastro_app' and pid <> pg_backend_pid()
"""


def _perguntar(api, autenticar, pergunta: str = VIGENTES):
    return api.post("/consultas", json={"pergunta": pergunta}, headers=autenticar("ana@alfa.demo"))


def _status_das_consultas(ctx, pergunta: str) -> list[str]:
    from app.core.db import sessao

    with sessao(ctx) as conn:
        return [r[0] for r in conn.execute("select status from consultas where pergunta = %s", (pergunta,))]


def test_banco_reiniciado_nao_derruba_a_proxima_consulta(api, autenticar):
    """Reinício do Postgres mata as conexões ociosas do pool. A próxima pergunta usa uma conexão nova."""
    cabecalho = autenticar("ana@alfa.demo")
    assert api.post("/consultas", json={"pergunta": VIGENTES}, headers=cabecalho).status_code == 200

    with _superusuario() as su:
        derrubadas = su.execute(DERRUBAR_CONEXOES_DA_API).fetchone()[0]
    assert derrubadas >= 1

    r = api.post("/consultas", json={"pergunta": VIGENTES}, headers=cabecalho)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "respondida"


def test_conexao_que_cai_no_meio_da_gravacao_nao_deixa_resposta_sem_recibo(
    api, autenticar, monkeypatch, ctx_ana
):
    """A API (ou o banco) cai entre gravar a consulta e o recibo: a transação some inteira, a resposta é 503
    e a pergunta seguinte funciona."""
    from app.modules.recibos import service as recibos

    def cai_no_meio(conn, *_a, **_k):
        conn.execute("select pg_terminate_backend(pg_backend_pid())")

    monkeypatch.setattr(recibos, "gravar", cai_no_meio)
    pergunta = f"{VIGENTES} [{uuid4().hex[:8]}]"
    r = _perguntar(api, autenticar, pergunta)
    assert r.status_code == 503 and r.json()["erro"]["codigo"] == "FONTE_INDISPONIVEL"
    assert "respondida" not in _status_das_consultas(ctx_ana, pergunta)

    monkeypatch.undo()
    depois = _perguntar(api, autenticar)
    assert depois.status_code == 200 and depois.json()["recibo_id"]
