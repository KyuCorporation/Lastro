"""Regras dos sinais v1 (SPEC §9), sem banco."""

import re
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from lastro_pipeline.sinais.regras import (
    ContratoFato,
    PagamentoFato,
    SancaoFato,
    calcular_todos,
    concentracao,
    moeda,
    penhasco,
    sancao_direta,
    subtrair_meses,
)

HOJE = date(2026, 11, 6)
F1 = "11222333000181"
F2 = "11444777000161"


def d(dias: int) -> date:
    return HOJE + timedelta(days=dias)


def contrato(valor, fim, *, uf="PE", cnpj=F1, orgao="o:1", assinatura=None, id_=None) -> ContratoFato:
    return ContratoFato(
        id=id_ or uuid4(),
        cnpj=cnpj,
        uf=uf,
        orgao_id=orgao,
        valor=None if valor is None else Decimal(valor),
        data_assinatura=assinatura,
        vigencia_inicio=None,
        vigencia_fim=fim,
        url_origem="https://exemplo/c",
    )


def pagamento(valor, data, *, uf="PE", cnpj=F1, orgao="o:1") -> PagamentoFato:
    return PagamentoFato(uuid4(), cnpj, uf, orgao, Decimal(valor), data, "https://exemplo/p")


def sancao(inicio, fim, *, cnpj=F1, fonte="ceis") -> SancaoFato:
    return SancaoFato(uuid4(), fonte, cnpj, "Impedimento", inicio, fim, "https://exemplo/s")


# ===================== sancao_direta =====================
def test_sancao_vigente_vira_sinal_forte_nacional():
    s = sancao(d(-10), d(100))
    (sinal,) = sancao_direta([s], HOJE)
    assert (sinal.tipo, sinal.gravidade, sinal.uf, sinal.valor) == ("sancao_direta", "forte", None, 1)
    assert sinal.evidencias == [{"tabela": "sancoes", "id": str(s.id), "url_origem": "https://exemplo/s"}]
    assert sinal.explicacao == f"Consta 1 sanção vigente no CEIS, até {d(100):%d/%m/%Y}."


@pytest.mark.parametrize(
    ("inicio", "fim", "vigente"),
    [
        (d(-10), d(-1), False),  # terminou ontem
        (d(-10), HOJE, True),  # termina hoje: ainda vale
        (d(1), d(100), False),  # começa amanhã
        (HOJE, None, True),  # começa hoje, sem prazo final
        (None, None, True),  # sem datas: tratada como vigente (o cadastro diz que está sancionada)
    ],
)
def test_limites_de_vigencia_da_sancao(inicio, fim, vigente):
    assert bool(sancao_direta([sancao(inicio, fim)], HOJE)) is vigente


def test_varias_sancoes_do_mesmo_cnpj_viram_um_sinal():
    sinais = sancao_direta(
        [sancao(d(-10), d(50)), sancao(d(-5), None, fonte="cnep"), sancao(d(-400), d(-1))], HOJE
    )
    (sinal,) = sinais
    assert sinal.valor == 2 and len(sinal.evidencias) == 2
    assert sinal.explicacao == "Constam 2 sanções vigentes (CEIS, CNEP), uma delas sem prazo final."


# ===================== penhasco =====================
def test_metade_do_vigente_vencendo_em_180_dias_dispara():
    vence = contrato("100000.00", d(60))
    (sinal,) = penhasco([vence, contrato("100000.00", d(400))], HOJE)
    assert (sinal.tipo, sinal.gravidade, sinal.uf) == ("penhasco", "atencao", "PE")
    assert sinal.valor == Decimal("50.0")
    assert [e["id"] for e in sinal.evidencias] == [str(vence.id)]
    assert sinal.explicacao == (
        "50,0% do valor vigente em PE (R$ 100.000,00 de R$ 200.000,00) termina em até 180 dias, em 1 contrato."
    )


def test_abaixo_de_50_por_cento_nao_dispara():
    assert penhasco([contrato("49999.99", d(60)), contrato("50000.01", d(400))], HOJE) == []


def test_limite_de_180_dias_e_inclusivo_e_181_nao_conta():
    assert penhasco([contrato("100", d(180))], HOJE)
    assert penhasco([contrato("100", d(181))], HOJE) == []


def test_contrato_encerrado_ou_sem_valor_nao_entra_no_vigente():
    # encerrado e sem valor fora do total: o único vigente com valor vence em 30 dias → 100%
    (sinal,) = penhasco(
        [contrato("100", d(30)), contrato("900", d(-1)), contrato(None, d(400)), contrato("0", d(400))], HOJE
    )
    assert sinal.valor == Decimal("100.0")


def test_penhasco_e_calculado_por_uf_sem_misturar():
    """Em PE vence 20% (não dispara); em AL vence 100%. Somado daria 60% e vazaria AL para quem só vê PE."""
    sinais = penhasco(
        [
            contrato("100", d(30), uf="PE"),
            contrato("400", d(400), uf="PE"),
            contrato("400", d(30), uf="AL"),
        ],
        HOJE,
    )
    assert [(s.uf, s.valor) for s in sinais] == [("AL", Decimal("100.0"))]
    assert "R$ 400,00 de R$ 400,00" in sinais[0].explicacao


