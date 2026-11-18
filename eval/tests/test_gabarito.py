"""Julgamento do gabarito, sem banco: equivalências e métricas."""

import pytest

from lastro_eval.gabarito import CasoGabarito, Observado, carregar, conferir_resultado, julgar, metricas
from tests.conftest import EVAL


def _caso(comportamento, intent="resumo_fornecedor"):
    return CasoGabarito(
        id="G900", usuario="a@b", pergunta="x", intent_esperada=intent, comportamento=comportamento
    )


@pytest.mark.parametrize(
    ("observado", "esperado", "acerta"),
    [
        (Observado(200, None, "respondida", "resumo_fornecedor", None), "responder", True),
        (
            Observado(200, None, "abstencao", "resumo_fornecedor", None, ("resultado_vazio",)),
            "responder",
            True,
        ),
        (
            Observado(200, None, "abstencao", "resumo_fornecedor", None, ("intent_sem_consulta",)),
            "responder",
            False,
        ),
        (Observado(200, None, "abstencao", "fora_de_escopo", None, ("fora_de_escopo",)), "abster", True),
        (Observado(403, "ESCOPO_NEGADO", "negada", None, "uf_fora_do_escopo"), "negar", True),
        (Observado(403, "ESCOPO_NEGADO", "negada", None, "pedido_fora_do_permitido"), "abster", True),
        (Observado(403, "ESCOPO_NEGADO", "negada", None, "pedido_fora_do_permitido"), "negar", True),
        (Observado(403, "ESCOPO_NEGADO", "negada", None, "uf_fora_do_escopo"), "responder", False),
        (Observado(200, None, "esclarecimento", "esclarecer", None), "esclarecer", True),
        (Observado(500, "ERRO_INTERNO", "erro", None, None), "responder", False),
    ],
)
def test_comportamento(observado, esperado, acerta):
    assert julgar(_caso(esperado), observado).acerto_comportamento is acerta


def test_intent_errada_e_intent_nao_avaliavel():
    errada = julgar(_caso("responder"), Observado(200, None, "respondida", "contratos_vigentes", None))
    assert errada.acerto_intent is False and not errada.ok
    guarda = julgar(_caso("negar"), Observado(403, "ESCOPO_NEGADO", "negada", None, "uf_fora_do_escopo"))
    assert guarda.acerto_intent is None and guarda.ok


def test_metricas():
    rs = [
        julgar(
            _caso("responder"), Observado(200, None, "respondida", "resumo_fornecedor", None, (), "fallback")
        ),
        julgar(_caso("responder"), Observado(200, None, "respondida", "contratos_vigentes", None)),
    ]
    m = metricas(rs)
    assert (m["n_casos"], m["ok"], m["acerto_intent"], m["taxa_fallback"]) == (2, 1, 50.0, 50.0)


def test_arquivo_do_gabarito_valido():
    casos = carregar(EVAL / "gabarito" / "perguntas.yaml")
    assert len(casos) >= 20 and len({c.id for c in casos}) == len(casos)


# ------------------------------------------------------------------ resultado: referência e contexto declarado
@pytest.mark.parametrize(
    ("referencia", "contexto", "recibo", "acerta", "nota"),
    [
        ({"a", "b"}, set(), {"a", "b"}, True, None),
        ({"a", "b"}, set(), {"a", "b", "e"}, False, "só na referência: 0, só no recibo: 1"),
        ({"a", "b"}, set(), {"a"}, False, "só na referência: 1, só no recibo: 0"),
        # G024/G025: o empenho citado à parte é contexto declarado, não erro
        ({"a", "b"}, {"e"}, {"a", "b", "e"}, True, None),
        # o contexto é opcional: resposta sem ele continua certa
        ({"a", "b"}, {"e"}, {"a", "b"}, True, None),
        # contexto não cobre linha que falta da referência nem linha estranha
        ({"a", "b"}, {"e"}, {"a", "e"}, False, "só na referência: 1, só no recibo: 0"),
        ({"a", "b"}, {"e"}, {"a", "b", "e", "x"}, False, "só na referência: 0, só no recibo: 1"),
    ],
)
def test_conferir_resultado(referencia, contexto, recibo, acerta, nota):
    assert conferir_resultado(referencia, recibo, contexto) == (acerta, nota)


def test_casos_com_contexto_tem_referencia():
    for caso in carregar(EVAL / "gabarito" / "perguntas.yaml"):
        if caso.sql_contexto:
            assert caso.sql_referencia and caso.comportamento == "responder", caso.id
