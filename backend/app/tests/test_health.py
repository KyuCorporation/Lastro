from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def test_health_com_banco(monkeypatch):
    monkeypatch.setattr(main, "db_disponivel", lambda: True)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "ok", "llm": main.settings.llm_provider}


def test_health_sem_banco_fica_degradado(monkeypatch):
    monkeypatch.setattr(main, "db_disponivel", lambda: False)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "degradado"
    assert r.json()["db"] == "indisponivel"


def test_raiz_leva_para_a_documentacao():
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/docs"
    assert client.get("/docs").status_code == 200
