"""Tipos que circulam entre coleta, normalização e gravação.

Fluxo: o conector coleta `RespostaBruta` → interpreta em registros de origem (dict) → a normalização
devolve `RegistroNormalizado` (fato + órgão + fornecedor) ou `Descarte` → a persistência grava.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

Esfera = Literal["federal", "estadual", "municipal", "distrital"]


@dataclass(frozen=True)
class RespostaBruta:
    """Uma resposta de API ou um arquivo, exatamente como veio da fonte."""

    conteudo: bytes
    url_origem: str
    nome: str  # nome do arquivo no bronze e na fixture, ex.: 'contratos_p0001.json'
    coletado_em: datetime
    metadados: dict[str, Any] = field(default_factory=dict)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.conteudo).hexdigest()


class _Modelo(BaseModel):
    model_config = ConfigDict(frozen=True)


class Orgao(_Modelo):
    id: str
    nome: str
    uf: str | None = Field(default=None, min_length=2, max_length=2)
    esfera: Esfera | None = None


class Fornecedor(_Modelo):
    cnpj: str = Field(pattern=r"^[0-9]{14}$")
    razao_social: str | None = None
    uf_sede: str | None = Field(default=None, min_length=2, max_length=2)


class Fato(_Modelo):
    """Linha pública com proveniência. `hash_conteudo` cobre só o conteúdo, nunca a hora da coleta."""

    tabela: ClassVar[str]
    fonte_id: str
    id_origem: str
    url_origem: str | None = None

    @property
    def hash_conteudo(self) -> str:
        dados = self.model_dump(mode="json")
        canonico = json.dumps(dados, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


class Contrato(Fato):
    tabela: ClassVar[str] = "contratos"
    uf: str = Field(min_length=2, max_length=2)
    orgao_id: str | None = None
    fornecedor_cnpj: str = Field(pattern=r"^[0-9]{14}$")
    objeto: str | None = None
    valor_global: Decimal | None = None
    data_assinatura: date | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None


class Pagamento(Fato):
    tabela: ClassVar[str] = "pagamentos"
    uf: str = Field(min_length=2, max_length=2)
    orgao_id: str | None = None
    fornecedor_cnpj: str = Field(pattern=r"^[0-9]{14}$")
    data_pagamento: date | None = None
    valor: Decimal | None = None
    descricao: str | None = None


class Sancao(Fato):
    tabela: ClassVar[str] = "sancoes"
    cnpj: str = Field(pattern=r"^[0-9]{14}$")
    tipo: str | None = None
    orgao_sancionador: str | None = None
    uf_orgao: str | None = Field(default=None, min_length=2, max_length=2)
    data_inicio: date | None = None
    data_fim: date | None = None
    fundamentacao: str | None = None


@dataclass(frozen=True)
class RegistroNormalizado:
    fato: Contrato | Pagamento | Sancao
    orgao: Orgao | None = None
    fornecedor: Fornecedor | None = None


@dataclass(frozen=True)
class Descarte:
    """Registro de origem que não entra no banco. `motivo` vai para o relatório de qualidade."""

    motivo: Literal["pessoa_fisica", "documento_invalido", "fora_do_escopo", "incompleto"]
    id_origem: str | None = None


Normalizacao = RegistroNormalizado | Descarte
