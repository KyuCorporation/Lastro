"""T18, passo 2 da demo: o analista sobe a carteira e recebe a fila priorizada por sinais explicáveis.

Postgres real como lastro_app, sob RLS, com os usuários do seed.
"""

import math
from uuid import uuid4

import pytest

from app.core.db import sessao
from app.modules.carteiras.tests.conftest import F1, F2, F3

CNPJS = ["11.222.333/0001-81", F2, F3, "123", F1]  # F1 repetido com e sem máscara; "123" inválido


def _criar(api, headers, **trocas):
    corpo = {"nome": f"T18 {uuid4().hex[:8]}", "finalidade": "homologacao", "cnpjs": CNPJS, **trocas}
    return api.post("/carteiras", json=corpo, headers=headers)


@pytest.fixture
def carteira(cliente, autenticar) -> dict:
    r = _criar(cliente, autenticar("ana@alfa.demo"))
    assert r.status_code == 201, r.text
    return r.json()


# ------------------------------------------------------------------ POST /carteiras
def test_criar_carteira_normaliza_deduplica_e_devolve_invalidos(carteira):
    assert carteira["n_itens"] == 3
    assert carteira["cnpjs_invalidos"] == ["123"]
    assert carteira["finalidade"] == "homologacao" and carteira["nome"].startswith("T18 ")
    assert set(carteira) == {"id", "nome", "finalidade", "n_itens", "cnpjs_invalidos"}


def test_criacao_fica_na_auditoria_do_tenant(carteira, ctx_caio):
    with sessao(ctx_caio) as conn:
        detalhes = conn.execute(
            "select detalhes from auditoria where evento = 'carteira_criada' and detalhes->>'carteira_id' = %s",
            (carteira["id"],),
        ).fetchone()[0]
    assert detalhes == {
        "carteira_id": carteira["id"],
        "finalidade": "homologacao",
        "n_itens": 3,
        "n_invalidos": 1,
    }


@pytest.mark.parametrize("email", ["gil@alfa.demo", "caio@alfa.demo"])
def test_gestor_e_auditor_nao_criam_carteira(cliente, autenticar, email):
    r = _criar(cliente, autenticar(email))
    assert r.status_code == 403 and r.json()["erro"]["codigo"] == "PERFIL_SEM_PERMISSAO"


def test_admin_cria_carteira(cliente, autenticar):
    assert _criar(cliente, autenticar("admin@alfa.demo"), finalidade="monitoramento").status_code == 201


@pytest.mark.parametrize(
    "trocas",
    [
        {"finalidade": "espionagem"},
        {"cnpjs": []},
        {"nome": "   "},
        {"nome": "x" * 121},
        {"cnpjs": ["1" * 40]},
        {"cnpjs": [F1] * 1001},
    ],
    ids=["finalidade", "sem_cnpjs", "nome_vazio", "nome_longo", "cnpj_longo", "cnpjs_demais"],
)
def test_entrada_invalida_422(cliente, autenticar, trocas):
    r = _criar(cliente, autenticar("ana@alfa.demo"), **trocas)
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "ENTRADA_INVALIDA"


def test_tenant_vem_da_sessao_e_nao_do_corpo(cliente, autenticar):
    """Um tenant_id no corpo é ignorado: a carteira nasce no tenant do token (AGENTS.md §3, regra 3)."""
    r = _criar(cliente, autenticar("ana@alfa.demo"), tenant_id="00000000-0000-0000-0000-00000000be7a")
    assert r.status_code == 201
    bia = cliente.get("/carteiras", headers=autenticar("bia@beta.demo")).json()
    assert r.json()["id"] not in {c["id"] for c in bia}


# ------------------------------------------------------------------ GET /carteiras
@pytest.mark.parametrize("email", ["ana@alfa.demo", "gil@alfa.demo", "caio@alfa.demo", "admin@alfa.demo"])
def test_todos_os_perfis_do_tenant_listam(cliente, autenticar, carteira, email):
    lista = cliente.get("/carteiras", headers=autenticar(email)).json()
    item = next(c for c in lista if c["id"] == carteira["id"])
    assert item["n_itens"] == 3 and item["criada_em"]
    assert set(item) == {"id", "nome", "finalidade", "n_itens", "criada_em"}


def test_outro_tenant_nao_lista(cliente, autenticar, carteira):
    lista = cliente.get("/carteiras", headers=autenticar("bia@beta.demo")).json()
    assert carteira["id"] not in {c["id"] for c in lista}


# ------------------------------------------------------------------ GET /carteiras/{id}/fila
def _fila(api, headers, carteira_id):
    return api.get(f"/carteiras/{carteira_id}/fila", headers=headers)


def test_fila_priorizada_com_sinais_so_das_ufs_do_usuario(cliente, autenticar, carteira):
    r = _fila(cliente, autenticar("ana@alfa.demo"), carteira["id"])
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["carteira"]["id"] == carteira["id"]
    primeiro, *resto = corpo["itens"]

    assert primeiro["cnpj"] == F1 and primeiro["razao_social"] == "FORNECEDOR TESTE UM LTDA"
    assert primeiro["valor_exposto"] == "400000.00"  # C1 + C2 em PE; C4 (AL) não entra para ana
    assert [s["tipo"] for s in primeiro["sinais"]] == ["sancao_direta", "concentracao"]  # forte antes
    assert primeiro["prioridade"] == pytest.approx(13 * math.log10(400001), abs=1e-4)
    for s in primeiro["sinais"]:
        assert set(s) == {"tipo", "gravidade", "explicacao", "evidencias"}

    # F2 e F3 sem sinal visível para ana (o penhasco de F3 é de AL): prioridade 0, sem exposição
    assert {(i["cnpj"], i["prioridade"], i["valor_exposto"], tuple(i["sinais"])) for i in resto} == {
        (F2, 0, "0.00", ()),
        (F3, 0, "0.00", ()),
    }
    assert "em AL" not in r.text  # nenhuma explicação de sinal de AL


def test_admin_com_pe_e_al_ve_o_sinal_e_a_exposicao_de_al(cliente, autenticar, carteira):
    itens = {
        i["cnpj"]: i for i in _fila(cliente, autenticar("admin@alfa.demo"), carteira["id"]).json()["itens"]
    }
    assert itens[F1]["valor_exposto"] == "470000.00"
    assert [s["tipo"] for s in itens[F1]["sinais"]] == ["sancao_direta", "concentracao", "penhasco"]
    assert [s["tipo"] for s in itens[F3]["sinais"]] == ["penhasco"]
    assert itens[F3]["valor_exposto"] == "5000.00"


@pytest.mark.parametrize("email", ["gil@alfa.demo", "caio@alfa.demo"])
def test_gestor_e_auditor_veem_a_fila(cliente, autenticar, carteira, email):
    assert _fila(cliente, autenticar(email), carteira["id"]).status_code == 200


def test_fila_de_outro_tenant_e_404(cliente, autenticar, carteira):
    """IDOR: bia não descobre nem que a carteira existe."""
    r = _fila(cliente, autenticar("bia@beta.demo"), carteira["id"])
    assert r.status_code == 404 and r.json()["erro"]["codigo"] == "NAO_ENCONTRADO"
    assert F1 not in r.text


def test_fila_inexistente_404_e_id_malformado_422(cliente, autenticar):
    ana = autenticar("ana@alfa.demo")
    assert _fila(cliente, ana, uuid4()).status_code == 404
    assert _fila(cliente, ana, "nao-e-uuid").status_code == 422
