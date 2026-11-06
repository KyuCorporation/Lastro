"""Saída de GET /fornecedores/{cnpj}/dossie (contracts/api.md).

Cada item traz a proveniência (`fonte_id`, `url_origem`, `coletado_em`). Sinais são derivados: em vez de fonte,
carregam `evidencias` que apontam para as linhas de origem, e a versão da regra.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.core.tipos import Dinheiro


class Fornecedor(BaseModel):
    cnpj: str
    razao_social: str | None
    uf_sede: str | None


class ResumoUf(BaseModel):
    uf: str
    n_contratos: int
    valor_contratado: Dinheiro
    valor_vigente: Dinheiro
    n_pagamentos: int
    valor_pago: Dinheiro
    valor_empenhado: Dinheiro


class Proveniencia(BaseModel):
    id: UUID
    fonte_id: str
    id_origem: str
    url_origem: str | None
    coletado_em: datetime


class ContratoDossie(Proveniencia):
    uf: str
    orgao_id: str | None
    orgao_nome: str | None
    objeto: str | None
    valor_global: Dinheiro | None
    data_assinatura: date | None
    vigencia_inicio: date | None
    vigencia_fim: date | None


class SancaoDossie(Proveniencia):
    tipo: str | None
    orgao_sancionador: str | None
    uf_orgao: str | None
    data_inicio: date | None
    data_fim: date | None
    fundamentacao: str | None
    vigente: bool


class SinalDossie(BaseModel):
    id: UUID
    tipo: str
    gravidade: Literal["forte", "atencao", "info"]
    uf: str | None
    valor: Decimal | None
    explicacao: str
    evidencias: list[dict[str, Any]]
    versao_regra: str
    calculado_em: datetime


class SocioDossie(BaseModel):
    socio_tipo: Literal["PF", "PJ"]
    socio_exibicao: str  # PF sempre mascarado na origem (SPEC §13)
    fonte_id: str
    coletado_em: datetime


class FonteDossie(BaseModel):
    fonte_id: str
    nome: str
    coletado_em: datetime  # a coleta mais recente entre as linhas do dossiê
    sintetico: bool


class Dossie(BaseModel):
    fornecedor: Fornecedor
    resumo_por_uf: list[ResumoUf]
    contratos_vigentes: list[ContratoDossie]
    vencendo_180d: list[ContratoDossie]
    sancoes: list[SancaoDossie]
    sinais: list[SinalDossie]
    socios: list[SocioDossie] | None  # None para perfil que não vê sócios (gestor)
    fontes: list[FonteDossie]
