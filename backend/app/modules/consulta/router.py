from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.contexto import ContextoAcesso
from app.modules.consulta import service
from app.modules.consulta.dependencias import ambiente, consultante
from app.modules.consulta.schemas import (
    LIMITE_LISTAGEM_MAXIMO,
    LIMITE_LISTAGEM_PADRAO,
    ConsultaEntrada,
    ConsultaListada,
    ConsultaSaida,
)
from app.modules.consulta.service import Ambiente
from app.modules.policy.service import Acao, exigir_qualquer

router = APIRouter(tags=["consulta"])


@router.post("/consultas", response_model=ConsultaSaida)
def criar_consulta(
    entrada: ConsultaEntrada,
    ctx: Annotated[ContextoAcesso, Depends(consultante)],
    amb: Annotated[Ambiente, Depends(ambiente)],
) -> ConsultaSaida:
    return service.responder(entrada, ctx, amb)


@router.get("/consultas", response_model=list[ConsultaListada])
def listar_consultas(
    ctx: Annotated[
        ContextoAcesso, Depends(exigir_qualquer(Acao.VER_PROPRIAS_CONSULTAS, Acao.VER_CONSULTAS_TENANT))
    ],
    limite: Annotated[int, Query(ge=1, le=LIMITE_LISTAGEM_MAXIMO)] = LIMITE_LISTAGEM_PADRAO,
) -> list[ConsultaListada]:
    # Quais consultas aparecem (as próprias, ou as do tenant para auditor e admin) é decidido pela RLS.
    return service.listar(ctx, limite)
