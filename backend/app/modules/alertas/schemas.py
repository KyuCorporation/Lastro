"""Saída de GET /alertas (contracts/api.md)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

StatusAlerta = Literal["aberto", "visto", "resolvido"]
LIMITE_ALERTAS = 200
# O status só avança: aberto → visto → resolvido (visto pode ser pulado).
ORDEM_STATUS: dict[str, int] = {"aberto": 0, "visto": 1, "resolvido": 2}


class SinalAlerta(BaseModel):
    id: UUID | None  # nulo quando o sinal deixou de valer no último cálculo: o conteúdo é a cópia do alerta
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


class AlertaAtualizacao(BaseModel):
    status: Literal["visto", "resolvido"]


class AlertaAtualizado(BaseModel):
    id: UUID
    status: StatusAlerta
