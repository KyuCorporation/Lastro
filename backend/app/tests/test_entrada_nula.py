"""Byte nulo em texto de entrada vira 422, nunca 500 (achado da suíte de ataques, caso A048).

O Postgres não guarda NUL em `text`: sem a validação na borda, a gravação falhava, a API respondia 500 e nem
o registro do erro entrava (a própria linha de erro tinha o NUL).
"""

import pytest

from app.modules.auth.schemas import LoginEntrada
from app.modules.carteiras.schemas import CarteiraEntrada
from app.modules.consulta.schemas import ConsultaEntrada


@pytest.mark.parametrize(
    ("modelo", "dados"),
    [
        (ConsultaEntrada, {"pergunta": "Resumo do CNPJ 99999999000191\x00 em AL"}),
        (LoginEntrada, {"email": "ana@alfa.demo\x00", "senha": "demo123"}),
        (LoginEntrada, {"email": "ana@alfa.demo", "senha": "demo\x00123"}),
        (CarteiraEntrada, {"nome": "a\x00b", "finalidade": "homologacao", "cnpjs": ["11222333000181"]}),
        (CarteiraEntrada, {"nome": "ok", "finalidade": "homologacao", "cnpjs": ["1122233300018\x001"]}),
    ],
)
def test_esquemas_recusam_byte_nulo(modelo, dados):
    with pytest.raises(ValueError, match="caractere nulo"):
        modelo(**dados)


def test_texto_normal_continua_valido():
    assert ConsultaEntrada(pergunta="Resumo do CNPJ 99.999.999/0001-91 ✓").pergunta.endswith("✓")


def test_login_com_byte_nulo_e_422(api):
    r = api.post("/auth/login", json={"email": "ana@alfa.demo\x00", "senha": "demo123"})
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "ENTRADA_INVALIDA"


def test_consulta_com_byte_nulo_e_422(api, autenticar):
    r = api.post(
        "/consultas",
        json={"pergunta": "Resumo\x00 do CNPJ 99999999000191"},
        headers=autenticar("ana@alfa.demo"),
    )
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "ENTRADA_INVALIDA"


def test_carteira_com_byte_nulo_e_422(api, autenticar):
    corpo = {"nome": "T18 \x00", "finalidade": "homologacao", "cnpjs": ["11222333000181"]}
    r = api.post("/carteiras", json=corpo, headers=autenticar("ana@alfa.demo"))
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "ENTRADA_INVALIDA"
