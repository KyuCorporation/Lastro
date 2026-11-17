from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.contexto import ContextoAcesso
from app.modules.alertas import service
from app.modules.alertas.schemas import AlertaAtualizacao, AlertaAtualizado, AlertaSaida, StatusAlerta
from app.modules.auth.dependencias import Contexto
from app.modules.policy.service import Acao, exigir

router = APIRouter(tags=["alertas"])


@router.get("/alertas", response_model=list[AlertaSaida])
def listar_alertas(ctx: Contexto, status: StatusAlerta | None = None) -> list[AlertaSaida]:
    # Todos os perfis veem os alertas do próprio tenant; a RLS esconde os dos outros.
    return service.listar(ctx, status)


@router.patch("/alertas/{alerta_id}", response_model=AlertaAtualizado)
def atualizar_alerta(
    alerta_id: UUID,
    entrada: AlertaAtualizacao,
    ctx: Annotated[ContextoAcesso, Depends(exigir(Acao.ATUALIZAR_ALERTA))],
) -> AlertaAtualizado:
    return service.atualizar(ctx, alerta_id, entrada)
