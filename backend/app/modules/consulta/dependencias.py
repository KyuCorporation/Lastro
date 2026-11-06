"""Dependências da rota de consulta, trocáveis nos testes com `app.dependency_overrides`."""

from functools import cache
from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.core.contexto import ContextoAcesso
from app.core.errors import ErroApi
from app.core.limite_taxa import LimitadorJanela
from app.llm.providers import obter_provedor
from app.modules.consulta.service import Ambiente
from app.modules.policy.service import Acao, exigir

CONSULTAS_POR_MINUTO = 30  # contracts/api.md, regras transversais


@cache
def limitador_consultas() -> LimitadorJanela:
    return LimitadorJanela(CONSULTAS_POR_MINUTO, 60.0)


@cache
def _ambiente_padrao() -> Ambiente:
    return Ambiente(provedor=obter_provedor(get_settings()))


def ambiente() -> Ambiente:
    return _ambiente_padrao()


def consultante(
    ctx: Annotated[ContextoAcesso, Depends(exigir(Acao.CONSULTAR))],
    limitador: Annotated[LimitadorJanela, Depends(limitador_consultas)],
) -> ContextoAcesso:
    """Perfil que pode consultar (senão 403 auditado) e dentro do limite por usuário (senão 429)."""
    if not limitador.permitir(ctx.usuario_id):
        raise ErroApi(429, "LIMITE_EXCEDIDO", "Limite de 30 consultas por minuto. Aguarde um pouco.")
    return ctx
