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
