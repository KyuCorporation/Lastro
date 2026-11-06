"""Entrada e saída de /carteiras (contracts/api.md)."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.tipos import Dinheiro

Finalidade = Literal["homologacao", "monitoramento", "renovacao"]

MAX_CNPJS_POR_CARTEIRA = 1000


class CarteiraEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    finalidade: Finalidade
    # Aceita com ou sem máscara; inválidos voltam em `cnpjs_invalidos` em vez de derrubar a carteira inteira.
    cnpjs: list[str] = Field(min_length=1, max_length=MAX_CNPJS_POR_CARTEIRA)

    @field_validator("nome")
    @classmethod
    def nome_com_texto(cls, nome: str) -> str:
        limpo = " ".join(nome.split())
        if not limpo:
            raise ValueError("nome vazio")
        return limpo

    @field_validator("cnpjs")
    @classmethod
    def cnpjs_curtos(cls, cnpjs: list[str]) -> list[str]:
        if any(len(c) > 32 for c in cnpjs):
            raise ValueError("CNPJ com mais de 32 caracteres")
        return cnpjs


class CarteiraCriada(BaseModel):
    id: UUID
    nome: str
    finalidade: Finalidade
    n_itens: int
    cnpjs_invalidos: list[str]


class CarteiraListada(BaseModel):
    id: UUID
    nome: str
    finalidade: Finalidade
    n_itens: int
    criada_em: datetime


class SinalFila(BaseModel):
    tipo: str
    gravidade: Literal["forte", "atencao", "info"]
    explicacao: str
    evidencias: list[dict[str, Any]]


class ItemFila(BaseModel):
    cnpj: str
    razao_social: str | None
    prioridade: float
    valor_exposto: Dinheiro
    sinais: list[SinalFila]


class CarteiraResumo(BaseModel):
    id: UUID
    nome: str
    finalidade: Finalidade
    criada_em: datetime


class Fila(BaseModel):
    carteira: CarteiraResumo
    itens: list[ItemFila]
