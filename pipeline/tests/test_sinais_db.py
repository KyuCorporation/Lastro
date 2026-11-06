"""T17 contra o Postgres real: recálculo idempotente como `lastro_ingest` e sinal por UF sob a RLS da API.

Tudo roda numa transação desfeita no fim. Os fornecedores são sintéticos (prefixo 7700) e só eles são
conferidos, então dados de ingestão já presentes no banco não atrapalham.
"""

import os
from collections.abc import Iterator
from datetime import date, timedelta

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from lastro_pipeline.sinais import calculo

HOJE = date(2026, 11, 6)
F_PE = "77000000000101"  # penhasco e concentração em PE, sanção vigente
F_AL = "77000000000202"  # penhasco só em AL
F_EMP = "77000000000303"  # em PE só tem empenho de um órgão: não é recebimento, não concentra
CNPJS = (F_PE, F_AL, F_EMP)


def d(dias: int) -> date:
    return HOJE + timedelta(days=dias)


FORNECEDORES = "insert into fornecedores (cnpj, razao_social, uf_sede) values (%s, %s, 'PE')"
ORGAO = "insert into orgaos (id, nome, uf, esfera) values (%s, %s, %s, 'estadual')"
CONTRATO = """
insert into contratos (fonte_id, id_origem, uf, orgao_id, fornecedor_cnpj, objeto, valor_global,
                       data_assinatura, vigencia_fim, url_origem, coletado_em, hash_conteudo)
values ('demo_sintetico', %s, %s, %s, %s, 'teste de sinais', %s, %s, %s, 'about:blank#t17', now(), repeat('a', 64))
"""
PAGAMENTO = """
insert into pagamentos (fonte_id, id_origem, uf, orgao_id, fornecedor_cnpj, data_pagamento, valor,
                        descricao, url_origem, coletado_em, hash_conteudo)
values ('demo_sintetico', %s, %s, %s, %s, %s, %s, 'teste', 'about:blank#t17', now(), repeat('b', 64))
"""
SANCAO = """
insert into sancoes (fonte_id, id_origem, cnpj, tipo, data_inicio, data_fim, url_origem, coletado_em, hash_conteudo)
values ('ceis', %s, %s, 'Impedimento', %s, %s, 'about:blank#t17', now(), repeat('c', 64))
"""


def _semear(conn: psycopg.Connection) -> None:
    for cnpj in CNPJS:
        conn.execute(FORNECEDORES, (cnpj, f"FORNECEDOR SINTETICO {cnpj}"))
    for org, uf in (("T17-PE1", "PE"), ("T17-PE2", "PE"), ("T17-AL1", "AL")):
        conn.execute(ORGAO, (f"demo_sintetico:{org}", f"Órgão {org}", uf))
    pe1, pe2, al1 = "demo_sintetico:T17-PE1", "demo_sintetico:T17-PE2", "demo_sintetico:T17-AL1"
    # F_PE em PE: 300 de 400 vigentes vencem em 60 dias (75%) → penhasco
    conn.execute(CONTRATO, ("T17-C1", "PE", pe1, F_PE, "300.00", d(-100), d(60)))
    conn.execute(CONTRATO, ("T17-C2", "PE", pe2, F_PE, "100.00", d(-100), d(400)))
    # F_PE em PE: 80% do pago vem de pe1 → concentração (o empenho grande de pe2 não conta)
    conn.execute(PAGAMENTO, ("liq:T17-P1", "PE", pe1, F_PE, d(-30), "80.00"))
    conn.execute(PAGAMENTO, ("liq:T17-P2", "PE", pe2, F_PE, d(-30), "20.00"))
    conn.execute(PAGAMENTO, ("emp:T17-P3", "PE", pe2, F_PE, d(-30), "100000.00"))
    conn.execute(SANCAO, ("T17-S1", F_PE, d(-10), d(100)))
    conn.execute(SANCAO, ("T17-S2", F_AL, d(-400), d(-1)))  # vencida: sem sinal
    # F_AL: só em AL, tudo vence em 30 dias → penhasco e concentração (por contratos) em AL
    conn.execute(CONTRATO, ("T17-C3", "AL", al1, F_AL, "500.00", d(-20), d(30)))
    # F_EMP: só empenho → nada
    conn.execute(PAGAMENTO, ("emp:T17-P4", "PE", pe1, F_EMP, d(-30), "999.00"))


def _sinais(conn: psycopg.Connection) -> dict[tuple[str, str | None, str], tuple]:
    linhas = conn.execute(
        "select fornecedor_cnpj, uf, tipo, id, gravidade, valor, versao_regra, evidencias "
        "from sinais where fornecedor_cnpj = any(%s)",
        (list(CNPJS),),
    ).fetchall()
    return {(c, uf, t): resto for c, uf, t, *resto in linhas}


@pytest.fixture
def semeado(conn) -> psycopg.Connection:
    _semear(conn)
    return conn


