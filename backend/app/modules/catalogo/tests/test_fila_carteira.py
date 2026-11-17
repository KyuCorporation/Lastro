"""I5: `fila_carteira` sob RLS (lastro_app com contexto), com a carteira TCAT (F1 e F2) do tenant alfa.

Os sinais da T18 podem estar no banco quando este módulo roda (fixture de sessão dos testes de carteiras), então
aqui não se conta sinal: a ordem e o texto com sinais são testados em `carteiras/tests/test_fila_na_consulta.py`.
"""

from decimal import Decimal

import pytest

from app.llm.plano import Parametros, PlanoConsulta
from app.modules.catalogo.executor import executar
from app.modules.catalogo.registry import PROVENIENCIA
from app.modules.catalogo.tests.conftest import F1, F2, HOJE

pytestmark = pytest.mark.usefixtures("dados_catalogo")


def plano(carteira_id) -> PlanoConsulta:
    return PlanoConsulta(intent="fila_carteira", parametros=Parametros(carteira_id=carteira_id))


def origens(linhas) -> set[str]:
    return {linha["id_origem"] for linha in linhas}


def test_fila_da_ana_so_com_pe(ctx_ana, carteira_tcat):
    r = executar(plano(carteira_tcat), ctx_ana, HOJE)
    assert r.versao == "fila_carteira@v1"
    assert r.parametros["carteira_id"] == carteira_tcat and r.parametros["ufs"] == ["PE"]

    fila = {f["cnpj"]: f for f in r.conjuntos["fila"]}
    assert set(fila) == {F1, F2}
    assert fila[F1]["razao_social"] == "FORNECEDOR TESTE UM LTDA"
    assert fila[F1]["valor_exposto"] == Decimal("400000.00")  # C1 + C2; C3 encerrado; C4 é de AL
    assert fila[F1]["n_contratos_vigentes"] == 2
    assert fila[F2]["valor_exposto"] == 0 and fila[F2]["gravidades"] == []

    assert origens(r.conjuntos["contratos"]) == {"TCAT-C1", "TCAT-C2"}
    assert origens(r.conjuntos["sancoes"]) == {"TCAT-S1"}  # S2 já terminou
    assert r.totais["n_fornecedores"] == 2
    assert r.totais["valor_exposto"] == Decimal("400000.00")
    assert r.totais["n_sancoes_vigentes"] == 1


def test_linhas_citaveis_tem_proveniencia(ctx_ana, carteira_tcat):
    r = executar(plano(carteira_tcat), ctx_ana, HOJE)
    for nome in ("contratos", "sancoes"):
        assert r.conjuntos[nome]
        for linha in r.conjuntos[nome]:
            assert set(PROVENIENCIA) <= set(linha)
            assert linha["fornecedor_cnpj"] == F1


def test_admin_com_pe_e_al_ve_a_exposicao_de_al(ctx_admin, carteira_tcat):
    r = executar(plano(carteira_tcat), ctx_admin, HOJE)
    assert origens(r.conjuntos["contratos"]) == {"TCAT-C1", "TCAT-C2", "TCAT-C4"}
    assert r.totais["valor_exposto"] == Decimal("470000.00")


def test_contrato_rescindido_nao_conta(ctx_ana, carteira_tcat, c2_rescindido):
    r = executar(plano(carteira_tcat), ctx_ana, HOJE)
    assert origens(r.conjuntos["contratos"]) == {"TCAT-C1"}
    assert r.totais["valor_exposto"] == Decimal("100000.00")


def test_carteira_de_outro_tenant_nao_devolve_nada(ctx_bia, carteira_tcat):
    """Mesmo com o id certo no plano, a RLS de carteira_itens esconde a carteira do tenant alfa."""
    r = executar(plano(carteira_tcat), ctx_bia, HOJE)
    assert r.conjuntos == {"fila": [], "contratos": [], "sancoes": []}
    assert r.totais["n_fornecedores"] == 0
