from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.contexto import ContextoAcesso
from app.modules.auditoria import service
from app.modules.auditoria.schemas import (
    LIMITE_MAXIMO,
    LIMITE_PADRAO,
    EventoAuditoria,
    VerificacaoCadeiaSaida,
)
from app.modules.policy.service import Acao, exigir

router = APIRouter(tags=["auditoria"])

Auditor = Annotated[ContextoAcesso, Depends(exigir(Acao.VER_AUDITORIA))]


@router.get("/auditoria", response_model=list[EventoAuditoria])
def listar_auditoria(
    ctx: Auditor,
    evento: Annotated[str | None, Query(max_length=40, pattern=r"^[a-z_]+$")] = None,
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO)] = LIMITE_PADRAO,
) -> list[EventoAuditoria]:
    # Só auditor e admin (403 auditado para os demais); a RLS limita ao tenant da sessão.
    return [EventoAuditoria(**e) for e in service.listar(ctx, evento, limite)]


@router.get("/auditoria/verificar", response_model=VerificacaoCadeiaSaida)
def verificar_auditoria(ctx: Auditor) -> VerificacaoCadeiaSaida:
    v = service.verificar(ctx)
    return VerificacaoCadeiaSaida(
        integra=v.integra, n_eventos=v.n_eventos, primeiro_seq_quebrado=v.primeiro_seq_quebrado
    )
