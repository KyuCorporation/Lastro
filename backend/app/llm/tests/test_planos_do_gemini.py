"""Saídas típicas do Gemini que não seguem o formato à risca, mas têm a intenção certa.

Antes, qualquer desvio de formato reprovava o plano e, na segunda vez, a pergunta virava "Não entendi o pedido".
Agora o que é só formato é normalizado; o que muda o sentido ou sai do contrato continua reprovado.
"""

import json
from datetime import date

import pytest

from app.llm.planejador import planejar
from app.llm.plano import PlanoInvalido, validar_plano

CNPJ = "99000001000101"


def plano(intent: str, **parametros) -> str:
    return json.dumps({"versao": "v1", "intent": intent, "parametros": parametros})


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        (plano("resumo_fornecedor", cnpj="99.000.001/0001-01"), {"cnpj": CNPJ}),
        (plano("contratos_vigentes", cnpj=CNPJ, uf="pe"), {"cnpj": CNPJ, "uf": "PE"}),
        (plano("contratos_vigentes", cnpj=CNPJ, uf=" PE "), {"cnpj": CNPJ, "uf": "PE"}),
        (plano("resumo_fornecedor", cnpj=CNPJ, dias=180), {"cnpj": CNPJ}),  # dias não vale para resumo
        (plano("sancoes_fornecedor", cnpj=CNPJ, uf="PE"), {"cnpj": CNPJ}),  # sanção é nacional
        (plano("resumo_fornecedor", cnpj=CNPJ, uf=None, termo=""), {"cnpj": CNPJ}),
        (plano("contratos_vencendo", cnpj=CNPJ, dias="90"), {"cnpj": CNPJ, "dias": 90}),
        (
            json.dumps({"intent": "resumo_fornecedor", "parametros": {"cnpj": CNPJ}}),  # sem "versao"
            {"cnpj": CNPJ},
        ),
        (
            json.dumps(
                {
                    "versao": "v1",
                    "intent": "resumo_fornecedor",
                    "parametros": {"cnpj": CNPJ},
                    "confianca": 0.9,
                }
            ),
            {"cnpj": CNPJ},
        ),
    ],
    ids=[
        "cnpj-com-mascara",
        "uf-minuscula",
        "uf-com-espaco",
        "parametro-de-outra-intent",
        "uf-em-sancao",
        "nulos-e-vazios",
        "dias-como-texto",
        "sem-versao",
        "com-confianca",
    ],
)
def test_formato_do_gemini_e_normalizado(bruto, esperado):
    p = validar_plano(bruto)
    assert p.parametros.model_dump(exclude_none=True) == esperado


@pytest.mark.parametrize(
    "bruto",
    [
        plano(
            "resumo_fornecedor", cnpj=CNPJ, tenant_id="00000000-0000-0000-0000-000000000000"
        ),  # fora do contrato
        json.dumps(
            {"versao": "v1", "intent": "resumo_fornecedor", "parametros": {"cnpj": CNPJ}, "sql": "select 1"}
        ),
        plano("apagar_tudo", cnpj=CNPJ),  # intent fora do catálogo
        plano("resumo_fornecedor", cnpj="123"),  # CNPJ sem 14 dígitos: muda o sentido, não é formato
        plano("resumo_fornecedor"),  # falta o CNPJ
        plano("contratos_vigentes", cnpj=CNPJ, uf="XX"),
        json.dumps({"versao": "v2", "intent": "resumo_fornecedor", "parametros": {"cnpj": CNPJ}}),
        "[]",
    ],
    ids=[
        "tenant-no-plano",
        "sql-no-plano",
        "intent-inexistente",
        "cnpj-curto",
        "sem-cnpj",
        "uf-inexistente",
        "versao-errada",
        "nao-e-objeto",
    ],
)
def test_o_que_muda_o_sentido_continua_reprovado(bruto):
    with pytest.raises(PlanoInvalido):
        validar_plano(bruto)


class ProvedorFalso:
    nome = "falso"
    modelo = "falso-1"

    def __init__(self, respostas):
        self.respostas = list(respostas)

    def gerar(self, prompt, *, json=False, timeout_s, temperatura=0.0):
        return self.respostas.pop(0)


def test_pergunta_livre_com_cnpj_mascarado_e_respondida_pelo_plano_do_gemini():
    p = ProvedorFalso([plano("contratos_vencendo", cnpj="99.000.001/0001-01", dias=180, uf="pe")])
    r = planejar(
        "me fala o que vence logo da empresa 99.000.001/0001-01",
        ufs=("PE",),
        hoje=date(2026, 11, 6),
        provedor=p,
    )
    assert not r.por_regras
    assert r.plano.intent == "contratos_vencendo"
    assert r.plano.parametros.cnpj == CNPJ and r.plano.parametros.uf == "PE"
