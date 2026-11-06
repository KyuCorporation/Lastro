from typing import Annotated

from fastapi import APIRouter, Query

from app.modules.auth.dependencias import Contexto
from app.modules.fontes import service
from app.modules.fontes.schemas import ExecucaoSaida, FonteSaida

router = APIRouter(tags=["fontes"])


@router.get("/fontes", response_model=list[FonteSaida])
def listar_fontes(ctx: Contexto) -> list[FonteSaida]:
    return service.listar_fontes(ctx)


@router.get("/fontes/execucoes", response_model=list[ExecucaoSaida])
def listar_execucoes(
    ctx: Contexto,
    fonte_id: Annotated[str | None, Query(max_length=40, pattern=r"^[a-z_]+$")] = None,
) -> list[ExecucaoSaida]:
    return service.listar_execucoes(ctx, fonte_id)
