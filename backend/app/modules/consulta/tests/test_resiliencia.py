"""SPEC §14.5: reinício no meio da consulta. Banco e API caem e voltam sem deixar consulta pela metade.

LLM fora do ar está em test_consulta_api.py (seção "LLM fora do ar"); fonte fora em pipeline/tests.
"""

import json
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


# ------------------------------------------------------------------ teto de tempo total da consulta
PLANO_VIGENTES = {"versao": "v1", "intent": "contratos_vigentes", "parametros": {"cnpj": "11222333000181"}}


class ProvedorLento:
    """LLM que responde certo, mas cada chamada custa `custo_s` no relógio da consulta (sem esperar de verdade)."""

    nome, modelo = "lento", "lento-1"

    def __init__(self, relogio: list[float], custo_s: float, plano: str | None = None) -> None:
        self.relogio, self.custo_s = relogio, custo_s
        self.plano = plano if plano is not None else json.dumps(PLANO_VIGENTES)
        self.timeouts: list[float] = []

    def gerar(self, prompt, *, json=False, timeout_s, temperatura=0.0) -> str:
        self.timeouts.append(timeout_s)
        self.relogio[0] += self.custo_s
        return self.plano if json else "O fornecedor {{v1}} tem {{v2}} contratos vigentes, somando {{v3}}."


def _recibo(api, cabecalho, corpo) -> dict:
    return api.get(f"/recibos/{corpo['recibo_id']}", headers=cabecalho).json()["conteudo"]


def test_planejador_lento_gasta_o_orcamento_e_o_texto_vem_do_modelo_padrao(api, autenticar, com_ambiente):
    """O plano chegou, mas não sobra tempo para o redator: a resposta sai com o texto padrão, sem outra espera."""
    relogio = [0.0]
    provedor = ProvedorLento(relogio, custo_s=11.0)
    com_ambiente(provedor=provedor, orcamento_s=12.0, relogio=lambda: relogio[0])
    cabecalho = autenticar("ana@alfa.demo")

    r = _perguntar(api, autenticar)
    assert r.status_code == 200 and r.json()["status"] == "respondida"
    assert len(provedor.timeouts) == 1  # só o planejador chamou a LLM
    recibo = _recibo(api, cabecalho, r.json())
    assert recibo["verificacao"] == {"status": "fallback", "motivos": ["tempo_esgotado"]}
    assert recibo["ia"]["planejador_por_regras"] is False


def test_sem_tempo_para_a_segunda_tentativa_o_plano_vem_das_regras(api, autenticar, com_ambiente):
    relogio = [0.0]
    provedor = ProvedorLento(relogio, custo_s=11.0, plano="isto não é um plano")
    com_ambiente(provedor=provedor, orcamento_s=12.0, relogio=lambda: relogio[0])
    cabecalho = autenticar("ana@alfa.demo")

    r = _perguntar(api, autenticar)
    assert r.status_code == 200 and r.json()["status"] == "respondida"
    assert len(provedor.timeouts) == 1  # a segunda tentativa do planejador não cabia no orçamento
    assert _recibo(api, cabecalho, r.json())["ia"]["planejador_por_regras"] is True


def test_cada_chamada_a_llm_recebe_no_maximo_o_tempo_que_resta(api, autenticar, com_ambiente):
    relogio = [0.0]
    provedor = ProvedorLento(relogio, custo_s=3.0)
    com_ambiente(provedor=provedor, timeout_s=20.0, orcamento_s=8.0, relogio=lambda: relogio[0])

    r = _perguntar(api, autenticar)
    assert r.status_code == 200
    assert provedor.timeouts == [8.0, 5.0]  # planejador com o orçamento inteiro; redator com o que sobrou
