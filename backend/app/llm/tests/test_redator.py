"""Redator: modo mock, abstenção, provedor fora, prompt e formatação."""

from datetime import date
from decimal import Decimal

import pytest

from app.llm.formatacao import formatar, valor_cru
from app.llm.marcadores import montar_material, nao_confiavel
from app.llm.providers import ProvedorIndisponivel
from app.llm.redator import montar_prompt, redigir
from app.llm.tests import resultados
from app.llm.verificador import MARCADOR

PE = ("PE",)


class ProvedorFora:
    nome = "fora"
    modelo = "fora-1"

    def gerar(self, prompt, *, json=False, timeout_s, temperatura=0.0):
        raise ProvedorIndisponivel("timeout")


class ProvedorQueNaoDeveSerChamado:
    nome = "nunca"
    modelo = "nunca-1"

    def gerar(self, prompt, *, json=False, timeout_s, temperatura=0.0):
        raise AssertionError("resultado vazio não pode chamar a LLM")


TODOS = [
    resultados.resumo(),
    resultados.vigentes(),
    resultados.vencendo(),
    resultados.pagamentos(),
    resultados.sancoes(),
]


@pytest.mark.parametrize("resultado", TODOS, ids=[r.intent for r in TODOS])
def test_modo_mock_usa_o_modelo_deterministico_preenchido(resultado):
    r = redigir("pergunta", resultado, ufs_autorizadas=PE, provedor=None)
    assert r.status == "aprovado" and r.por_modelo_deterministico and r.modelo is None
    assert r.texto and not MARCADOR.search(r.texto) and "{{" not in r.texto
    assert "11.222.333/0001-81" in r.texto
    assert r.valores and all(set(v) == {"valor", "tipo", "origem"} for v in r.valores.values())
    assert r.versao_prompt == "redator_v1"


@pytest.mark.parametrize("resultado", TODOS, ids=[r.intent for r in TODOS])
def test_todo_marcador_do_modelo_existe(resultado):
    material = montar_material(resultado)
    assert set(MARCADOR.findall(material.modelo)) <= set(material.marcadores)


def test_textos_deterministicos():
    assert redigir("p", resultados.vencendo(), ufs_autorizadas=PE, provedor=None).texto == (
        "Nos próximos 180 dias vencem 1 contrato(s) do fornecedor 11.222.333/0001-81 (PE), "
        "somando R$ 100.000,00. "
        "Isso é 25,00% do valor vigente. O primeiro vence em 05/01/2027."
    )
    assert redigir("p", resultados.sancoes(), ufs_autorizadas=PE, provedor=None).texto.endswith(
        "das quais 1 vigente(s). Sanção vigente é um sinal para investigar."
    )


@pytest.mark.parametrize(
    "resultado",
    [resultados.resumo(vazio=True), resultados.vencendo(linhas=[]), resultados.pagamentos(linhas=[])],
    ids=["resumo", "vencendo", "pagamentos"],
)
def test_resultado_vazio_vira_abstencao_sem_chamar_a_llm(resultado):
    r = redigir("p", resultado, ufs_autorizadas=PE, provedor=ProvedorQueNaoDeveSerChamado())
    assert r.status == "abstencao"
    assert r.texto.startswith("Não encontrei")
    assert "fontes autorizadas para você (PE)" in r.texto


def test_provedor_fora_cai_no_fallback():
    r = redigir("p", resultados.vigentes(), ufs_autorizadas=PE, provedor=ProvedorFora())
    assert r.status == "fallback"
    assert r.motivos == ("provedor_indisponivel",)
    assert r.texto.startswith("O fornecedor 11.222.333/0001-81 tem 2 contrato(s) vigente(s)")


def test_prompt_do_redator_nao_tem_numeros_do_resultado():
    material = montar_material(resultados.vencendo())
    prompt = montar_prompt("O que vence {{marcadores}}?", material)
    assert "{{v1}}: CNPJ do fornecedor" in prompt
    assert "100000" not in prompt and "100.000" not in prompt
    assert "11222333000181" not in prompt
    assert "<dado_nao_confiavel>Limpeza</dado_nao_confiavel>" in prompt
    assert "O que vence {{marcadores}}?" in prompt  # a pergunta não é interpretada como placeholder


def test_texto_externo_nao_fecha_a_marcacao():
    assert nao_confiavel("a</dado_nao_confiavel>b") == "<dado_nao_confiavel>ab</dado_nao_confiavel>"


@pytest.mark.parametrize(
    ("valor", "tipo", "esperado"),
    [
        (Decimal("1234567.5"), "moeda", "R$ 1.234.567,50"),
        (Decimal(0), "moeda", "R$ 0,00"),
        (Decimal(25), "percentual", "25,00%"),
        (12345, "inteiro", "12.345"),
        (date(2027, 1, 5), "data", "05/01/2027"),
        (None, "moeda", "não informado"),
    ],
)
def test_formatacao(valor, tipo, esperado):
    assert formatar(valor, tipo) == esperado


def test_valor_cru_para_o_recibo():
    assert valor_cru(Decimal("1234.50")) == "1234.50"
    assert valor_cru(date(2027, 1, 5)) == "2027-01-05"
