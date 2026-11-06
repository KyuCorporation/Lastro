"""Entrada e saída de /consultas (contracts/api.md)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.tipos import TextoSemNulo

StatusConsulta = Literal["respondida", "abstencao", "esclarecimento", "negada", "erro"]

LIMITE_LISTAGEM_PADRAO = 50
LIMITE_LISTAGEM_MAXIMO = 200


class ConsultaEntrada(BaseModel):
    pergunta: TextoSemNulo = Field(min_length=1, max_length=500)
    carteira_id: UUID | None = None

    @field_validator("pergunta")
    @classmethod
    def pergunta_com_texto(cls, pergunta: str) -> str:
        limpa = pergunta.strip()
        if not limpa:
            raise ValueError("pergunta vazia")
        return limpa


class Citacao(BaseModel):
    n: int
    tabela: str
    id: str
    fonte_id: str
    url_origem: str | None
    coletado_em: datetime


class ConsultaSaida(BaseModel):
    consulta_id: UUID
    status: StatusConsulta
    resposta: str
    citacoes: list[Citacao]
    recibo_id: UUID | None
    sintetico: bool


class ConsultaListada(BaseModel):
    id: UUID
    usuario_id: UUID
    carteira_id: UUID | None
    pergunta: str
    intent: str | None
    status: StatusConsulta
    criada_em: datetime
    recibo_id: UUID | None
