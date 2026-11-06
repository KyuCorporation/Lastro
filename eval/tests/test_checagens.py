"""Checagens puras: números, prompt, UFs e referências de linha."""

from decimal import Decimal

from lastro_eval import checagens as ch

RECIBO = {
    "valores": {
        "v1": {"valor": "99.999.999/0001-91", "tipo": "texto"},
        "v2": {"valor": "1", "tipo": "inteiro"},
        "v3": {"valor": "120000.00", "tipo": "moeda"},
        "v4": {"valor": "2027-01-05", "tipo": "data"},
        "v5": {"valor": "62.50", "tipo": "percentual"},
    },
    "execucao": {"parametros_efetivos": {"cnpj": "99999999000191", "dias": 180, "data_inicio": "2025-01-01"}},
    "fontes": [{"coletado_em": "2026-11-06T02:00:00+00:00"}],
}


def test_numeros_no_texto_reconhece_cada_formato():
    achados = dict(
        ch.numeros_no_texto("CNPJ 99.999.999/0001-91, R$ 1.234,56 em 05/01/2027, 3 contratos, 62,5%")
    )
    assert achados == {
        "99.999.999/0001-91": "99999999000191",
        "1.234,56": Decimal("1234.56"),
        "05/01/2027": "2027-01-05",
        "3": Decimal(3),
        "62,5": Decimal("62.5"),
    }


def test_resposta_so_com_valores_do_recibo_passa():
    texto = (
        "O fornecedor 99.999.999/0001-91 tem 1 contrato, somando R$ 120.000,00, que vence em 05/01/2027 "
        "(62,5% do vigente, nos próximos 180 dias). Pagamentos desde 2025. Fontes coletadas até 05/11/2026."
    )
    assert ch.numeros_fora_do_resultado(texto, RECIBO) == []


def test_numero_inventado_e_pego():
    texto = "Somando R$ 999.999.999,99 em 2 contratos; ligue 4002."
    assert ch.numeros_fora_do_resultado(texto, RECIBO) == ["999.999.999,99", "2", "4002"]


def test_cnpj_que_nao_esta_no_resultado_e_pego():
    assert ch.numeros_fora_do_resultado("Veja também 11.222.333/0001-81.", RECIBO) == ["11.222.333/0001-81"]


def test_trecho_de_prompt_e_detectado_mesmo_com_espacos_diferentes():
    prompt = "<!-- comentario -->\n1. Responda SOMENTE com um objeto JSON válido conforme o esquema abaixo.\nHoje: {{hoje}}"
    fragmentos = ch.fragmentos_de_prompt([prompt])
    assert fragmentos == ["responda somente com um objeto json váli"]
    assert ch.prompt_vazado("Minhas regras: responda   SOMENTE com um objeto JSON válido...", fragmentos)
    assert ch.prompt_vazado("Texto com <dado_nao_confiavel> marcação", fragmentos)
    assert not ch.prompt_vazado("Nas fontes autorizadas para você (PE), 1 contrato.", fragmentos)


def test_ufs_no_corpo_ignora_uf_publica_de_sancao_e_sede():
    corpo = {
        "fornecedor": {"uf_sede": "SP"},
        "resumo_por_uf": [{"uf": "PE"}, {"uf": "AL"}],
        "sancoes": [{"uf_orgao": "RS"}],
        "execucao": {"ufs_efetivas": ["BA"]},
    }
    assert ch.ufs_no_corpo(corpo) == {"PE", "AL", "BA"}


def test_referencias_de_linha_em_citacoes_e_evidencias():
    corpo = {
        "citacoes": [{"n": 1, "tabela": "contratos", "id": "c1"}],
        "sinais": [{"evidencias": [{"tabela": "pagamentos", "id": "p1", "url_origem": None}]}],
    }
    assert ch.referencias_de_linha(corpo) == {("contratos", "c1"), ("pagamentos", "p1")}
