from uuid import UUID

from fastapi import APIRouter

from app.modules.auth.dependencias import Contexto
from app.modules.recibos import service
from app.modules.recibos.schemas import ReciboSaida, VerificacaoSaida

router = APIRouter(tags=["recibos"])


@router.get("/recibos/{recibo_id}", response_model=ReciboSaida)
def obter_recibo(recibo_id: UUID, ctx: Contexto) -> ReciboSaida:
    # Quem pode ver (dono, auditor, admin do tenant) é decidido pela RLS; o resto recebe 404.
    return ReciboSaida(**service.obter(ctx, recibo_id))


@router.get("/recibos/{recibo_id}/verificar", response_model=VerificacaoSaida)
def verificar_recibo(recibo_id: UUID, ctx: Contexto) -> VerificacaoSaida:
    # Mesma visibilidade do GET /recibos/{id}: quem não vê o recibo recebe 404, sem hash nenhum.
    v = service.verificar(ctx, recibo_id)
    return VerificacaoSaida(
        integro=v.integro, hash_gravado=v.hash_gravado, hash_recalculado=v.hash_recalculado
    )
