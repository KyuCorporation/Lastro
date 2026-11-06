"""GET /fontes. Requer o banco do Compose com os seeds (make seed)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def token(email: str) -> str:
    return client.post("/auth/login", json={"email": email, "senha": "demo123"}).json()["token"]


def test_lista_as_fontes_no_formato_do_contrato():
    r = client.get("/fontes", headers={"Authorization": f"Bearer {token('ana@alfa.demo')}"})
    assert r.status_code == 200
    fontes = {f["id"]: f for f in r.json()}
    assert {"pe_portal", "pncp", "ceis", "cnep"} <= set(fontes)
    for f in fontes.values():
        assert set(f) == {"id", "nome", "tipo", "ultima_execucao"}
        if f["ultima_execucao"] is not None:
            assert set(f["ultima_execucao"]) == {"id", "status", "finalizada_em", "registros_novos"}
            assert f["ultima_execucao"]["status"] != "rodando"


def test_todos_os_perfis_veem_as_fontes():
    for email in ("gil@alfa.demo", "caio@alfa.demo", "bia@beta.demo"):
        assert client.get("/fontes", headers={"Authorization": f"Bearer {token(email)}"}).status_code == 200


def test_sem_token_401():
    assert client.get("/fontes").status_code == 401
