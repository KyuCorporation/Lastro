"""GET /alertas: só os do tenant, e o sinal só quando a UF dele está no escopo de quem lê."""

from collections.abc import Iterator

import pytest

from app.conftest import TENANT_ALFA
from app.modules.carteiras.tests.conftest import F1, VERSAO
from app.modules.catalogo.tests.conftest import _superusuario


@pytest.fixture
def alertas(cliente) -> Iterator[dict[str, str]]:
    """Carteira do Alfa com dois alertas de F1: um do sinal de PE (aberto) e um do sinal de AL (visto)."""
    with _superusuario() as su:
        carteira = su.execute(
            "insert into carteiras (tenant_id, nome, finalidade) values (%s, 'T18 alertas', 'monitoramento') "
            "returning id::text",
            (TENANT_ALFA,),
        ).fetchone()[0]
        sinal = {
            uf: su.execute(
                "select id::text from sinais where fornecedor_cnpj = %s and uf = %s and versao_regra = %s",
                (F1, uf, VERSAO),
            ).fetchone()[0]
            for uf in ("PE", "AL")
        }
        ids = {}
        for uf, status in (("PE", "aberto"), ("AL", "visto")):
            ids[uf] = su.execute(
                "insert into alertas (tenant_id, carteira_id, fornecedor_cnpj, sinal_id, status) "
                "values (%s, %s, %s, %s, %s) returning id::text",
                (TENANT_ALFA, carteira, F1, sinal[uf], status),
            ).fetchone()[0]
    yield {"carteira": carteira, **ids}
    with _superusuario() as su:
        su.execute("delete from alertas where carteira_id = %s", (carteira,))
        su.execute("delete from carteiras where id = %s", (carteira,))


def _por_id(r) -> dict[str, dict]:
    assert r.status_code == 200, r.text
    return {a["id"]: a for a in r.json()}


def test_analista_ve_os_alertas_do_tenant_com_sinal_so_da_propria_uf(cliente, autenticar, alertas):
    vistos = _por_id(cliente.get("/alertas", headers=autenticar("ana@alfa.demo")))
    pe, al = vistos[alertas["PE"]], vistos[alertas["AL"]]
    assert set(pe) == {"id", "carteira_id", "cnpj", "sinal", "status", "criado_em"}
    assert pe["cnpj"] == F1 and pe["carteira_id"] == alertas["carteira"] and pe["status"] == "aberto"
    assert pe["sinal"]["tipo"] == "concentracao" and pe["sinal"]["uf"] == "PE"
    assert al["sinal"] is None  # sinal de AL: a ana (PE) não vê o conteúdo


def test_admin_com_al_ve_o_sinal_de_al(cliente, autenticar, alertas):
    vistos = _por_id(cliente.get("/alertas", headers=autenticar("admin@alfa.demo")))
    assert vistos[alertas["AL"]]["sinal"]["uf"] == "AL"


def test_filtro_por_status(cliente, autenticar, alertas):
    vistos = _por_id(cliente.get("/alertas?status=visto", headers=autenticar("gil@alfa.demo")))
    assert alertas["AL"] in vistos and alertas["PE"] not in vistos
    assert {a["status"] for a in vistos.values()} == {"visto"}


def test_outro_tenant_nao_ve(cliente, autenticar, alertas):
    vistos = _por_id(cliente.get("/alertas", headers=autenticar("bia@beta.demo")))
    assert not ({alertas["PE"], alertas["AL"]} & set(vistos))


def test_status_invalido_422(cliente, autenticar):
    r = cliente.get("/alertas?status=apagado", headers=autenticar("ana@alfa.demo"))
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "ENTRADA_INVALIDA"
