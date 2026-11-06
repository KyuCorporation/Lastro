"""Saída de GET /alertas (contracts/api.md)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

StatusAlerta = Literal["aberto", "visto", "resolvido"]
LIMITE_ALERTAS = 200


class SinalAlerta(BaseModel):
    id: UUID
    tipo: str
    gravidade: str
    uf: str | None
    explicacao: str


class AlertaSaida(BaseModel):
    id: UUID
    carteira_id: UUID | None
    cnpj: str
    sinal: SinalAlerta | None  # nulo se o alerta não tem sinal ou se o sinal é de UF fora do escopo
    status: StatusAlerta
    criado_em: datetime
