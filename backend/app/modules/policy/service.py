"""Permissão por perfil (SPEC §6.2).

O escopo de UF e de tenant é aplicado pela RLS no banco. Aqui fica só a pergunta "este perfil pode fazer esta
ação?". Toda negação é gravada na auditoria antes de responder 403 (contracts/api.md, regras transversais).
"""

from collections.abc import Callable
from enum import StrEnum

from app.core.contexto import ContextoAcesso, Perfil
from app.core.errors import ErroApi
from app.modules.auditoria import service as auditoria
from app.modules.auth.dependencias import Contexto


class Acao(StrEnum):
    CONSULTAR = "consultar"
    VER_DOSSIE = "ver_dossie"
    EDITAR_CARTEIRA = "editar_carteira"
    VER_FILA = "ver_fila"
    VER_PROPRIAS_CONSULTAS = "ver_proprias_consultas"
    VER_CONSULTAS_TENANT = "ver_consultas_tenant"
    VER_AUDITORIA = "ver_auditoria"
    VER_SOCIOS = "ver_socios"


TODOS: frozenset[Perfil] = frozenset({"analista", "gestor", "auditor", "admin"})

PERMISSOES: dict[Acao, frozenset[Perfil]] = {
    Acao.CONSULTAR: frozenset({"analista", "admin"}),
    Acao.VER_DOSSIE: TODOS,
    Acao.EDITAR_CARTEIRA: frozenset({"analista", "admin"}),
    Acao.VER_FILA: TODOS,
    Acao.VER_PROPRIAS_CONSULTAS: frozenset({"analista", "admin"}),
    Acao.VER_CONSULTAS_TENANT: frozenset({"auditor", "admin"}),
    Acao.VER_AUDITORIA: frozenset({"auditor", "admin"}),
    Acao.VER_SOCIOS: frozenset({"analista", "auditor", "admin"}),
}


def pode(perfil: Perfil, acao: Acao) -> bool:
    return perfil in PERMISSOES[acao]


def exigir(acao: Acao) -> Callable[[ContextoAcesso], ContextoAcesso]:
    """Dependência de rota: devolve o contexto se o perfil pode a ação; senão audita e responde 403."""

    def dependencia(ctx: Contexto) -> ContextoAcesso:
        if pode(ctx.perfil, acao):
            return ctx
        auditoria.registrar(
            ctx, "negado", {"motivo": "perfil_sem_permissao", "acao": acao.value, "perfil": ctx.perfil}
        )
        raise ErroApi(403, "PERFIL_SEM_PERMISSAO", "Seu perfil não tem permissão para esta ação.")

    return dependencia