# ===================== concentracao =====================
def test_um_orgao_com_70_por_cento_do_recebido_dispara():
    sinais = concentracao(
        [],
        [pagamento("70", d(-30), orgao="o:1"), pagamento("30", d(-30), orgao="o:2")],
        HOJE,
        {"o:1": "Secretaria de Saúde"},
    )
    (sinal,) = sinais
    assert (sinal.tipo, sinal.gravidade, sinal.uf, sinal.valor) == ("concentracao", "atencao", "PE", 70)
    assert sinal.explicacao.endswith("vem de um único órgão: Secretaria de Saúde.")
    assert "do valor recebido em PE nos últimos 24 meses (R$ 70,00 de R$ 100,00)" in sinal.explicacao
    assert len(sinal.evidencias) == 1 and sinal.evidencias[0]["tabela"] == "pagamentos"


def test_abaixo_de_70_por_cento_nao_dispara():
    assert concentracao([], [pagamento("69", d(-1)), pagamento("31", d(-1), orgao="o:2")], HOJE) == []


def test_janela_ignora_pagamento_antigo_que_mudaria_o_resultado():
    antigo = subtrair_meses(HOJE, 24) - timedelta(days=1)
    pagos = [
        pagamento("1000", antigo, orgao="o:1"),
        pagamento("50", d(-1), orgao="o:2"),
        pagamento("50", d(-1)),
    ]
    assert concentracao([], pagos, HOJE) == []  # na janela: 50/50; com o antigo seria 91% de o:1


def test_orgao_desconhecido_entra_no_total_mas_nao_e_o_maior():
    pagos = [pagamento("60", d(-1), orgao=None), pagamento("40", d(-1), orgao="o:1")]
    assert concentracao([], pagos, HOJE) == []  # o:1 tem 40% do total


def test_sem_pagamentos_usa_contratos_assinados_na_janela_e_avisa():
    """O PNCP (AL) só traz contratos: a concentração usa o valor contratado e a explicação diz isso."""
    sinais = concentracao(
        [
            contrato("900", d(100), uf="AL", assinatura=d(-60)),
            contrato("100", d(100), uf="AL", orgao="o:2", assinatura=d(-60)),
        ],
        [],
        HOJE,
    )
    (sinal,) = sinais
    assert sinal.uf == "AL" and sinal.evidencias[0]["tabela"] == "contratos"
    assert "do valor contratado (a fonte não traz pagamentos)" in sinal.explicacao


def test_com_pagamentos_na_uf_os_contratos_nao_entram():
    sinais = concentracao(
        [contrato("1000000", d(100), orgao="o:9", assinatura=d(-10))],
        [pagamento("50", d(-1), orgao="o:1"), pagamento("50", d(-1), orgao="o:2")],
        HOJE,
    )
    assert sinais == []


def test_nome_do_orgao_externo_vira_uma_linha_curta():
    nome = "Órgão\ncom quebra " + "x" * 300
    (sinal,) = concentracao([], [pagamento("100", d(-1))], HOJE, {"o:1": nome})
    assert "\n" not in sinal.explicacao and len(sinal.explicacao) < 300


# ===================== transversais =====================
PALAVRAS_PROIBIDAS = re.compile(r"fraude|irregular|suspeit|corrup", re.IGNORECASE)


def _todos():
    return calcular_todos(
        [contrato("100", d(30)), contrato("100", d(30), uf="AL", cnpj=F2, assinatura=d(-5))],
        [pagamento("100", d(-1))],
        [sancao(d(-1), None), sancao(d(-1), d(5), cnpj=F2, fonte="cnep")],
        HOJE,
    )


def test_explicacoes_sao_uma_frase_sem_linguagem_acusatoria():
    sinais = _todos()
    assert {s.tipo for s in sinais} == {"sancao_direta", "penhasco", "concentracao"}
    for s in sinais:
        assert not PALAVRAS_PROIBIDAS.search(s.explicacao), s.explicacao
        assert s.explicacao.endswith(".") and "\n" not in s.explicacao
        assert s.versao_regra == "v1"


def test_toda_evidencia_aponta_para_uma_linha_de_origem():
    for s in _todos():
        assert s.evidencias
        for e in s.evidencias:
            assert set(e) == {"tabela", "id", "url_origem"}
            assert e["tabela"] in {"contratos", "pagamentos", "sancoes"}
            UUID(e["id"])


def test_resultado_e_deterministico():
    id_fixo = UUID(int=7)
    c = [contrato("100", d(30), id_=id_fixo), contrato("100", d(40))]
    assert penhasco(c, HOJE) == penhasco(list(reversed(c)), HOJE)


@pytest.mark.parametrize(
    ("origem", "meses", "esperado"),
    [
        (date(2026, 11, 6), 24, date(2024, 11, 6)),
        (date(2026, 3, 31), 1, date(2026, 2, 28)),
        (date(2024, 2, 29), 12, date(2023, 2, 28)),
    ],
)
def test_subtrair_meses(origem, meses, esperado):
    assert subtrair_meses(origem, meses) == esperado


def test_moeda_no_formato_brasileiro():
    assert moeda(Decimal("1234567.891")) == "R$ 1.234.567,89"
