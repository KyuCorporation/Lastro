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
    settings = get_settings()
    return Ambiente(provedor=obter_provedor(settings), timeout_s=settings.llm_timeout_seconds)


def ambiente() -> Ambiente:
    return _ambiente_padrao()


def consultante(
    ctx: Annotated[ContextoAcesso, Depends(exigir(Acao.CONSULTAR))],
    limitador: Annotated[LimitadorJanela, Depends(limitador_consultas)],
) -> ContextoAcesso:
    """Perfil que pode consultar (senão 403 auditado) e dentro do limite por usuário (senão 429)."""
    if not limitador.permitir(ctx.usuario_id):
        espera = limitador.espera_s(ctx.usuario_id)
        raise ErroApi(
            429,
            "LIMITE_EXCEDIDO",
            f"Limite de {CONSULTAS_POR_MINUTO} consultas por minuto. Tente de novo em {espera} s.",
            {"Retry-After": str(espera)},
        )
    return ctx
