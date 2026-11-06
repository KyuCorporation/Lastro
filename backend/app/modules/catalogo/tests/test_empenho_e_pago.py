"""Empenho não é pagamento (decisão de produto, 06/11/2026): "pago" soma só o que saiu (liquidação e
pagamento); o empenhado aparece à parte. O TCE-PE grava o empenho com id_origem `emp:` e a liquidação com
`liq:` (pipeline/normalize/pe_portal.py), os dois na tabela pagamentos.

Cenário igual ao de Garanhuns nas fixtures: um empenho de R$ 40.000 e duas liquidações de R$ 20.000 dele.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.llm.plano import PlanoConsulta
from app.llm.redator import redigir
from app.modules.catalogo.executor import executar
from app.modules.catalogo.tests.conftest import HOJE, _superusuario

F3 = "11555888000145"  # CNPJ sintético com dígitos verificadores válidos
ORGAO = "demo_sintetico:TEMP-PE1"

PAGAMENTOS = [
    ("emp:TEMP:2025:NE1", date(2025, 4, 5), "40000.00", "empenho: transporte escolar"),
    ("liq:TEMP:2025:NE1:1", date(2025, 4, 30), "20000.00", "liquidação do empenho NE1"),
    ("liq:TEMP:2025:NE1:2", date(2025, 5, 31), "20000.00", "liquidação do empenho NE1"),
]


@pytest.fixture(scope="module")
def empenho_e_liquidacoes(dados_catalogo):
    limpar = [
        "delete from pagamentos where id_origem like '%%:TEMP:%%'",
        "delete from orgaos where id = %(orgao)s",
        "delete from fornecedores where cnpj = %(cnpj)s",
    ]
    with _superusuario() as su:
        for sql in limpar:
            su.execute(sql, {"orgao": ORGAO, "cnpj": F3})
        su.execute(
            "insert into fornecedores (cnpj, razao_social, uf_sede) values (%s, 'TESTE EMPENHO LTDA', 'PE')",
            (F3,),
        )
        su.execute(
            "insert into orgaos (id, nome, uf, esfera) values (%s, 'Prefeitura Teste', 'PE', 'municipal')",
            (ORGAO,),
        )
        for id_origem, data, valor, descricao in PAGAMENTOS:
            su.execute(
                "insert into pagamentos (fonte_id, id_origem, uf, orgao_id, fornecedor_cnpj, data_pagamento, valor, "
                "descricao, url_origem, coletado_em, hash_conteudo) "
                "values ('demo_sintetico', %s, 'PE', %s, %s, %s, %s, %s, 'about:blank#teste', now(), repeat('e', 64))",
                (id_origem, ORGAO, F3, data, valor, descricao),
            )
    yield
    with _superusuario() as su:
        for sql in limpar:
            su.execute(sql, {"orgao": ORGAO, "cnpj": F3})


pytestmark = pytest.mark.usefixtures("empenho_e_liquidacoes")


def _plano(intent: str, **parametros) -> PlanoConsulta:
    return PlanoConsulta(intent=intent, parametros={"cnpj": F3, **parametros})


def test_resumo_separa_pago_de_empenhado(ctx_ana):
    r = executar(_plano("resumo_fornecedor"), ctx_ana, HOJE)
    assert r.versao == "resumo_fornecedor@v2"
    assert r.totais["n_pagamentos"] == 2
    assert r.totais["valor_pago"] == Decimal("40000.00")
    assert r.totais["n_empenhos"] == 1
    assert r.totais["valor_empenhado"] == Decimal("40000.00")
    (grupo,) = r.conjuntos["por_uf_orgao"]
    assert (grupo["valor_pago"], grupo["valor_empenhado"]) == (Decimal("40000.00"), Decimal("40000.00"))
    # As três linhas continuam citáveis: o empenho também é fonte, só não é contado como pago.
    assert len(r.conjuntos["pagamentos"]) == 3


def test_pagamentos_no_periodo_separa_pago_de_empenhado(ctx_ana):
    r = executar(
        _plano("pagamentos_periodo", data_inicio=date(2025, 1, 1), data_fim=date(2025, 12, 31)), ctx_ana, HOJE
    )
    assert r.versao == "pagamentos_periodo@v2"
    assert r.totais == {
        "n_pagamentos": 2,
        "valor_total": Decimal("40000.00"),
        "n_empenhos": 1,
        "valor_empenhado": Decimal("40000.00"),
    }
    assert len(r.conjuntos["linhas"]) == 3


def test_periodo_so_com_empenho_nao_inventa_pagamento(ctx_ana):
    r = executar(
        _plano("pagamentos_periodo", data_inicio=date(2025, 4, 1), data_fim=date(2025, 4, 10)), ctx_ana, HOJE
    )
    assert r.totais == {
        "n_pagamentos": 0,
        "valor_total": Decimal(0),
        "n_empenhos": 1,
        "valor_empenhado": Decimal("40000.00"),
    }


def test_texto_do_resumo_diz_pago_e_empenhado_separados(ctx_ana):
    texto = redigir(
        "p", executar(_plano("resumo_fornecedor"), ctx_ana, HOJE), ufs_autorizadas=("PE",), provedor=None
    ).texto
    assert "Foram registrados 2 pagamento(s), num total de R$ 40.000,00." in texto
    assert "R$ 40.000,00 empenhado(s) em 1 empenho(s)" in texto
    assert "80.000" not in texto


def test_texto_dos_pagamentos_no_periodo(ctx_ana):
    resultado = executar(
        _plano("pagamentos_periodo", data_inicio=date(2025, 1, 1), data_fim=date(2025, 12, 31)), ctx_ana, HOJE
    )
    texto = redigir("p", resultado, ufs_autorizadas=("PE",), provedor=None).texto
    assert "recebeu 2 pagamento(s)" in texto and "num total de R$ 40.000,00" in texto
    assert "R$ 40.000,00 empenhado(s) em 1 empenho(s)" in texto
