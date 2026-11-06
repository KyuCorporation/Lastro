from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.core.contexto import ContextoAcesso
from app.core.relogio import Hoje
from app.modules.fornecedores import service
from app.modules.fornecedores.schemas import Dossie
from app.modules.policy.service import Acao, exigir

router = APIRouter(tags=["fornecedores"])


@router.get("/fornecedores/{cnpj}/dossie", response_model=Dossie)
def dossie(
    cnpj: Annotated[str, Path(max_length=32, description="CNPJ com ou sem máscara")],
    ctx: Annotated[ContextoAcesso, Depends(exigir(Acao.VER_DOSSIE))],
    hoje: Hoje,
) -> Dossie:
    return service.montar(ctx, cnpj, hoje)
