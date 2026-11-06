from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.contexto import ContextoAcesso
from app.core.relogio import Hoje
from app.modules.auth.dependencias import Contexto
from app.modules.carteiras import service
from app.modules.carteiras.schemas import CarteiraCriada, CarteiraEntrada, CarteiraListada, Fila
from app.modules.policy.service import Acao, exigir

router = APIRouter(tags=["carteiras"])


@router.post("/carteiras", response_model=CarteiraCriada, status_code=status.HTTP_201_CREATED)
def criar_carteira(
    entrada: CarteiraEntrada,
    ctx: Annotated[ContextoAcesso, Depends(exigir(Acao.EDITAR_CARTEIRA))],
) -> CarteiraCriada:
    return service.criar(ctx, entrada)


@router.get("/carteiras", response_model=list[CarteiraListada])
def listar_carteiras(ctx: Contexto) -> list[CarteiraListada]:
    # Todos os perfis veem as carteiras do próprio tenant (SPEC §6.2); a RLS esconde as dos outros.
    return service.listar(ctx)


@router.get("/carteiras/{carteira_id}/fila", response_model=Fila)
def fila_da_carteira(
    carteira_id: UUID,
    ctx: Annotated[ContextoAcesso, Depends(exigir(Acao.VER_FILA))],
    hoje: Hoje,
) -> Fila:
    return service.fila(ctx, carteira_id, hoje)
