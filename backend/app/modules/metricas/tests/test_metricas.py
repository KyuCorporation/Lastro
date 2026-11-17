"""GET /metricas lê os relatórios do eval; relatório ausente ou corrompido vira nulo."""

import json

from fastapi.testclient import TestClient

from app.core.contexto import ContextoAcesso
from app.main import app
from app.modules.auth.dependencias import contexto_atual
from app.modules.metricas import service

CTX = ContextoAcesso.__new__(ContextoAcesso)


def _escrever(pasta, nome, gerado_em, metricas):
    (pasta / f"{nome}.json").write_text(
        json.dumps({"gerado_em": gerado_em, "provedor_llm": "mock", "n_casos": 5, "metricas": metricas}),
        encoding="utf-8",
    )


def test_le_os_relatorios_e_a_data_mais_recente(tmp_path):
    _escrever(tmp_path, "ataques", "2026-11-06T14:00:00+00:00", {"vazamentos": 0, "pct_bloqueado": 100.0})
    _escrever(tmp_path, "gabarito", "2026-11-06T15:00:00+00:00", {"acerto_intent": 100.0})
    m = service.metricas(tmp_path)
    assert m["ataques"]["vazamentos"] == 0 and m["ataques"]["n_casos"] == 5
    assert m["eval"]["acerto_intent"] == 100.0
    assert m["cronometro"] is None
    assert m["ultima_atualizacao"] == "2026-11-06T15:00:00+00:00"


def test_relatorio_corrompido_ou_ausente_vira_nulo(tmp_path):
    (tmp_path / "ataques.json").write_text("{nao é json", encoding="utf-8")
    assert service.metricas(tmp_path) == {
        "eval": None,
        "ataques": None,
        "cronometro": None,
        "ultima_atualizacao": None,
    }


def test_rota_devolve_o_formato_do_contrato(tmp_path, monkeypatch):
    _escrever(tmp_path, "ataques", "2026-11-06T14:00:00+00:00", {"vazamentos": 0})
    monkeypatch.setattr(service, "pasta_relatorios", lambda: tmp_path)
    app.dependency_overrides[contexto_atual] = lambda: CTX
    try:
        r = TestClient(app).get("/metricas")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert set(r.json()) == {"eval", "ataques", "cronometro", "ultima_atualizacao"}
    assert r.json()["ataques"]["vazamentos"] == 0


def _escrever_de(pasta, arquivo, provedor, gerado_em, metricas):
    (pasta / arquivo).write_text(
        json.dumps({"gerado_em": gerado_em, "provedor_llm": provedor, "n_casos": 5, "metricas": metricas}),
        encoding="utf-8",
    )


def test_cada_parte_traz_o_resultado_por_provedor(tmp_path):
    _escrever_de(tmp_path, "ataques.json", "mock", "2026-11-17T10:00:00+00:00", {"pct_bloqueado": 100.0})
    _escrever_de(tmp_path, "ataques.mock.json", "mock", "2026-11-17T10:00:00+00:00", {"pct_bloqueado": 100.0})
    _escrever_de(
        tmp_path, "ataques.gemini.json", "gemini", "2026-11-16T10:00:00+00:00", {"pct_bloqueado": 98.3}
    )
    m = service.metricas(tmp_path)
    assert m["ataques"]["pct_bloqueado"] == 100.0
    por = m["ataques"]["por_provedor"]
    assert set(por) == {"mock", "gemini"}
    assert (
        por["gemini"]["pct_bloqueado"] == 98.3 and por["gemini"]["gerado_em"] == "2026-11-16T10:00:00+00:00"
    )
    assert "por_provedor" not in por["gemini"]
    assert m["ultima_atualizacao"] == "2026-11-17T10:00:00+00:00"


def test_relatorio_antigo_sem_copia_por_provedor_aparece_pelo_proprio_provedor(tmp_path):
    _escrever_de(tmp_path, "gabarito.json", "mock", "2026-11-17T10:00:00+00:00", {"acerto_intent": 100.0})
    assert set(service.metricas(tmp_path)["eval"]["por_provedor"]) == {"mock"}


def test_copia_de_provedor_sem_relatorio_principal_ainda_aparece(tmp_path):
    _escrever_de(
        tmp_path, "gabarito.gemini.json", "gemini", "2026-11-16T10:00:00+00:00", {"acerto_intent": 94.0}
    )
    m = service.metricas(tmp_path)
    assert m["eval"]["provedor_llm"] == "gemini"
    assert set(m["eval"]["por_provedor"]) == {"gemini"}


def test_arquivo_de_provedor_com_nome_estranho_ou_corrompido_e_ignorado(tmp_path):
    _escrever_de(tmp_path, "ataques.json", "mock", "2026-11-17T10:00:00+00:00", {})
    (tmp_path / "ataques.gemini.json").write_text("{quebrado", encoding="utf-8")
    _escrever_de(tmp_path, "ataques.Mais Um.json", "x", "2026-11-17T10:00:00+00:00", {})
    assert set(service.metricas(tmp_path)["ataques"]["por_provedor"]) == {"mock"}
