from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UltimaExecucao(BaseModel):
    id: UUID
    status: str
    finalizada_em: datetime | None
    registros_novos: int | None


class Fonte(BaseModel):
    """GET /fontes (contracts/api.md)."""

    id: str
    nome: str
    tipo: str
    ultima_execucao: UltimaExecucao | None
