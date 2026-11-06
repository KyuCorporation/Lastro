"""Ataques ao verificador (SPEC §8.3, §8.5): formas de o redator passar número, data, link ou acusação
sem usar os marcadores, ou de enganar a leitura do texto na tela. Toda reprovação leva ao modelo
determinístico (fallback), então errar para o lado de reprovar é seguro."""

import pytest

from app.llm.marcadores import montar_material
from app.llm.tests.resultados import vencendo
from app.llm.verificador import verificar

PE = ("PE",)
# Caracteres invisíveis montados com chr(): nunca literais no código-fonte (o formatador os desfaria).
RLO, LRI = chr(0x202E), chr(0x2066)


def material():
    # vencendo: v1 cnpj, v2 dias, v3 n, v4 valor, v5 primeiro vencimento, v6 ufs, v7 percentual
    return montar_material(vencendo())


def _verificar(texto: str, **extra):
    m = material()
    opcoes = {"ufs_autorizadas": PE, "essenciais": m.essenciais, "resultado_vazio": m.vazio, **extra}
    return verificar(texto, m.marcadores, **opcoes)


# ------------------------------------------------------------------ números e datas sem marcador
@pytest.mark.parametrize(
    "texto",
    [
        "Vencem três contratos, somando {{v4}}.",
        "Vencem {{v3}} contratos, somando um milhão de reais e {{v4}}.",
        "Vencem {{v3}} contratos, metade do valor vigente {{v4}}.",
        "Vencem {{v3}} contratos; ambos somam {{v4}}.",
        "Vencem {{v3}} contratos, {{v4}}, cerca de cinquenta por cento.",
        "Vencem {{v3}} contratos ({{v4}}), o primeiro em janeiro.",
        "Vencem {{v3}} contratos ({{v4}}), o primeiro amanhã.",
        "Vencem {{v3}} contratos, somando {{v4}} vezes ²",
        "Vencem {{v3}} contratos, somando {{v4}} e mais ½.",
        "Vencem {{v3}} contratos, somando {{v4}} ou ３ vezes isso.",
    ],
)
def test_numero_ou_data_por_extenso_ou_em_outro_alfabeto_e_reprovado(texto):
    v = _verificar(texto)
    assert not v.aprovado
    assert "numero_fora_do_resultado" in v.motivos


def test_um_como_artigo_e_ordinal_continuam_permitidos():
    v = _verificar("Há {{v3}} contrato vencendo: um contrato de limpeza, o primeiro a terminar, soma {{v4}}.")
    assert v.aprovado, v.motivos


# ------------------------------------------------------------------ texto que engana a leitura
@pytest.mark.parametrize(
    "texto",
    [
        "Vence {{v3}} contrato, somando " + RLO + "{{v4}}.",  # override bidirecional inverte o valor na tela
        "Vence {{v3}} contrato, somando {{v4}}" + LRI + ".",
        "Vence {{v3}} contrato\u200b, somando {{v4}}.",  # caractere invisível
        "Vence {{v3}} contrato, somando {{v4}}.\x07",
    ],
)
def test_caractere_invisivel_ou_de_direcao_e_reprovado(texto):
    v = _verificar(texto)
    assert not v.aprovado
    assert "caractere_nao_permitido" in v.motivos


def test_homoglifo_de_outro_alfabeto_nao_esconde_acusacao():
    v = _verificar("O fornecedor {{v1}} tem indício de frаude: {{v3}} contrato.")  # 'а' cirílico
    assert not v.aprovado
    assert "caractere_nao_permitido" in v.motivos


@pytest.mark.parametrize(
    "texto",
    [
        "O fornecedor {{v1}} tem {{v3}} contrato com indício de ilícito.",
        "Há sinais de superfaturamento nos {{v3}} contratos.",
        "O fornecedor {{v1}} pode estar envolvido em desvio de dinheiro: {{v3}} contrato.",
        "Contratos de {{v1}} com pagamento de propina: {{v3}}.",
    ],
)
def test_linguagem_de_acusacao_ampliada(texto):
    v = _verificar(texto)
    assert not v.aprovado
    assert "linguagem_de_acusacao" in v.motivos


@pytest.mark.parametrize(
    "texto",
    [
        "Veja em bit.ly/contratos: {{v3}} contrato.",
        "Fale com contato@empresa.app sobre o {{v3}} contrato.",
        "Detalhes em portal.transparencia.info, {{v3}} contrato.",
    ],
)
def test_link_e_email_sao_reprovados(texto):
    v = _verificar(texto)
    assert not v.aprovado
    assert "url_fora_do_resultado" in v.motivos


# ------------------------------------------------------------------ resposta que contradiz o resultado
@pytest.mark.parametrize(
    "texto",
    [
        "Não encontrei contratos do fornecedor {{v1}} que vençam nos próximos {{v2}} dias.",
        "Não há registros para o fornecedor {{v1}}.",
        "Nenhum registro do fornecedor {{v1}} nas fontes.",
    ],
)
def test_negar_registros_quando_o_resultado_tem_linhas_e_reprovado(texto):
    v = _verificar(texto)
    assert not v.aprovado
    assert "contradiz_resultado" in v.motivos


def test_texto_sem_nenhum_valor_do_resultado_e_reprovado():
    v = _verificar("O fornecedor {{v1}} tem contratos que vencem em breve nas fontes de {{v6}}.")
    assert not v.aprovado
    assert "sem_valor_do_resultado" in v.motivos


def test_texto_longo_demais_e_reprovado():
    v = _verificar("Vence {{v3}} contrato somando {{v4}}. " + "Texto de enchimento. " * 200)
    assert not v.aprovado
    assert "texto_longo" in v.motivos


# ------------------------------------------------------------------ preenchimento sem símbolo duplicado
def test_simbolo_de_moeda_e_de_percentual_nao_duplicam():
    v = _verificar("Vence {{v3}} contrato, somando R$ {{v4}}, ou {{v7}}% do vigente.")
    assert v.aprovado, v.motivos
    assert "R$ R$" not in v.texto_final
    assert "%%" not in v.texto_final
    assert v.texto_final == "Vence 1 contrato, somando R$ 100.000,00, ou 25,00% do vigente."
