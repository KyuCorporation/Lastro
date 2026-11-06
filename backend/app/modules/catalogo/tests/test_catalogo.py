"""Intents N1 do catálogo contra dados sintéticos, sob RLS (conectado como lastro_app, com contexto)."""

from datetime import date
from decimal import Decimal

import pytest
from psycopg.rows import dict_row

from app.core.cnpj import cnpj_valido
from app.core.db import sessao
from app.core.errors import ErroApi
from app.llm.plano import Parametros, PlanoConsulta
from app.modules.catalogo.executor import IntentSemConsulta, executar
from app.modules.catalogo.intents import INTENTS
from app.modules.catalogo.registry import CONSULTAS, PROVENIENCIA, sql
from app.modules.catalogo.tests.conftest import F1, F2, HOJE

pytestmark = pytest.mark.usefixtures("dados_catalogo")

N1_COM_SQL = {
    "resumo_fornecedor",
    "contratos_vigentes",
    "contratos_vencendo",
    "pagamentos_periodo",
    "sancoes_fornecedor",
}


def plano(intent: str, **parametros) -> PlanoConsulta:
    return PlanoConsulta(intent=intent, parametros=Parametros(cnpj=F1, **parametros))


def origens(linhas) -> set[str]:
    return {linha["id_origem"] for linha in linhas}


def assert_proveniencia(resultado) -> None:
    for nome in CONSULTAS[resultado.intent].citaveis:
        for linha in resultado.conjuntos[nome]:
            for coluna in PROVENIENCIA:
                assert coluna in linha, f"{nome} sem {coluna}"
            for coluna in ("id", "fonte_id", "id_origem", "url_origem", "coletado_em", "hash_conteudo"):
                assert linha[coluna] is not None, f"{nome}.{coluna} nulo"


def test_cnpjs_sinteticos_sao_validos():
    assert cnpj_valido(F1) and cnpj_valido(F2)
    assert not cnpj_valido("11222333000180")
    assert not cnpj_valido("11111111111111")


def test_registro_cobre_as_intents_n1_e_os_arquivos_existem():
    assert set(CONSULTAS) == N1_COM_SQL
    assert set(CONSULTAS) <= set(INTENTS)
    for consulta in CONSULTAS.values():
        for conjunto in consulta.conjuntos:
            assert sql(consulta.intent, conjunto).strip()


# ---------------------------------------------------------------- resumo_fornecedor
def test_resumo_so_com_as_ufs_da_ana(ctx_ana):
    r = executar(plano("resumo_fornecedor"), ctx_ana, HOJE)
    assert r.versao == "resumo_fornecedor@v1"
    assert r.parametros["ufs"] == ["PE"]
    assert origens(r.conjuntos["contratos"]) == {"TCAT-C1", "TCAT-C2", "TCAT-C3"}
    assert origens(r.conjuntos["pagamentos"]) == {"TCAT-P1", "TCAT-P2", "TCAT-P3"}
    assert {g["uf"] for g in r.conjuntos["por_uf_orgao"]} == {"PE"}
    assert r.totais == {
        "n_contratos": 3,
        "n_pagamentos": 3,
        "valor_contratado": Decimal("450000.00"),
        "valor_vigente": Decimal("400000.00"),
        "valor_pago": Decimal("55000.00"),
    }
    assert_proveniencia(r)


def test_resumo_por_orgao(ctx_ana):
    r = executar(plano("resumo_fornecedor"), ctx_ana, HOJE)
    por_orgao = {g["orgao_id"]: g for g in r.conjuntos["por_uf_orgao"]}
    pe1 = por_orgao["demo_sintetico:TCAT-PE1"]
    assert (pe1["n_contratos"], pe1["valor_contratado"], pe1["valor_pago"]) == (
        2,
        Decimal("150000.00"),
        Decimal("45000.00"),
    )
    assert pe1["orgao_nome"] == "Secretaria Teste PE 1"


def test_resumo_da_bia_so_ve_alagoas(ctx_bia):
    r = executar(plano("resumo_fornecedor"), ctx_bia, HOJE)
    assert origens(r.conjuntos["contratos"]) == {"TCAT-C4"}
    assert origens(r.conjuntos["pagamentos"]) == {"TCAT-P4"}


def test_uf_fora_do_escopo_e_negada_sem_consultar(ctx_ana):
    with pytest.raises(ErroApi) as erro:
        executar(plano("resumo_fornecedor", uf="AL"), ctx_ana, HOJE)
    assert (erro.value.status, erro.value.codigo) == (403, "ESCOPO_NEGADO")
    assert "AL" in erro.value.mensagem


