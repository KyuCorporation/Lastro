from uuid import UUID

from fastapi import APIRouter

from app.modules.auth.dependencias import Contexto
from app.modules.recibos import service
from app.modules.recibos.schemas import ReciboSaida

router = APIRouter(tags=["recibos"])


@router.get("/recibos/{recibo_id}", response_model=ReciboSaida)
def obter_recibo(recibo_id: UUID, ctx: Contexto) -> ReciboSaida:
    # Quem pode ver (dono, auditor, admin do tenant) é decidido pela RLS; o resto recebe 404.
    return ReciboSaida(**service.obter(ctx, recibo_id))
