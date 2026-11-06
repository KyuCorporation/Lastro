"""O verificador não pode reprovar texto correto: senão toda resposta cai no modelo determinístico e a LLM
não serve para nada. O modelo determinístico (com marcadores) é o texto correto canônico de cada intent."""

import pytest

from app.llm.marcadores import montar_material
from app.llm.redator import redigir
from app.llm.tests import resultados
from app.llm.verificador import verificar

PE = ("PE",)
NAO_VAZIOS = [
    resultados.resumo(),
    resultados.vigentes(),
    resultados.vencendo(),
    resultados.pagamentos(),
    resultados.sancoes(),
    resultados.sancoes(vigente=False),
]


@pytest.mark.parametrize("resultado", NAO_VAZIOS, ids=lambda r: r.intent)
def test_modelo_deterministico_passa_no_verificador(resultado):
    m = montar_material(resultado)
    anos = {v.year for k, v in resultado.parametros.items() if k.startswith("data_")}
    v = verificar(
        m.modelo,
        m.marcadores,
        ufs_autorizadas=PE,
        anos_permitidos=anos,
        essenciais=m.essenciais,
        resultado_vazio=m.vazio,
    )
    assert v.aprovado, v.motivos


@pytest.mark.parametrize(
    ("resultado", "texto"),
    [
        (
            resultados.vencendo(),
            (
                "Nos próximos {{v2}} dias vence {{v3}} contrato do fornecedor {{v1}}, no valor de R$ {{v4}}, "
                "o que representa {{v7}}% do valor vigente. O primeiro vencimento é em {{v5}}."
            ),
        ),
        (
            resultados.vencendo(),
            (
                "Há {{v3}} contrato do fornecedor {{v1}} terminando em breve em Pernambuco, com o órgão "
                "Secretaria de Saúde, somando {{v4}}. É um sinal para investigar a renovação."
            ),
        ),
        (
            resultados.resumo(),
            (
                "O fornecedor {{v1}} tem {{v2}} contratos ({{v3}}), dos quais {{v4}} seguem vigentes. "
                "Recebeu {{v6}} em {{v5}} pagamento, nas fontes de {{v7}}."
            ),
        ),
        (
            resultados.sancoes(),
            (
                "Constam {{v2}} sanção no CEIS ou no CNEP para o fornecedor {{v1}}, e {{v3}} está vigente. "
                "Sanção vigente é um sinal para investigar."
            ),
        ),
        (
            resultados.sancoes(vigente=False),
            "O fornecedor {{v1}} tem {{v2}} sanção registrada, mas nenhuma sanção vigente.",
        ),
        (
            resultados.pagamentos(),
            "Em 2025 o fornecedor {{v1}} recebeu {{v6}}, em {{v5}} pagamento da Prefeitura de Garanhuns.",
        ),
    ],
    ids=["vencendo-simbolos", "vencendo-orgao", "resumo", "sancoes", "sancoes-encerradas", "pagamentos-ano"],
)
def test_parafrases_corretas_sao_aprovadas(resultado, texto):
    class Provedor:
        nome, modelo = "fixo", "fixo-1"

        def gerar(self, prompt, *, json=False, timeout_s, temperatura=0.0):
            return texto

    r = redigir("pergunta", resultado, ufs_autorizadas=PE, provedor=Provedor())
    assert r.status == "aprovado", r.motivos
    assert "{{" not in r.texto
