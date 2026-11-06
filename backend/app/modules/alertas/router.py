from fastapi import APIRouter

from app.modules.alertas import service
from app.modules.alertas.schemas import AlertaSaida, StatusAlerta
from app.modules.auth.dependencias import Contexto

router = APIRouter(tags=["alertas"])


@router.get("/alertas", response_model=list[AlertaSaida])
def listar_alertas(ctx: Contexto, status: StatusAlerta | None = None) -> list[AlertaSaida]:
    # Todos os perfis veem os alertas do próprio tenant; a RLS esconde os dos outros.
    return service.listar(ctx, status)
