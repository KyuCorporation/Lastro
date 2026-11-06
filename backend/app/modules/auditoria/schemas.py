"""Saída de /auditoria e /auditoria/verificar (contracts/api.md)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

LIMITE_PADRAO = 100
LIMITE_MAXIMO = 500


class EventoAuditoria(BaseModel):
    seq: int
    usuario_id: UUID | None
    evento: str
    detalhes: dict[str, Any] | None
    criado_em: datetime
    hash: str


class VerificacaoCadeiaSaida(BaseModel):
    integra: bool
    n_eventos: int
    primeiro_seq_quebrado: int | None = None
