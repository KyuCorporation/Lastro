"""Provedor Gemini sem rede: cliente falso no lugar do google-genai."""

from datetime import date

import pytest
from google.genai import errors

from app.llm.providers import base, gemini
from app.llm.providers.gemini import ProvedorGemini
from app.llm.regras import planejar_por_regras


class Resposta:
    def __init__(self, text):
        self.text = text


class ClienteFalso:
    """Imita `genai.Client`: `models.generate_content` devolve ou levanta o que foi programado."""

    def __init__(self, resultados):
        self.resultados = list(resultados)
        self.configs = []
        self.models = self

    def generate_content(self, *, model, contents, config):
        self.configs.append(config)
        r = self.resultados.pop(0)
        if isinstance(r, Exception):
            raise r
        return Resposta(r)


def erro_servidor(codigo=503):
    return errors.ServerError(
        codigo, {"error": {"code": codigo, "message": "high demand", "status": "UNAVAILABLE"}}
    )


@pytest.fixture(autouse=True)
def sem_pausa(monkeypatch):
    monkeypatch.setattr(gemini, "PAUSA_ANTES_DE_REPETIR_S", 0)


def test_raciocinio_desligado_por_padrao():
    cliente = ClienteFalso(['{"ok": true}'])
    ProvedorGemini("chave", "gemini-3.6-flash", cliente=cliente).gerar("p", json=True, timeout_s=5)
    config = cliente.configs[0]
    assert config.thinking_config.thinking_budget == 0
    assert config.response_mime_type == "application/json"
    assert config.http_options.timeout == 5000


def test_raciocinio_ligado_pelo_env():
    cliente = ClienteFalso(["ok"])
    ProvedorGemini("chave", "m", raciocinio=True, cliente=cliente).gerar("p", timeout_s=5)
    assert cliente.configs[0].thinking_config is None


def test_503_passageiro_repete_uma_vez():
    cliente = ClienteFalso([erro_servidor(), '{"ok": true}'])
    assert ProvedorGemini("chave", "m", cliente=cliente).gerar("p", timeout_s=5) == '{"ok": true}'
    assert len(cliente.configs) == 2


def test_503_duas_vezes_vira_indisponivel():
    cliente = ClienteFalso([erro_servidor(), erro_servidor()])
    with pytest.raises(base.ProvedorIndisponivel):
        ProvedorGemini("chave", "m", cliente=cliente).gerar("p", timeout_s=5)
    assert len(cliente.configs) == 2


def test_erro_do_cliente_nao_repete():
    """Modelo inexistente ou chave errada (4xx) não melhora repetindo: cai no fallback na hora."""
    cliente = ClienteFalso([errors.ClientError(404, {"error": {"code": 404, "message": "not found"}})])
    with pytest.raises(base.ProvedorIndisponivel):
        ProvedorGemini("chave", "m", cliente=cliente).gerar("p", timeout_s=5)
    assert len(cliente.configs) == 1


def test_resposta_vazia_vira_indisponivel():
    with pytest.raises(base.ProvedorIndisponivel):
        ProvedorGemini("chave", "m", cliente=ClienteFalso([""])).gerar("p", timeout_s=5)


@pytest.mark.parametrize(
    "pergunta",
    [
        "Que contratos o 18008915000109 ainda mantém ativos hoje?",
        "Quais contratos em andamento do CNPJ 18.008.915/0001-09?",
    ],
)
def test_regras_entendem_contrato_ativo(pergunta):
    assert planejar_por_regras(pergunta, date(2026, 11, 6)).intent == "contratos_vigentes"


def test_modelo_que_recusa_desligar_o_raciocinio_segue_sem_a_configuracao():
    erro_400 = errors.ClientError(
        400, {"error": {"code": 400, "message": "Request contains an invalid argument."}}
    )
    cliente = ClienteFalso([erro_400, "ok", "ok de novo"])
    p = ProvedorGemini("chave", "gemini-3.5-flash-lite", cliente=cliente)
    assert p.gerar("p", timeout_s=5) == "ok"
    assert cliente.configs[0].thinking_config is not None and cliente.configs[1].thinking_config is None
    assert p.gerar("p", timeout_s=5) == "ok de novo"  # já não manda a configuração recusada
    assert cliente.configs[2].thinking_config is None
    assert len(cliente.configs) == 3


def test_400_sem_relacao_com_raciocinio_nao_fica_em_laco():
    erro_400 = errors.ClientError(400, {"error": {"code": 400, "message": "bad"}})
    cliente = ClienteFalso([erro_400, erro_400])
    with pytest.raises(base.ProvedorIndisponivel):
        ProvedorGemini("chave", "m", cliente=cliente).gerar("p", timeout_s=5)
    assert len(cliente.configs) == 2


def test_cota_esgotada_429_nao_repete():
    erro_429 = errors.ClientError(429, {"error": {"code": 429, "message": "RESOURCE_EXHAUSTED"}})
    cliente = ClienteFalso([erro_429])
    with pytest.raises(base.ProvedorIndisponivel):
        ProvedorGemini("chave", "m", cliente=cliente).gerar("p", timeout_s=5)
    assert len(cliente.configs) == 1
