"""T15: GET /recibos/{id}/verificar recalcula o hash canônico e compara com o gravado.

Critério de aceite: alterar uma linha do recibo no banco (como superusuário) faz o selo virar "alterado".
O superusuário só aparece aqui para simular a adulteração; a API nunca o usa.
"""

from collections.abc import Iterator

import pytest

from app.modules.catalogo.tests.conftest import _superusuario
from app.modules.recibos.canonico import hash_recibo
from app.modules.recibos.service import verificar_conteudo

VENCENDO = "Quais contratos do CNPJ 11.222.333/0001-81 vencem nos próximos 6 meses?"


# ------------------------------------------------------------------ função pura
def test_conteudo_intacto_e_integro():
    conteudo = {"versao": "v1", "resposta_final": "ok", "linhas": [{"id": "1"}]}
    resultado = verificar_conteudo(conteudo, hash_recibo(conteudo))
    assert resultado.integro
    assert resultado.hash_gravado == resultado.hash_recalculado


def test_qualquer_campo_alterado_quebra_a_integridade():
    original = {"versao": "v1", "resposta_final": "Vence R$ 100.000,00.", "linhas": [{"id": "1"}]}
    gravado = hash_recibo(original)
    for alterado in (
        {**original, "resposta_final": "Vence R$ 900.000,00."},
        {**original, "linhas": []},
        {**original, "extra": True},
    ):
        resultado = verificar_conteudo(alterado, gravado)
        assert not resultado.integro
        assert resultado.hash_gravado == gravado and resultado.hash_recalculado != gravado


def test_hash_gravado_com_espacos_do_char64_ainda_compara():
    conteudo = {"versao": "v1"}
    assert verificar_conteudo(conteudo, f" {hash_recibo(conteudo).upper()} ").integro


# ------------------------------------------------------------------ pela API, banco real
@pytest.fixture
def recibo_da_ana(api, autenticar) -> Iterator[str]:
    """Recibo novo da Ana. No fim, devolve conteúdo e hash originais (o teste pode ter adulterado)."""
    feita = api.post("/consultas", json={"pergunta": VENCENDO}, headers=autenticar("ana@alfa.demo")).json()
    recibo_id = feita["recibo_id"]
    assert recibo_id
    with _superusuario() as su:
        conteudo, hash_ = su.execute(
            "select conteudo::text, hash from recibos where id = %s", (recibo_id,)
        ).fetchone()
    yield recibo_id
    with _superusuario() as su:
        su.execute(
            "update recibos set conteudo = %s::jsonb, hash = %s where id = %s", (conteudo, hash_, recibo_id)
        )


def _verificar(api, headers, recibo_id: str):
    return api.get(f"/recibos/{recibo_id}/verificar", headers=headers)


def test_recibo_recem_gravado_e_integro(api, autenticar, recibo_da_ana):
    r = _verificar(api, autenticar("ana@alfa.demo"), recibo_da_ana)
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == {"integro", "hash_gravado", "hash_recalculado"}
    assert corpo["integro"] is True
    assert corpo["hash_gravado"] == corpo["hash_recalculado"]
    assert len(corpo["hash_gravado"]) == 64


@pytest.mark.parametrize(
    "adulteracao",
    [
        # resposta trocada: o número que o usuário leu não é mais o que foi entregue
        (
            "update recibos set conteudo = jsonb_set(conteudo, '{resposta_final}', '\"Vence R$ 999,00.\"') "
            "where id = %s"
        ),
        # uma linha citada some do recibo
        "update recibos set conteudo = jsonb_set(conteudo, '{linhas}', '[]') where id = %s",
        # escopo reescrito para parecer que a consulta valeu para outra UF
        (
            "update recibos set conteudo = jsonb_set(conteudo, '{ufs_autorizadas}', '[\"AL\", \"PE\"]') "
            "where id = %s"
        ),
        # o hash gravado é trocado em vez do conteúdo
        "update recibos set hash = repeat('0', 64) where id = %s",
    ],
    ids=["resposta", "linhas", "escopo", "hash"],
)
def test_alterar_o_recibo_no_banco_vira_alterado(api, autenticar, recibo_da_ana, adulteracao):
    cabecalho = autenticar("ana@alfa.demo")
    antes = _verificar(api, cabecalho, recibo_da_ana).json()
    with _superusuario() as su:
        assert su.execute(adulteracao, (recibo_da_ana,)).rowcount == 1

    depois = _verificar(api, cabecalho, recibo_da_ana).json()
    assert antes["integro"] is True
    assert depois["integro"] is False
    assert depois["hash_gravado"] != depois["hash_recalculado"]


def test_auditor_e_admin_verificam_recibo_do_tenant(api, autenticar, recibo_da_ana):
    for email in ("caio@alfa.demo", "admin@alfa.demo"):
        r = _verificar(api, autenticar(email), recibo_da_ana)
        assert r.status_code == 200 and r.json()["integro"] is True


@pytest.mark.parametrize("email", ["bia@beta.demo", "gil@alfa.demo"])
def test_quem_nao_ve_o_recibo_recebe_404(api, autenticar, recibo_da_ana, email):
    """Outro tenant (IDOR) e gestor que não é dono: 404, igual a inexistente, e sem hash na resposta."""
    r = _verificar(api, autenticar(email), recibo_da_ana)
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "NAO_ENCONTRADO"
    assert "hash" not in r.text


def test_recibo_inexistente_404(api, autenticar):
    r = _verificar(api, autenticar("ana@alfa.demo"), "00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404 and r.json()["erro"]["codigo"] == "NAO_ENCONTRADO"


def test_id_malformado_422(api, autenticar):
    r = _verificar(api, autenticar("ana@alfa.demo"), "nao-e-uuid")
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "ENTRADA_INVALIDA"
