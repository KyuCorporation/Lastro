"""GET /fontes e GET /fontes/execucoes: tela de fontes com a execução mais recente de cada fonte."""

from collections.abc import Iterator

import pytest

from app.modules.catalogo.tests.conftest import _superusuario

ERRO_LONGO = "FonteIndisponivel: " + "x" * 2000


@pytest.fixture
def execucoes() -> Iterator[tuple[str, str]]:
    """Duas execuções da fonte sintética: uma antiga que falhou e uma recente ok."""
    with _superusuario() as su:
        antiga = su.execute(
            "insert into execucoes_ingestao (fonte_id, iniciada_em, finalizada_em, status, registros_lidos, erro) "
            "values ('demo_sintetico', now() - interval '2 days', now() - interval '2 days', 'falhou', 0, %s) "
            "returning id::text",
            (ERRO_LONGO,),
        ).fetchone()[0]
        recente = su.execute(
            "insert into execucoes_ingestao (fonte_id, iniciada_em, finalizada_em, status, registros_lidos, "
            "registros_novos, registros_descartados) values ('demo_sintetico', now() + interval '1 day', "
            "now() + interval '1 day', 'ok', 9, 7, 2) returning id::text"
        ).fetchone()[0]
    yield antiga, recente
    with _superusuario() as su:
        su.execute("delete from execucoes_ingestao where id in (%s, %s)", (antiga, recente))


@pytest.mark.parametrize("email", ["ana@alfa.demo", "gil@alfa.demo", "caio@alfa.demo", "bia@beta.demo"])
def test_todos_os_perfis_veem_as_fontes_com_a_ultima_execucao(api, autenticar, execucoes, email):
    r = api.get("/fontes", headers=autenticar(email))
    assert r.status_code == 200
    fontes = {f["id"]: f for f in r.json()}
    assert {"pe_portal", "pncp", "ceis", "cnep", "demo_sintetico"} <= set(fontes)
    sintetica = fontes["demo_sintetico"]
    assert sintetica["tipo"] == "sintetico" and sintetica["nome"]
    assert sintetica["ultima_execucao"]["id"] == execucoes[1]
    assert set(sintetica["ultima_execucao"]) == {"id", "status", "finalizada_em", "registros_novos"}
    assert (
        sintetica["ultima_execucao"]["status"] == "ok"
        and sintetica["ultima_execucao"]["registros_novos"] == 7
    )


def test_fonte_sem_execucao_vem_com_ultima_execucao_nula(api, autenticar):
    fontes = {f["id"]: f for f in api.get("/fontes", headers=autenticar("ana@alfa.demo")).json()}
    assert fontes["receita_qsa"]["ultima_execucao"] is None  # quadro societário (N3) nunca rodou


def test_execucoes_filtradas_por_fonte_mais_recente_primeiro(api, autenticar, execucoes):
    r = api.get("/fontes/execucoes?fonte_id=demo_sintetico", headers=autenticar("gil@alfa.demo"))
    assert r.status_code == 200
    lista = r.json()
    assert [e["id"] for e in lista[:2]] == [execucoes[1], execucoes[0]]
    assert {e["fonte_id"] for e in lista} == {"demo_sintetico"}
    assert set(lista[0]) == {
        "id",
        "fonte_id",
        "status",
        "iniciada_em",
        "finalizada_em",
        "registros_lidos",
        "registros_novos",
        "registros_descartados",
        "erro",
    }
    assert lista[1]["status"] == "falhou" and len(lista[1]["erro"]) == 500  # erro longo cortado


def test_execucoes_sem_filtro_e_fonte_desconhecida(api, autenticar, execucoes):
    ana = autenticar("ana@alfa.demo")
    assert len(api.get("/fontes/execucoes", headers=ana).json()) >= 2
    assert api.get("/fontes/execucoes?fonte_id=inexistente", headers=ana).json() == []
    assert api.get("/fontes/execucoes?fonte_id=x';drop", headers=ana).status_code == 422
