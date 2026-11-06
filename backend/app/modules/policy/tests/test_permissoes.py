"""Matriz de perfis do SPEC §6.2."""

import pytest

from app.modules.policy.service import PERMISSOES, Acao, pode

# (ação, analista, gestor, auditor, admin)
MATRIZ = [
    (Acao.CONSULTAR, True, False, False, True),
    (Acao.VER_DOSSIE, True, True, True, True),
    (Acao.EDITAR_CARTEIRA, True, False, False, True),
    (Acao.VER_FILA, True, True, True, True),
    (Acao.VER_PROPRIAS_CONSULTAS, True, False, False, True),
    (Acao.VER_CONSULTAS_TENANT, False, False, True, True),
    (Acao.VER_AUDITORIA, False, False, True, True),
    (Acao.VER_SOCIOS, True, False, True, True),
]


@pytest.mark.parametrize(("acao", "analista", "gestor", "auditor", "admin"), MATRIZ)
def test_matriz_de_perfis(acao, analista, gestor, auditor, admin):
    assert pode("analista", acao) is analista
    assert pode("gestor", acao) is gestor
    assert pode("auditor", acao) is auditor
    assert pode("admin", acao) is admin


def test_toda_acao_tem_regra():
    assert set(PERMISSOES) == set(Acao)
    assert {linha[0] for linha in MATRIZ} == set(Acao)