def test_uf_pedida_dentro_do_escopo_restringe(ctx_admin):
    r = executar(plano("resumo_fornecedor", uf="AL"), ctx_admin, HOJE)
    assert r.parametros["ufs"] == ["AL"]
    assert origens(r.conjuntos["contratos"]) == {"TCAT-C4"}


def test_rls_filtra_mesmo_se_o_parametro_pedir_outra_uf(ctx_ana):
    """Defesa em profundidade: se o executor errasse a interseção, o banco ainda não entrega AL."""
    with sessao(ctx_ana) as conn:
        linhas = (
            conn.cursor(row_factory=dict_row)
            .execute(sql("resumo_fornecedor", "contratos"), {"cnpj": F1, "ufs": ["PE", "AL"], "limite": 201})
            .fetchall()
        )
    assert {linha["uf"] for linha in linhas} == {"PE"}


# ---------------------------------------------------------------- contratos_vigentes
def test_contratos_vigentes(ctx_ana):
    r = executar(plano("contratos_vigentes"), ctx_ana, HOJE)
    assert origens(r.conjuntos["linhas"]) == {"TCAT-C1", "TCAT-C2"}
    assert r.totais == {"n_contratos": 2, "valor_total": Decimal("400000.00")}
    assert_proveniencia(r)


# ---------------------------------------------------------------- contratos_vencendo
def test_contratos_vencendo_com_percentual_do_vigente(ctx_ana):
    r = executar(plano("contratos_vencendo", dias=180), ctx_ana, HOJE)
    assert origens(r.conjuntos["linhas"]) == {"TCAT-C1"}
    assert r.totais == {
        "n_contratos": 1,
        "valor_vencendo": Decimal("100000.00"),
        "valor_vigente_total": Decimal("400000.00"),
        "percentual_do_vigente": Decimal("25.00"),
    }
    assert_proveniencia(r)


def test_contratos_vencendo_usa_180_dias_por_padrao(ctx_ana):
    r = executar(plano("contratos_vencendo"), ctx_ana, HOJE)
    assert r.parametros["dias"] == 180


def test_contratos_vencendo_prazo_curto(ctx_ana):
    r = executar(plano("contratos_vencendo", dias=30), ctx_ana, HOJE)
    assert r.conjuntos["linhas"] == []
    assert r.totais["n_contratos"] == 0


# ---------------------------------------------------------------- pagamentos_periodo
def test_pagamentos_no_periodo(ctx_ana):
    r = executar(
        plano("pagamentos_periodo", data_inicio=date(2025, 1, 1), data_fim=date(2025, 12, 31)), ctx_ana, HOJE
    )
    assert origens(r.conjuntos["linhas"]) == {"TCAT-P1", "TCAT-P2"}
    assert r.totais == {"n_pagamentos": 2, "valor_total": Decimal("50000.00")}
    assert_proveniencia(r)


# ---------------------------------------------------------------- sancoes_fornecedor
def test_sancoes_vigentes_e_passadas(ctx_ana):
    r = executar(plano("sancoes_fornecedor"), ctx_ana, HOJE)
    vigente = {s["id_origem"]: s["vigente"] for s in r.conjuntos["linhas"]}
    assert vigente == {"TCAT-S1": True, "TCAT-S2": False}
    assert r.totais == {"n_sancoes": 2, "n_vigentes": 1}
    assert "ufs" not in r.parametros
    assert_proveniencia(r)


def test_sancao_e_nacional_e_aparece_para_qualquer_uf(ctx_bia):
    r = executar(plano("sancoes_fornecedor"), ctx_bia, HOJE)
    assert r.totais["n_sancoes"] == 2


def test_fornecedor_sem_registros(ctx_ana):
    r = executar(PlanoConsulta(intent="sancoes_fornecedor", parametros=Parametros(cnpj=F2)), ctx_ana, HOJE)
    assert r.conjuntos["linhas"] == [] and r.totais == {"n_sancoes": 0, "n_vigentes": 0}


# ---------------------------------------------------------------- validações
def test_cnpj_com_digito_verificador_errado(ctx_ana):
    with pytest.raises(ErroApi) as erro:
        executar(
            PlanoConsulta(intent="sancoes_fornecedor", parametros=Parametros(cnpj="11222333000180")),
            ctx_ana,
            HOJE,
        )
    assert erro.value.codigo == "ENTRADA_INVALIDA"


@pytest.mark.parametrize("intent", ["fora_de_escopo", "esclarecer"])
def test_intents_sem_consulta(intent, ctx_ana):
    with pytest.raises(IntentSemConsulta):
        executar(PlanoConsulta(intent=intent), ctx_ana, HOJE)


def test_intent_n2_ainda_sem_sql(ctx_ana):
    with pytest.raises(IntentSemConsulta):
        executar(PlanoConsulta(intent="orgaos_fornecedor", parametros=Parametros(cnpj=F1)), ctx_ana, HOJE)
