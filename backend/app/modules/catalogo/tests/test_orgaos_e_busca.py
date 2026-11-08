"""T19: `orgaos_fornecedor` e `busca_objeto` contra dados sintéticos, sob RLS (lastro_app com contexto)."""

from decimal import Decimal

import pytest

from app.core.db import sessao
from app.llm.plano import Parametros, PlanoConsulta
from app.modules.catalogo.executor import executar
from app.modules.catalogo.registry import CONSULTAS, PROVENIENCIA, sql
from app.modules.catalogo.tests.conftest import F1, F2, HOJE

pytestmark = pytest.mark.usefixtures("dados_catalogo")


def orgaos(cnpj: str = F1, **parametros) -> PlanoConsulta:
    return PlanoConsulta(intent="orgaos_fornecedor", parametros=Parametros(cnpj=cnpj, **parametros))


def busca(termo: str, **parametros) -> PlanoConsulta:
    return PlanoConsulta(intent="busca_objeto", parametros=Parametros(termo=termo, **parametros))


def origens(linhas) -> set[str]:
    return {linha["id_origem"] for linha in linhas}


def assert_proveniencia(resultado) -> None:
    for nome in CONSULTAS[resultado.intent].citaveis:
        assert resultado.conjuntos[nome], f"{nome} sem linhas"
        for linha in resultado.conjuntos[nome]:
            for coluna in PROVENIENCIA:
                assert coluna in linha, f"{nome} sem {coluna}"


# ------------------------------------------------------------------ orgaos_fornecedor
def test_ranking_de_orgaos_com_participacao(ctx_ana):
    r = executar(orgaos(), ctx_ana, HOJE)
    assert r.versao == "orgaos_fornecedor@v1"
    ranking = r.conjuntos["ranking"]
    assert [g["orgao_id"] for g in ranking] == ["demo_sintetico:TCAT-PE2", "demo_sintetico:TCAT-PE1"]
    assert [g["valor_contratado"] for g in ranking] == [Decimal("300000.00"), Decimal("150000.00")]
    assert [g["participacao"] for g in ranking] == [Decimal("66.67"), Decimal("33.33")]
    assert ranking[0]["orgao_nome"] == "Prefeitura Teste PE 2"
    assert r.totais == {
        "n_orgaos": 2,
        "n_contratos": 3,
        "valor_total": Decimal("450000.00"),
        "maior_orgao": "Prefeitura Teste PE 2",
        "maior_participacao": Decimal("66.67"),
    }
    assert origens(r.conjuntos["contratos"]) == {"TCAT-C1", "TCAT-C2", "TCAT-C3"}
    assert_proveniencia(r)


def test_orgaos_so_nas_ufs_do_escopo(ctx_bia, ctx_admin):
    bia = executar(orgaos(), ctx_bia, HOJE)
    assert [g["orgao_id"] for g in bia.conjuntos["ranking"]] == ["demo_sintetico:TCAT-AL1"]
    assert bia.totais["maior_participacao"] == Decimal("100.00")
    admin_al = executar(orgaos(uf="AL"), ctx_admin, HOJE)
    assert origens(admin_al.conjuntos["contratos"]) == {"TCAT-C4"}


def test_orgaos_de_fornecedor_sem_contratos(ctx_ana):
    r = executar(orgaos(F2), ctx_ana, HOJE)
    assert r.conjuntos["ranking"] == [] and r.conjuntos["contratos"] == []
    assert r.totais["n_orgaos"] == 0 and r.totais["maior_orgao"] is None


# ------------------------------------------------------------------ busca_objeto
def test_busca_full_text_em_portugues(ctx_ana):
    r = executar(busca("limpeza tcat"), ctx_ana, HOJE)
    assert r.versao == "busca_objeto@v1"
    assert origens(r.conjuntos["linhas"]) == {"TCAT-C1", "TCAT-C3"}  # C4 é de AL
    assert r.totais == {"n_contratos": 2, "valor_total": Decimal("150000.00")}
    assert r.parametros["termo"] == "limpeza tcat" and "cnpj" not in r.parametros
    assert {linha["fornecedor_cnpj"] for linha in r.conjuntos["linhas"]} == {F1}
    assert_proveniencia(r)


def test_busca_usa_radical_do_portugues(ctx_ana):
    # "escolas" e "escolar" têm o mesmo radical no dicionário portuguese do Postgres.
    assert origens(executar(busca("escola tcat"), ctx_ana, HOJE).conjuntos["linhas"]) == {
        "TCAT-C1",
        "TCAT-C2",
    }


def test_busca_respeita_o_escopo(ctx_bia, ctx_admin):
    assert origens(executar(busca("limpeza tcat"), ctx_bia, HOJE).conjuntos["linhas"]) == {"TCAT-C4"}
    assert origens(executar(busca("limpeza tcat", uf="PE"), ctx_admin, HOJE).conjuntos["linhas"]) == {
        "TCAT-C1",
        "TCAT-C3",
    }


def test_busca_sem_resultado_e_termo_so_de_palavras_vazias(ctx_ana):
    assert executar(busca("helicóptero tcat"), ctx_ana, HOJE).conjuntos["linhas"] == []
    assert executar(busca("de a"), ctx_ana, HOJE).totais["n_contratos"] == 0


def test_busca_com_texto_de_ataque_nao_vira_sql(ctx_ana):
    r = executar(busca("x'; drop table contratos; --"), ctx_ana, HOJE)
    assert r.conjuntos["linhas"] == []
    with sessao(ctx_ana) as conn:
        assert conn.execute("select count(*) from contratos").fetchone()[0] >= 1


def test_busca_limita_a_20_linhas_mas_o_total_e_de_tudo(ctx_ana):
    assert "limit 20" in sql("busca_objeto", "linhas").lower()
