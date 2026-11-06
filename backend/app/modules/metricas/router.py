from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.auth.dependencias import Contexto
from app.modules.metricas import service

router = APIRouter(tags=["metricas"])


class MetricasSaida(BaseModel):
    eval: dict[str, Any] | None
    ataques: dict[str, Any] | None
    cronometro: dict[str, Any] | None
    ultima_atualizacao: str | None


@router.get("/metricas", response_model=MetricasSaida)
def obter_metricas(_ctx: Contexto) -> MetricasSaida:
    # Números agregados do eval, sem dado de tenant: qualquer perfil autenticado.
    return MetricasSaida(**service.metricas())
