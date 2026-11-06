"""T16: GET /auditoria e GET /auditoria/verificar.

Critério de aceite: alterar a cadeia no banco (como superusuário) faz a verificação acusar o primeiro elo quebrado.
O superusuário só aparece para simular a adulteração; a API nunca o usa.
"""

from collections.abc import Iterator

import psycopg
import pytest

from app.conftest import TENANT_ALFA
from app.core.db import parametros_contexto
from app.modules.auditoria import service
from app.modules.catalogo.tests.conftest import _superusuario


@pytest.fixture
def evento_alfa(api, autenticar) -> int:
    """Gera um evento novo na trilha do Alfa (uma negação de escopo) e devolve o seq dele."""
    api.post(
        "/consultas",
        json={"pergunta": "Resumo do CNPJ 11.222.333/0001-81 em Alagoas"},
        headers=autenticar("ana@alfa.demo"),
    )
    with _superusuario() as su:
        return su.execute("select max(seq) from auditoria where tenant_id = %s", (TENANT_ALFA,)).fetchone()[0]


# ------------------------------------------------------------------ GET /auditoria
def test_auditor_lista_a_trilha_do_tenant(api, autenticar, evento_alfa):
    r = api.get("/auditoria", headers=autenticar("caio@alfa.demo"))
    assert r.status_code == 200
    eventos = r.json()
    assert eventos[0]["seq"] == evento_alfa  # mais recente primeiro
    assert set(eventos[0]) == {"seq", "usuario_id", "evento", "detalhes", "criado_em", "hash"}
    assert [e["seq"] for e in eventos] == sorted((e["seq"] for e in eventos), reverse=True)


def test_filtro_por_evento_e_limite(api, autenticar, evento_alfa):
    r = api.get("/auditoria?evento=negado&limite=3", headers=autenticar("admin@alfa.demo"))
    assert r.status_code == 200
    assert 1 <= len(r.json()) <= 3 and {e["evento"] for e in r.json()} == {"negado"}


def test_admin_de_um_tenant_nao_ve_o_outro(api, autenticar):
    api.post(
        "/consultas",
        json={"pergunta": "Resumo do CNPJ 11.222.333/0001-81 em Pernambuco"},
        headers=autenticar("bia@beta.demo"),
    )  # gera evento no Beta
    with _superusuario() as su:
        seqs_beta = {
            s
            for (s,) in su.execute(
                "select seq from auditoria where tenant_id <> %s", (TENANT_ALFA,)
            ).fetchall()
        }
    vistos = {
        e["seq"] for e in api.get("/auditoria?limite=500", headers=autenticar("admin@alfa.demo")).json()
    }
    assert seqs_beta and not (vistos & seqs_beta)


@pytest.mark.parametrize("email", ["ana@alfa.demo", "gil@alfa.demo", "bia@beta.demo"])
@pytest.mark.parametrize("rota", ["/auditoria", "/auditoria/verificar"])
def test_quem_nao_e_auditor_recebe_403_auditado(api, autenticar, email, rota):
    with _superusuario() as su:
        antes = su.execute("select coalesce(max(seq), 0) from auditoria").fetchone()[0]
    r = api.get(rota, headers=autenticar(email))
    assert r.status_code == 403 and r.json()["erro"]["codigo"] == "PERFIL_SEM_PERMISSAO"
    with _superusuario() as su:
        detalhes = su.execute(
            "select detalhes from auditoria where seq > %s and evento = 'negado' order by seq desc limit 1",
            (antes,),
        ).fetchone()[0]
    assert detalhes["acao"] == "ver_auditoria"


@pytest.mark.parametrize("consulta", ["evento=DROP%20TABLE", "limite=0", "limite=501"])
def test_parametros_invalidos_422(api, autenticar, consulta):
    assert api.get(f"/auditoria?{consulta}", headers=autenticar("caio@alfa.demo")).status_code == 422


# ------------------------------------------------------------------ GET /auditoria/verificar
def test_cadeia_integra(api, autenticar, evento_alfa):
    r = api.get("/auditoria/verificar", headers=autenticar("caio@alfa.demo"))
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["integra"] is True and corpo["primeiro_seq_quebrado"] is None and corpo["n_eventos"] > 0


@pytest.fixture
def restaurar_evento(evento_alfa) -> Iterator[int]:
    with _superusuario() as su:
        detalhes, hash_ = su.execute(
            "select detalhes::text, hash from auditoria where seq = %s", (evento_alfa,)
        ).fetchone()
    yield evento_alfa
    with _superusuario() as su:
        su.execute(
            "update auditoria set detalhes = %s::jsonb, hash = %s where seq = %s",
            (detalhes, hash_, evento_alfa),
        )


@pytest.mark.parametrize(
    "adulteracao",
    [
        "update auditoria set detalhes = jsonb_set(detalhes, '{motivo}', '\"apagado\"') where seq = %s",
        "update auditoria set hash = repeat('f', 64) where seq = %s",
    ],
    ids=["detalhes", "hash"],
)
def test_adulterar_um_evento_quebra_a_cadeia_nele(api, autenticar, restaurar_evento, adulteracao):
    with _superusuario() as su:
        assert su.execute(adulteracao, (restaurar_evento,)).rowcount == 1
    corpo = api.get("/auditoria/verificar", headers=autenticar("caio@alfa.demo")).json()
    assert corpo["integra"] is False
    assert corpo["primeiro_seq_quebrado"] == restaurar_evento


def _verificar_como_auditor(su: psycopg.Connection, ctx) -> service.VerificacaoCadeia:
    """Roda a verificação como lastro_app com o contexto do auditor, dentro da transação do superusuário."""
    su.execute("set local role lastro_app")
    su.execute(
        "select set_config('app.tenant_id', %(tenant_id)s, true), set_config('app.usuario_id', %(usuario_id)s, true),"
        " set_config('app.perfil', %(perfil)s, true), set_config('app.ufs', %(ufs)s, true)",
        parametros_contexto(ctx, 5000),
    )
    return service.verificar_em(su)


def test_evento_apagado_no_meio_quebra_o_seguinte(api, autenticar, ctx_caio, evento_alfa):
    """Apagar não deixa rastro na linha, mas o evento seguinte aponta para um hash que sumiu."""
    api.post(
        "/consultas",
        json={"pergunta": "Resumo do CNPJ 11.222.333/0001-81 em Sergipe"},
        headers=autenticar("ana@alfa.demo"),
    )
    with _superusuario() as su, su.transaction(force_rollback=True):
        seguinte = su.execute(
            "select min(seq) from auditoria where tenant_id = %s and seq > %s", (TENANT_ALFA, evento_alfa)
        ).fetchone()[0]
        su.execute("delete from auditoria where seq = %s", (evento_alfa,))
        resultado = _verificar_como_auditor(su, ctx_caio)
    assert resultado.integra is False and resultado.primeiro_seq_quebrado == seguinte
