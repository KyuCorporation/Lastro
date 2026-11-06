from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.contexto import ContextoAcesso
from app.core.errors import ErroApi
from app.modules.consulta.schemas import ConsultaEntrada
from app.modules.policy.service import Acao, exigir

router = APIRouter(tags=["consulta"])


@router.post("/consultas")
def criar_consulta(
    entrada: ConsultaEntrada,
    ctx: Annotated[ContextoAcesso, Depends(exigir(Acao.CONSULTAR))],
) -> None:
    # A permissão por perfil já vale. A orquestração (planejador → catálogo → redator → recibo)
    # ainda não existe.
    raise ErroApi(501, "NAO_IMPLEMENTADO", "Consulta ainda não implementada.")
