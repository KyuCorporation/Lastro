"""Login e /me. Requer o banco do Compose com os seeds de demo (make seed)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import criar_token
from app.main import app

client = TestClient(app)

USUARIOS_SEED = [
    ("ana@alfa.demo", "analista", "Cliente Alfa", ["PE"]),
    ("caio@alfa.demo", "auditor", "Cliente Alfa", ["PE"]),
    ("gil@alfa.demo", "gestor", "Cliente Alfa", ["PE"]),
    ("admin@alfa.demo", "admin", "Cliente Alfa", ["AL", "PE"]),
    ("bia@beta.demo", "analista", "Cliente Beta", ["AL"]),
]


def login(email: str, senha: str = "demo123"):
    return client.post("/auth/login", json={"email": email, "senha": senha})


def assert_401(r) -> None:
    assert r.status_code == 401
    erro = r.json()["erro"]
    assert erro["codigo"] == "NAO_AUTENTICADO"
    assert erro["request_id"]


@pytest.mark.parametrize(("email", "perfil", "tenant", "ufs"), USUARIOS_SEED)
def test_login_dos_usuarios_de_seed(email, perfil, tenant, ufs):
    r = login(email)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["token"]
    assert corpo["usuario"]["perfil"] == perfil
    assert corpo["usuario"]["tenant"]["nome"] == tenant
    assert corpo["usuario"]["ufs"] == ufs

    me = client.get("/me", headers={"Authorization": f"Bearer {corpo['token']}"})
    assert me.status_code == 200
    assert me.json() == corpo["usuario"]


def test_email_com_maiusculas_tambem_entra():
    assert login("ANA@alfa.demo").status_code == 200


def test_senha_errada_e_email_inexistente_dao_o_mesmo_401():
    errada, inexistente = login("ana@alfa.demo", "errada"), login("ninguem@alfa.demo")
    assert_401(errada)
    assert_401(inexistente)
    assert errada.json()["erro"]["mensagem"] == inexistente.json()["erro"]["mensagem"]


def test_me_sem_token_401():
    assert_401(client.get("/me"))


def test_me_com_token_invalido_401():
    assert_401(client.get("/me", headers={"Authorization": "Bearer nao-e-um-jwt"}))


def test_me_com_token_expirado_401(ctx_ana):
    vencido = criar_token(ctx_ana, agora=datetime.now(UTC) - timedelta(days=2))
    assert_401(client.get("/me", headers={"Authorization": f"Bearer {vencido}"}))


def test_entrada_invalida_422_no_formato_padrao():
    r = client.post("/auth/login", json={"email": "ana@alfa.demo"})
    assert r.status_code == 422
    assert r.json()["erro"]["codigo"] == "ENTRADA_INVALIDA"
