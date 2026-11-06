"""Fixtures da T18: cliente da API, dados do catálogo e sinais sintéticos por UF.

Dados (modules/catalogo/tests/conftest.py): F1 tem em PE os contratos C1 (100 mil, vence em 60 dias),
C2 (300 mil, vigente por 400 dias) e C3 (encerrado); em AL, C4 (70 mil, vence em 30 dias); sanção S1 vigente
(CEIS) e S2 passada (CNEP). F2 existe como fornecedor, sem nenhum fato. F3, criado aqui, só tem contrato em AL.
"""

import json
from collections.abc import Iterator

import pytest

from app.core import relogio
from app.main import app
from app.modules.catalogo.tests.conftest import F1, F2, HOJE, _superusuario, d, dados_catalogo  # noqa: F401
from app.modules.consulta.tests.conftest import api, autenticar, com_ambiente  # noqa: F401

F3 = "11333555000171"  # só em AL
VERSAO = "teste-t18"

# (cnpj, uf, tipo, gravidade, explicacao)
SINAIS = [
    (F1, None, "sancao_direta", "forte", "Consta 1 sanção vigente no CEIS."),
    (F1, "PE", "concentracao", "atencao", "80,0% do valor recebido em PE vem de um único órgão."),
    (F1, "AL", "penhasco", "atencao", "100,0% do valor vigente em AL termina em até 180 dias."),
    (F3, "AL", "penhasco", "atencao", "100,0% do valor vigente em AL termina em até 180 dias."),
]


@pytest.fixture(scope="session")
def dados_t18(dados_catalogo) -> Iterator[None]:  # noqa: F811
    limpar = [
        ("delete from sinais where fornecedor_cnpj = any(%s)", ([F1, F2, F3],)),
        ("delete from contratos where id_origem = 'T18-C1'", ()),
        ("delete from fornecedores where cnpj = %s", (F3,)),
        ("delete from orgaos where id = 'demo_sintetico:T18-AL1'", ()),
        ("delete from socios where cnpj = %s", (F1,)),
    ]
    with _superusuario() as su:
        for sql, params in limpar:
            su.execute(sql, params)
        su.execute(
            "insert into fornecedores (cnpj, razao_social, uf_sede) values (%s, 'SO EM AL LTDA', 'AL')", (F3,)
        )
        # Órgão próprio: a limpeza do dados_catalogo apaga os órgãos TCAT e não pode esbarrar neste contrato.
        su.execute(
            "insert into orgaos (id, nome, uf, esfera) "
            "values ('demo_sintetico:T18-AL1', 'Órgão T18 AL', 'AL', 'estadual')"
        )
        su.execute(
            "insert into contratos (fonte_id, id_origem, uf, orgao_id, fornecedor_cnpj, objeto, valor_global, "
            "data_assinatura, vigencia_fim, url_origem, coletado_em, hash_conteudo) values ('demo_sintetico', "
            "'T18-C1', 'AL', 'demo_sintetico:T18-AL1', %s, 'Serviço AL', 5000, %s, %s, 'about:blank#t18', now(), "
            "repeat('e', 64))",
            (F3, d(-30), d(30)),
        )
        for cnpj, uf, tipo, gravidade, explicacao in SINAIS:
            evidencia = [
                {"tabela": "contratos", "id": "00000000-0000-0000-0000-000000000000", "url_origem": None}
            ]
            su.execute(
                "insert into sinais (fornecedor_cnpj, uf, tipo, gravidade, valor, explicacao, evidencias, "
                "versao_regra) values (%s, %s, %s, %s, 1, %s, %s::jsonb, %s)",
                (cnpj, uf, tipo, gravidade, explicacao, json.dumps(evidencia), VERSAO),
            )
        su.execute(
            "insert into socios (cnpj, socio_chave, socio_tipo, socio_exibicao, coletado_em) "
            "values (%s, repeat('f', 64), 'PF', 'J*** S*** (CPF ***.456.789-**)', now())",
            (F1,),
        )
    yield
    with _superusuario() as su:
        for sql, params in limpar:
            su.execute(sql, params)
        su.execute("delete from carteiras where nome like 'T18 %%'")


@pytest.fixture
def cliente(api, dados_t18):  # noqa: F811
    """API com os dados da T18 e a data de hoje dos dados de teste (o `com_ambiente` limpa os overrides)."""
    app.dependency_overrides[relogio.hoje] = lambda: HOJE
    return api
