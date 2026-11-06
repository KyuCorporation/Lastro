"""Saída de /fontes e /fontes/execucoes (contracts/api.md)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

LIMITE_EXECUCOES = 100


class UltimaExecucao(BaseModel):
    id: UUID
    status: str
    finalizada_em: datetime | None
    registros_novos: int | None


class FonteSaida(BaseModel):
    id: str
    nome: str
    tipo: str
    ultima_execucao: UltimaExecucao | None


class ExecucaoSaida(BaseModel):
    id: UUID
    fonte_id: str
    status: str
    iniciada_em: datetime
    finalizada_em: datetime | None
    registros_lidos: int | None
    registros_novos: int | None
    registros_descartados: int | None
    erro: str | None
