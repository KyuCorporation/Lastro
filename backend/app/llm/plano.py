"""Plano de consulta (contracts/plano_consulta.schema.json) e sua validação.

O plano nunca contém tenant, usuário ou SQL. A UF pedida é interseccionada com o escopo da sessão depois,
pelo executor do catálogo.
"""

import json
import re
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.modules.catalogo.intents import INTENTS, UFS, IntentId


class PlanoInvalido(Exception):
    pass


class Parametros(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cnpj: Annotated[str, Field(pattern=r"^[0-9]{14}$")] | None = None
    uf: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None
    dias: Annotated[int, Field(ge=1, le=365)] | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    termo: Annotated[str, Field(min_length=2, max_length=80)] | None = None
    carteira_id: UUID | None = None
    motivo: Annotated[str, Field(max_length=200)] | None = None
    pergunta_de_volta: Annotated[str, Field(max_length=200)] | None = None

    @field_validator("uf")
    @classmethod
    def uf_existe(cls, uf: str | None) -> str | None:
        if uf is not None and uf not in UFS:
            raise ValueError("UF inexistente")
        return uf


class PlanoConsulta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    versao: Literal["v1"] = "v1"
    intent: IntentId
    parametros: Parametros = Field(default_factory=Parametros)
    confianca: Annotated[float, Field(ge=0, le=1)] | None = None

    @model_validator(mode="after")
    def parametros_da_intent(self) -> "PlanoConsulta":
        intent = INTENTS[self.intent]
        presentes = {k for k, v in self.parametros.model_dump().items() if v is not None}
        if faltando := set(intent.obrigatorios) - presentes:
            raise ValueError(f"parâmetros obrigatórios ausentes: {sorted(faltando)}")
        if sobrando := presentes - set(intent.obrigatorios) - set(intent.opcionais):
            raise ValueError(f"parâmetros que a intent não aceita: {sorted(sobrando)}")
        p = self.parametros
        if p.data_inicio and p.data_fim and p.data_inicio > p.data_fim:
            raise ValueError("data_inicio depois de data_fim")
        return self


def esclarecer(pergunta_de_volta: str) -> PlanoConsulta:
    return PlanoConsulta(intent="esclarecer", parametros=Parametros(pergunta_de_volta=pergunta_de_volta))


def fora_de_escopo(motivo: str) -> PlanoConsulta:
    return PlanoConsulta(intent="fora_de_escopo", parametros=Parametros(motivo=motivo))


_CERCA = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def validar_plano(bruto: str) -> PlanoConsulta:
    """Valida a saída da LLM. Qualquer desvio do contrato vira PlanoInvalido."""
    texto = _CERCA.sub(r"\1", bruto)
    try:
        dados = json.loads(texto)
        if not isinstance(dados, dict):
            raise PlanoInvalido("o plano não é um objeto JSON")
        if faltando := {"versao", "intent", "parametros"} - dados.keys():
            raise PlanoInvalido(f"campos obrigatórios ausentes: {sorted(faltando)}")
        return PlanoConsulta.model_validate(dados, strict=False)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise PlanoInvalido(str(exc)) from exc
