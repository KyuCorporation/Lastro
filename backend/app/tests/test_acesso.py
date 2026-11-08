"""Matriz de acesso (SPEC §6.4, T13): os 8 casos obrigatórios.

Roda contra o Postgres real do Compose, conectado como lastro_app (a API) e, só para montar e limpar dados de
teste, como superusuário. Requer os seeds de demo (make seed).

Onde a rota ainda não existe (sinais: T17; busca textual: T19; carteiras e alertas: T18 e T28), o caso é
provado no banco, sob a RLS, com o mesmo contexto de sessão que a API aplica: é a RLS que garante o caso,
e a rota vai ler por ela.
"""

import os
import re
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.main import app
from app.modules.catalogo.tests.conftest import F1, _superusuario

client = TestClient(app)

ROTAS_PUBLICAS = {"/health", "/auth/login"}
GIL_ID = "00000000-0000-0000-0000-0000000000a3"
TENANT_ALFA = UUID("00000000-0000-0000-0000-00000000a1fa")
VENCENDO_PE = "Quais contratos do CNPJ 11.222.333/0001-81 vencem nos próximos 6 meses?"


def conectar() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5)


def token(email: str) -> str:
    r = client.post("/auth/login", json={"email": email, "senha": "demo123"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def cabecalho(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(email)}"}


# ====================================================================== caso 1
def test_caso_1_ana_pergunta_sobre_pe_e_recebe_resposta(api, autenticar):
    r = api.post("/consultas", json={"pergunta": VENCENDO_PE}, headers=autenticar("ana@alfa.demo"))
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["status"] == "respondida"
    assert corpo["citacoes"] and corpo["recibo_id"]
    assert all(c["fonte_id"] for c in corpo["citacoes"])


@pytest.mark.parametrize(
    "pergunta",
    [
        "Quanto o CNPJ 11.222.333/0001-81 recebeu em Alagoas?",
        "Contratos vigentes do CNPJ 11.222.333/0001-81 em AL",
        "Resumo do fornecedor 11222333000181 no estado de Alagoas",
    ],
)
def test_caso_1_ana_pergunta_sobre_al_e_e_negada_sem_vazar_contagem(api, autenticar, pergunta):
    r = api.post("/consultas", json={"pergunta": pergunta}, headers=autenticar("ana@alfa.demo"))
    assert r.status_code == 403
    erro = r.json()["erro"]
    assert erro["codigo"] == "ESCOPO_NEGADO"
    assert erro["mensagem"] == "Você não tem acesso a dados de AL."
    # Nenhum número na resposta: nem contagem, nem valor do que existe em AL (o contrato C4 de 70 mil).
    assert not re.search(r"\d", erro["mensagem"])
    assert "70.000" not in r.text and "TCAT-C4" not in r.text


def test_caso_1_bia_ve_alagoas_e_nunca_pernambuco(api, autenticar):
    r = api.post(
        "/consultas",
        json={"pergunta": "Resumo do fornecedor 11.222.333/0001-81"},
        headers=autenticar("bia@beta.demo"),
    )
    assert r.status_code == 200
    assert "R$ 70.000,00" in r.json()["resposta"]
    assert "450.000" not in r.json()["resposta"]  # soma de PE
    assert {c["id"] for c in r.json()["citacoes"]}  # só linhas de AL (a RLS filtra)


# ====================================================================== caso 2
@pytest.fixture
def dados_do_alfa(api, autenticar, ctx_ana):
    """Uma consulta e um recibo da Ana (pela API), uma carteira com item e um alerta do Cliente Alfa."""
    feita = api.post("/consultas", json={"pergunta": VENCENDO_PE}, headers=autenticar("ana@alfa.demo")).json()
    carteira_id = uuid4()
    with sessao(ctx_ana) as conn:
        conn.execute(
            "insert into carteiras (id, tenant_id, nome, finalidade, criada_por) "
            "values (%s, ctx_tenant(), 'Carteira teste T13', 'homologacao', ctx_usuario())",
            (carteira_id,),
        )
        conn.execute(
            "insert into carteira_itens (carteira_id, tenant_id, fornecedor_cnpj) values (%s, ctx_tenant(), %s)",
            (carteira_id, F1),
        )
        alerta_id = conn.execute(
            "insert into alertas (tenant_id, carteira_id, fornecedor_cnpj) values (ctx_tenant(), %s, %s) returning id",
            (carteira_id, F1),
        ).fetchone()[0]
        auditoria_seq = conn.execute(
            "select max(seq) from auditoria where tenant_id = ctx_tenant()"
        ).fetchone()  # ana não lê auditoria: vem None, o seq é lido como superusuário abaixo
    with _superusuario() as su:
        seq = su.execute("select max(seq) from auditoria where tenant_id = %s", (TENANT_ALFA,)).fetchone()[0]
    assert auditoria_seq == (None,)
    yield {
        "consulta_id": feita["consulta_id"],
        "recibo_id": feita["recibo_id"],
        "carteira_id": carteira_id,
        "alerta_id": alerta_id,
        "auditoria_seq": seq,
    }
    with _superusuario() as su:
        su.execute("delete from alertas where id = %s", (alerta_id,))
        su.execute("delete from carteiras where id = %s", (carteira_id,))


CONSULTAS_POR_ID = {
    "carteiras": "select count(*) from carteiras where id = %(carteira_id)s",
    "carteira_itens": "select count(*) from carteira_itens where carteira_id = %(carteira_id)s",
    "consultas": "select count(*) from consultas where id = %(consulta_id)s",
    "recibos": "select count(*) from recibos where id = %(recibo_id)s",
    "alertas": "select count(*) from alertas where id = %(alerta_id)s",
    "auditoria": "select count(*) from auditoria where seq = %(auditoria_seq)s",
}


@pytest.mark.parametrize("tabela", sorted(CONSULTAS_POR_ID))
def test_caso_2_bia_nao_ve_dado_do_alfa_nem_por_id_direto(dados_do_alfa, ctx_bia, ctx_caio, tabela):
    sql = CONSULTAS_POR_ID[tabela]
    with sessao(ctx_bia) as conn:
        assert conn.execute(sql, dados_do_alfa).fetchone() == (0,)
    with sessao(ctx_caio) as conn:  # controle: o auditor do Alfa vê o mesmo id
        assert conn.execute(sql, dados_do_alfa).fetchone() == (1,)


def test_caso_2_bia_nao_ve_nada_do_alfa_nem_listando(dados_do_alfa, ctx_bia):
    with sessao(ctx_bia) as conn:
        for tabela in ("carteiras", "carteira_itens", "consultas", "recibos", "alertas", "auditoria"):
            alheias = conn.execute(f"select count(*) from {tabela} where tenant_id = %s", (TENANT_ALFA,))
            assert alheias.fetchone() == (0,), tabela


def test_caso_2_idor_pela_api(api, autenticar, dados_do_alfa):
    bia = autenticar("bia@beta.demo")
    recibo = api.get(f"/recibos/{dados_do_alfa['recibo_id']}", headers=bia)
    assert recibo.status_code == 404 and recibo.json()["erro"]["codigo"] == "NAO_ENCONTRADO"

    listadas = api.get("/consultas?limite=200", headers=bia).json()
    assert dados_do_alfa["consulta_id"] not in {c["id"] for c in listadas}

    com_carteira_alheia = api.post(
        "/consultas",
        json={"pergunta": VENCENDO_PE, "carteira_id": str(dados_do_alfa["carteira_id"])},
        headers=bia,
    )
    assert com_carteira_alheia.status_code == 404


def test_caso_2_bia_nao_grava_no_tenant_do_alfa(ctx_bia):
    with pytest.raises(psycopg.errors.InsufficientPrivilege), sessao(ctx_bia) as conn:
        conn.execute(
            "insert into carteiras (tenant_id, nome, finalidade) values (%s, 'invasão', 'homologacao')",
            (TENANT_ALFA,),
        )


# ====================================================================== caso 3
@pytest.fixture
def sinais_por_uf():
    """Um sinal de F1 em PE, um em AL e um nacional (uf nula), gravados como a pipeline gravaria."""
    linhas = [
        ("PE", "penhasco", "atencao"),
        ("AL", "concentracao", "atencao"),
        (None, "sancao_direta", "forte"),
    ]
    with _superusuario() as su:
        ids = [
            su.execute(
                "insert into sinais (fornecedor_cnpj, uf, tipo, gravidade, explicacao, evidencias, versao_regra) "
                "values (%s, %s, %s, %s, 'teste T13', '[]', 'teste-t13') returning id",
                (F1, uf, tipo, gravidade),
            ).fetchone()[0]
            for uf, tipo, gravidade in linhas
        ]
    yield ids
    with _superusuario() as su:
        su.execute("delete from sinais where versao_regra = 'teste-t13'")


def _ufs_dos_sinais(ctx: ContextoAcesso) -> set[str | None]:
    with sessao(ctx) as conn:
        linhas = conn.execute("select uf from sinais where versao_regra = 'teste-t13'").fetchall()
    return {linha[0] for linha in linhas}


def test_caso_3_sinal_de_al_nao_aparece_para_ana(sinais_por_uf, ctx_ana, ctx_bia, ctx_admin):
    assert _ufs_dos_sinais(ctx_ana) == {"PE", None}
    assert _ufs_dos_sinais(ctx_bia) == {"AL", None}
    assert _ufs_dos_sinais(ctx_admin) == {"PE", "AL", None}


# ====================================================================== caso 4
BUSCA_TEXTUAL = """
select uf from contratos
 where objeto_tsv @@ plainto_tsquery('portuguese', %(termo)s) and id_origem like 'TCAT-%%'
"""


def test_caso_4_busca_textual_nao_atravessa_a_uf(dados_catalogo, ctx_ana, ctx_bia):
    """ "Limpeza" existe em contratos de PE e de AL: cada um só acha o da própria UF."""
    with sessao(ctx_ana) as conn:
        ufs_ana = {r[0] for r in conn.execute(BUSCA_TEXTUAL, {"termo": "limpeza tcat"})}
    with sessao(ctx_bia) as conn:
        ufs_bia = {r[0] for r in conn.execute(BUSCA_TEXTUAL, {"termo": "limpeza tcat"})}
    assert ufs_ana == {"PE"}
    assert ufs_bia == {"AL"}


def test_caso_4_busca_textual_sem_contexto_nao_acha_nada(dados_catalogo):
    with sessao(None) as conn:
        assert conn.execute(BUSCA_TEXTUAL, {"termo": "limpeza tcat"}).fetchall() == []


# ====================================================================== caso 5
def negacoes_do_gil(ctx_auditor) -> int:
    sql = "select count(*) from auditoria where usuario_id = %s and evento = 'negado'"
    with sessao(ctx_auditor) as conn:
        return conn.execute(sql, (GIL_ID,)).fetchone()[0]


def test_caso_5_gestor_nao_consulta_e_a_negacao_vai_para_a_auditoria(ctx_caio):
    antes = negacoes_do_gil(ctx_caio)

    r = client.post(
        "/consultas",
        json={"pergunta": "Quanto o fornecedor recebeu?"},
        headers=cabecalho("gil@alfa.demo"),
    )

    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "PERFIL_SEM_PERMISSAO"
    assert negacoes_do_gil(ctx_caio) == antes + 1
    with sessao(ctx_caio) as conn:
        detalhes = conn.execute(
            "select detalhes from auditoria where usuario_id = %s order by seq desc limit 1", (GIL_ID,)
        ).fetchone()[0]
    assert detalhes == {"motivo": "perfil_sem_permissao", "acao": "consultar", "perfil": "gestor"}


def test_caso_5_analista_passa_pela_permissao(api, autenticar):
    r = api.post("/consultas", json={"pergunta": VENCENDO_PE}, headers=autenticar("ana@alfa.demo"))
    assert r.status_code == 200


# ====================================================================== caso 6
def _rotas_protegidas() -> list[tuple[str, str]]:
    """Todas as rotas da API (lidas do OpenAPI, então rota nova entra no teste sozinha), menos as públicas."""
    rotas = []
    for caminho, operacoes in app.openapi()["paths"].items():
        if caminho in ROTAS_PUBLICAS:
            continue
        concreto = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", caminho)
        rotas += [(metodo.upper(), concreto) for metodo in sorted(operacoes)]
    return rotas


def test_caso_6_existem_rotas_protegidas():
    rotas = _rotas_protegidas()
    for esperada in [("POST", "/consultas"), ("GET", "/consultas"), ("GET", "/me")]:
        assert esperada in rotas
    assert ("GET", "/recibos/00000000-0000-0000-0000-000000000000") in rotas


@pytest.mark.parametrize(("metodo", "caminho"), _rotas_protegidas())
def test_caso_6_sem_token_401_em_tudo(metodo, caminho):
    r = client.request(metodo, caminho, json={})
    assert r.status_code == 401
    assert r.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


@pytest.mark.parametrize(("metodo", "caminho"), _rotas_protegidas())
def test_caso_6_token_adulterado_tambem_401(metodo, caminho):
    cabeca, corpo, assinatura = token("ana@alfa.demo").split(".")
    adulterado = f"{cabeca}.{corpo}.{assinatura[::-1]}"
    r = client.request(metodo, caminho, json={}, headers={"Authorization": f"Bearer {adulterado}"})
    assert r.status_code == 401


@pytest.mark.parametrize("caminho", sorted(ROTAS_PUBLICAS))
def test_caso_6_rotas_publicas_nao_pedem_token(caminho):
    metodo = "POST" if caminho == "/auth/login" else "GET"
    r = client.request(metodo, caminho, json={"email": "ana@alfa.demo", "senha": "demo123"})
    assert r.status_code == 200


# ====================================================================== caso 7
def test_caso_7_sem_contexto_nada_e_visivel():
    """Conexão como lastro_app sem set_config: select count(*) from contratos retorna 0."""
    with conectar() as conn:
        assert conn.execute("select current_user").fetchone() == ("lastro_app",)
        assert conn.execute("select count(*) from contratos").fetchone() == (0,)


@pytest.mark.parametrize(
    "tabela",
    [
        "contratos",
        "pagamentos",
        "sinais",
        "consultas",
        "recibos",
        "auditoria",
        "carteiras",
        "alertas",
        "usuarios",
    ],
)
def test_caso_7_sem_contexto_nenhuma_tabela_com_rls_mostra_linha(tabela):
    with conectar() as conn:
        assert conn.execute(f"select count(*) from {tabela}").fetchone() == (0,)


def test_caso_7_lastro_app_nao_ignora_a_rls():
    with conectar() as conn:
        papel = conn.execute(
            "select rolsuper, rolbypassrls from pg_roles where rolname = current_user"
        ).fetchone()
    assert papel == (False, False)


# ====================================================================== caso 8
MUDANCAS_PROIBIDAS = [
    "update recibos set hash = repeat('0', 64)",
    "delete from recibos",
    "update auditoria set evento = 'adulterado'",
    "delete from auditoria",
    "truncate recibos",
    "truncate auditoria",
]


@pytest.mark.parametrize("sql", MUDANCAS_PROIBIDAS)
def test_caso_8_lastro_app_nao_altera_nem_apaga_auditoria_e_recibos(ctx_admin, sql):
    with pytest.raises(psycopg.errors.InsufficientPrivilege), sessao(ctx_admin) as conn:
        conn.execute(sql)


def test_caso_8_recibo_gravado_continua_igual(api, autenticar, ctx_ana):
    """Depois das tentativas, o recibo e o hash continuam os mesmos (o banco recusou tudo)."""
    feita = api.post("/consultas", json={"pergunta": VENCENDO_PE}, headers=autenticar("ana@alfa.demo")).json()
    with sessao(ctx_ana) as conn:
        antes = conn.execute(
            "select hash, conteudo from recibos where id = %s", (feita["recibo_id"],)
        ).fetchone()
    for sql in ("update recibos set hash = repeat('0', 64)", "delete from recibos"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege), sessao(ctx_ana) as conn:
            conn.execute(sql)
    with sessao(ctx_ana) as conn:
        depois = conn.execute(
            "select hash, conteudo from recibos where id = %s", (feita["recibo_id"],)
        ).fetchone()
    assert depois == antes
