"""JSON canônico, hash e montagem do recibo, sem banco."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from app.core.contexto import ContextoAcesso
from app.modules.recibos.canonico import hash_recibo, json_canonico, para_json
from app.modules.recibos.montagem import IA, DadosRecibo, Execucao, Fonte, montar_conteudo
from app.modules.recibos.tests.esquema import erros

CTX = ContextoAcesso(
    UUID("00000000-0000-0000-0000-00000000a1fa"),
    UUID("00000000-0000-0000-0000-0000000000a1"),
    "analista",
    ("PE",),
)
AGORA = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def dados(**trocas) -> DadosRecibo:
    base = {
        "consulta_id": UUID("10000000-0000-0000-0000-000000000001"),
        "ctx": CTX,
        "pergunta": "Quanto vence?",
        "plano": {"versao": "v1", "intent": "contratos_vencendo", "parametros": {"cnpj": "11222333000181"}},
        "execucao": Execucao(
            "contratos_vencendo@v1", {"cnpj": "11222333000181", "dias": 180}, ("PE",), 1, 12
        ),
        "linhas": (
            {
                "tabela": "contratos",
                "id": UUID("20000000-0000-0000-0000-000000000001"),
                "fonte_id": "pe_portal",
                "id_origem": "ctr:1",
                "url_origem": "https://sistemas.tcepe.tc.br/x",
                "coletado_em": AGORA,
                "hash_conteudo": "a" * 64,
                "valor_global": Decimal("100000.00"),  # não vai para o recibo: só a proveniência
            },
        ),
        "fontes": (Fonte("pe_portal", "TCE-PE Dados Abertos", AGORA, None, False),),
        "valores": {"v4": {"valor": "100000.00", "tipo": "moeda", "origem": "sum(valor_global)"}},
        "resposta_final": "Vence 1 contrato, somando R$ 100.000,00.",
        "verificacao_status": "aprovado",
        "verificacao_motivos": (),
        "ia": IA("mock", None, "planejador_v1", "redator_v2", True),
        "criado_em": AGORA,
    }
    return DadosRecibo(**{**base, **trocas})


# ------------------------------------------------------------------ canônico
def test_ordem_das_chaves_nao_muda_o_hash():
    assert hash_recibo({"b": 1, "a": {"y": 2, "x": 3}}) == hash_recibo({"a": {"x": 3, "y": 2}, "b": 1})


def test_json_canonico_sem_espacos_e_em_utf8():
    assert json_canonico({"b": "ção", "a": [1, 2]}) == '{"a":[1,2],"b":"ção"}'


def test_tipos_convertidos_sem_float_para_dinheiro():
    convertido = para_json(
        {"d": Decimal("1234.50"), "data": date(2027, 1, 5), "id": UUID(int=1), "t": (1, 2), "c": {3, 1, 2}}
    )
    assert convertido == {
        "d": "1234.50",
        "data": "2027-01-05",
        "id": "00000000-0000-0000-0000-000000000001",
        "t": [1, 2],
        "c": [1, 2, 3],
    }


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), object()])
def test_valor_sem_representacao_estavel_e_recusado(valor):
    with pytest.raises((TypeError, ValueError)):
        para_json({"x": valor})


def test_ida_e_volta_em_json_preserva_o_hash():
    conteudo = montar_conteudo(
        dados(plano={"versao": "v1", "intent": "esclarecer", "parametros": {}, "confianca": 0.85})
    )
    assert hash_recibo(json.loads(json.dumps(conteudo))) == hash_recibo(conteudo)


# ------------------------------------------------------------------ montagem conforme o contrato
def test_conteudo_segue_o_schema_do_recibo():
    assert erros(montar_conteudo(dados())) == []


def test_linha_do_recibo_leva_so_a_proveniencia():
    (linha,) = montar_conteudo(dados())["linhas"]
    assert set(linha) == {
        "tabela",
        "id",
        "fonte_id",
        "id_origem",
        "url_origem",
        "coletado_em",
        "hash_conteudo",
    }
    assert linha["id"] == "20000000-0000-0000-0000-000000000001"


def test_abstencao_sem_execucao_tambem_segue_o_schema():
    conteudo = montar_conteudo(
        dados(
            execucao=Execucao("fora_de_escopo"),
            linhas=(),
            fontes=(),
            valores={},
            verificacao_status="abstencao",
            verificacao_motivos=("fora_de_escopo",),
            ia=IA("mock", None, "planejador_v1", None, True),
            plano={
                "versao": "v1",
                "intent": "fora_de_escopo",
                "parametros": {"motivo": "pergunta fora do catálogo"},
            },
        )
    )
    assert erros(conteudo) == []
    assert "versao_prompt_redator" not in conteudo["ia"]


def test_schema_acusa_campo_a_mais():
    conteudo = {**montar_conteudo(dados()), "extra": 1}
    assert any("extra" in e for e in erros(conteudo))