def test_calcula_os_tres_sinais_por_uf(semeado):
    resumo = calculo.recalcular(semeado, HOJE)
    sinais = _sinais(semeado)

    assert set(sinais) == {
        (F_PE, None, "sancao_direta"),
        (F_PE, "PE", "penhasco"),
        (F_PE, "PE", "concentracao"),
        (F_AL, "AL", "penhasco"),
        (F_AL, "AL", "concentracao"),
    }
    assert sinais[(F_PE, None, "sancao_direta")][1] == "forte"
    assert sinais[(F_PE, "PE", "penhasco")][2] == 75
    assert sinais[(F_PE, "PE", "concentracao")][2] == 80  # empenho de 100 mil fora da conta
    assert all(s[3] == "v1" for s in sinais.values())
    assert resumo.novos >= 5


def test_evidencias_apontam_para_linhas_que_existem(semeado):
    calculo.recalcular(semeado, HOJE)
    tabelas = {"contratos", "pagamentos", "sancoes"}
    for *_, evidencias in _sinais(semeado).values():
        for e in evidencias:
            assert e["tabela"] in tabelas
            sql = {
                "contratos": "select url_origem from contratos where id = %s",
                "pagamentos": "select url_origem from pagamentos where id = %s",
                "sancoes": "select url_origem from sancoes where id = %s",
            }[e["tabela"]]
            assert semeado.execute(sql, (e["id"],)).fetchone() == (e["url_origem"],)


def test_recalcular_de_novo_mantem_os_mesmos_ids(semeado):
    calculo.recalcular(semeado, HOJE)
    antes = {k: v[0] for k, v in _sinais(semeado).items()}
    segunda = calculo.recalcular(semeado, HOJE)
    depois = {k: v[0] for k, v in _sinais(semeado).items()}
    assert depois == antes
    assert segunda.novos == 0 and segunda.apagados == 0


def test_sinal_que_deixou_de_valer_e_apagado(semeado):
    calculo.recalcular(semeado, HOJE)
    # 200 dias depois: a sanção de F_PE venceu, os contratos de 60 e 30 dias acabaram
    calculo.recalcular(semeado, d(200))
    restantes = set(_sinais(semeado))
    assert (F_PE, None, "sancao_direta") not in restantes
    assert (F_AL, "AL", "penhasco") not in restantes


# ===================== critério de aceite: sinal de AL invisível para ana =====================
def _superusuario() -> psycopg.Connection:
    url, usuario, senha = (os.environ.get(k) for k in ("DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD"))
    if not (url and usuario and senha):
        pytest.skip("sem credenciais do banco: rodar com `make test-pipeline` (Compose)")
    base = conninfo_to_dict(url)
    base.update(user=usuario, password=senha)
    return psycopg.connect(make_conninfo(**base), autocommit=True)


CONTEXTO = """
select set_config('app.tenant_id', %s, true), set_config('app.usuario_id', %s, true),
       set_config('app.perfil', %s, true), set_config('app.ufs', %s, true)
"""
ANA = ("00000000-0000-0000-0000-00000000a1fa", "00000000-0000-0000-0000-0000000000a1", "analista", "PE")
BIA = ("00000000-0000-0000-0000-00000000be7a", "00000000-0000-0000-0000-0000000000b1", "analista", "AL")


@pytest.fixture
def como_superusuario() -> Iterator[psycopg.Connection]:
    """Uma transação desfeita no fim; dentro dela o teste troca de papel com `set local role`."""
    with _superusuario() as su, su.transaction(force_rollback=True):
        yield su


def _visiveis(conn: psycopg.Connection, ctx: tuple[str, str, str, str]) -> set[tuple[str, str | None, str]]:
    conn.execute("set local role lastro_app")
    conn.execute(CONTEXTO, ctx)
    vistos = conn.execute(
        "select fornecedor_cnpj, uf, tipo from sinais where fornecedor_cnpj = any(%s)", (list(CNPJS),)
    ).fetchall()
    conn.execute("reset role")
    return set(vistos)


def test_sinal_de_al_invisivel_para_ana(como_superusuario):
    conn = como_superusuario
    conn.execute("set local role lastro_ingest")
    _semear(conn)
    calculo.recalcular(conn, HOJE)
    conn.execute("reset role")

    ana = _visiveis(conn, ANA)
    bia = _visiveis(conn, BIA)
    assert ana == {(F_PE, None, "sancao_direta"), (F_PE, "PE", "penhasco"), (F_PE, "PE", "concentracao")}
    assert all(uf != "AL" for _, uf, _ in ana)
    assert bia == {(F_PE, None, "sancao_direta"), (F_AL, "AL", "penhasco"), (F_AL, "AL", "concentracao")}


def test_recalculo_fica_na_trilha_global_de_auditoria(como_superusuario):
    """A pipeline grava o evento sem poder ler a auditoria; a leitura aqui é como superusuário."""
    conn = como_superusuario
    conn.execute("set local role lastro_ingest")
    _semear(conn)
    calculo.recalcular(conn, HOJE)
    conn.execute("reset role")
    evento, detalhes, tenant = conn.execute(
        "select evento, detalhes, tenant_id from auditoria where evento = 'sinais_recalculados' "
        "order by seq desc limit 1"
    ).fetchone()
    assert evento == "sinais_recalculados" and tenant is None
    assert detalhes["versao_regra"] == "v1" and detalhes["hoje"] == HOJE.isoformat()
