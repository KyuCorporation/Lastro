"""O arquivo de ataques é válido e cobre o que o SPEC §14.2 pede."""

from collections import Counter

import pytest
from pydantic import ValidationError

from lastro_eval.casos import Caso, carregar, ler_checagem
from tests.conftest import EVAL

CASOS = carregar(EVAL / "ataques" / "ataques.yaml")


def test_pelo_menos_50_casos_com_ids_unicos():
    assert len(CASOS) >= 50
    assert len({c.id for c in CASOS}) == len(CASOS)


def test_cobre_as_categorias_do_spec():
    exigidas = {
        "direta",
        "armazenada",
        "outra_uf",
        "outro_tenant",
        "idor",
        "vazar_prompt",
        "sql_param",
        "entrada_invalida",
        "abuso",
    }
    assert exigidas <= set(Counter(c.categoria for c in CASOS))


def test_injecao_armazenada_usa_o_fornecedor_envenenado_do_seed():
    armazenadas = [c for c in CASOS if c.categoria == "armazenada"]
    assert len(armazenadas) >= 5
    assert all(
        "99999999000191" in (c.pergunta or "").replace(".", "").replace("/", "").replace("-", "")
        or "{cnpj_envenenado}" in (c.requisicao or "")
        for c in armazenadas
    )


def test_virgula_dentro_de_aspas_nao_quebra_a_checagem():
    a002 = next(c for c in CASOS if c.id == "A002")
    assert ("sem_texto", "999.999.999,99") in a002.checagens


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ('sem_texto:"R$ 1,00"', ("sem_texto", "R$ 1,00")),
        ("sem_uf:AL", ("sem_uf", "AL")),
        ("recibo_integro", ("recibo_integro", None)),
        ('status_em:"abstencao,esclarecimento"', ("status_em", "abstencao,esclarecimento")),
    ],
)
def test_ler_checagem(texto, esperado):
    assert ler_checagem(texto) == esperado


@pytest.mark.parametrize(
    "dados",
    [
        {"id": "A900", "categoria": "direta", "usuario": "a@b", "esperado": "negar"},  # sem pergunta
        {
            "id": "A900",
            "categoria": "direta",
            "usuario": "a@b",
            "pergunta": "x",
            "requisicao": "GET /x",
            "esperado": "negar",
        },
        {
            "id": "A900",
            "categoria": "direta",
            "pergunta": "x",
            "esperado": "negar",
        },  # token válido sem usuário
        {
            "id": "A900",
            "categoria": "direta",
            "usuario": "a@b",
            "pergunta": "x",
            "esperado": "negar",
            "verificar": ["checagem_inventada"],
        },
        {
            "id": "A900",
            "categoria": "direta",
            "usuario": "a@b",
            "pergunta": "x",
            "esperado": "negar",
            "rajada": 5,
        },
        {
            "id": "A900",
            "categoria": "direta",
            "usuario": "a@b",
            "requisicao": "DELETE /x",
            "esperado": "negar",
        },
        {"id": "X1", "categoria": "direta", "usuario": "a@b", "pergunta": "x", "esperado": "negar"},
    ],
)
def test_caso_mal_formado_e_recusado(dados):
    with pytest.raises(ValidationError):
        Caso(**dados)


def test_preencher_ate_gera_o_tamanho_pedido():
    caso = Caso(
        id="A900", categoria="abuso", usuario="a@b", pergunta="abc", preencher_ate=501, esperado="bloquear"
    )
    assert len(caso.pergunta_final()) == 501
