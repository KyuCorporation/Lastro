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


# ===================== geração por evento (I7, T28) =====================
@pytest.fixture
def carteira_da_ana(cliente, autenticar) -> Iterator[str]:
    """Carteira do Alfa com F1, criada pela API (ana, PE). Sai junto com os alertas que gerou."""
    r = cliente.post(
        "/carteiras",
        json={"nome": "T18 alertas por evento", "finalidade": "monitoramento", "cnpjs": [F1]},
        headers=autenticar("ana@alfa.demo"),
    )
    assert r.status_code == 201, r.text
    carteira = r.json()["id"]
    yield carteira
    with _superusuario() as su:
        su.execute("delete from alertas where carteira_id = %s", (carteira,))
        su.execute("delete from carteiras where id = %s", (carteira,))


def _da_carteira(cliente, autenticar, email: str, carteira: str) -> list[dict]:
    r = cliente.get("/alertas", headers=autenticar(email))
    assert r.status_code == 200, r.text
    return [a for a in r.json() if a["carteira_id"] == carteira]


def test_criar_carteira_gera_alerta_aberto_para_cada_sinal_visivel(cliente, autenticar, carteira_da_ana):
    alertas = _da_carteira(cliente, autenticar, "ana@alfa.demo", carteira_da_ana)
    tipos = sorted((a["sinal"]["tipo"], a["sinal"]["uf"]) for a in alertas)
    assert tipos == [("concentracao", "PE"), ("sancao_direta", None)]  # o de AL fica fora: ana é de PE
    assert {a["status"] for a in alertas} == {"aberto"} and {a["cnpj"] for a in alertas} == {F1}


def test_abrir_a_fila_de_novo_nao_duplica(cliente, autenticar, carteira_da_ana):
    for _ in range(2):
        assert (
            cliente.get(f"/carteiras/{carteira_da_ana}/fila", headers=autenticar("ana@alfa.demo")).status_code
            == 200
        )
    assert len(_da_carteira(cliente, autenticar, "ana@alfa.demo", carteira_da_ana)) == 2


def test_fila_aberta_por_quem_tem_al_gera_o_de_al_sem_mostrar_a_ana(cliente, autenticar, carteira_da_ana):
    assert (
        cliente.get(f"/carteiras/{carteira_da_ana}/fila", headers=autenticar("admin@alfa.demo")).status_code
        == 200
    )
    do_admin = _da_carteira(cliente, autenticar, "admin@alfa.demo", carteira_da_ana)
    assert ("penhasco", "AL") in {(a["sinal"]["tipo"], a["sinal"]["uf"]) for a in do_admin}
    da_ana = _da_carteira(cliente, autenticar, "ana@alfa.demo", carteira_da_ana)
    assert len(da_ana) == 3
    assert all(a["sinal"] is None or a["sinal"]["uf"] != "AL" for a in da_ana)


def test_alerta_de_outro_tenant_nao_aparece(cliente, autenticar, carteira_da_ana):
    assert _da_carteira(cliente, autenticar, "bia@beta.demo", carteira_da_ana) == []


def test_sinal_que_deixou_de_valer_some_mas_o_alerta_guarda_o_que_ele_dizia(
    cliente, autenticar, carteira_da_ana
):
    with _superusuario() as su:
        sinal = su.execute(
            "insert into sinais (fornecedor_cnpj, uf, tipo, gravidade, valor, explicacao, evidencias, versao_regra) "
            "values (%s, 'PE', 'penhasco', 'atencao', 1, 'Sinal temporário do teste.', '[]'::jsonb, %s) "
            "returning id::text",
            (F1, VERSAO),
        ).fetchone()[0]
    try:
        assert (
            cliente.get(f"/carteiras/{carteira_da_ana}/fila", headers=autenticar("ana@alfa.demo")).status_code
            == 200
        )
        with _superusuario() as su:
            su.execute("delete from sinais where id = %s", (sinal,))  # o que a pipeline faz com sinal vencido
        (alerta,) = [
            a
            for a in _da_carteira(cliente, autenticar, "ana@alfa.demo", carteira_da_ana)
            if a["sinal"] and a["sinal"]["tipo"] == "penhasco"
        ]
        assert alerta["sinal"]["id"] is None
        assert alerta["sinal"]["explicacao"] == "Sinal temporário do teste." and alerta["sinal"]["uf"] == "PE"
    finally:
        with _superusuario() as su:
            su.execute("delete from sinais where id = %s", (sinal,))
