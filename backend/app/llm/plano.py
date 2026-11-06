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


def _normalizar(dados: dict) -> dict:
    """Corrige só o que é formato, sem mudar o sentido do plano.

    - `versao` ausente vira "v1"; `parametros` ausente vira objeto vazio.
    - Parâmetro nulo ou vazio é ignorado.
    - CNPJ com máscara perde a pontuação (se não sobrarem 14 dígitos, a validação reprova como antes).
    - UF vai para maiúsculas, sem espaço.
    - Parâmetro conhecido que a intent não usa (ex.: `dias` num resumo, `uf` numa sanção) é descartado.
    Campo fora do contrato (ex.: `tenant_id`, `sql`) não é tocado: a validação continua reprovando.
    """
    dados = {**dados}
    dados.setdefault("versao", "v1")
    params = dados.get("parametros")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return dados
    limpos = {k: v for k, v in params.items() if v is not None and not (isinstance(v, str) and not v.strip())}
    if isinstance(limpos.get("cnpj"), str):
        limpos["cnpj"] = re.sub(r"\D", "", limpos["cnpj"])
    if isinstance(limpos.get("uf"), str):
        limpos["uf"] = limpos["uf"].strip().upper()
    intent = INTENTS.get(dados.get("intent")) if isinstance(dados.get("intent"), str) else None
    if intent is not None:
        aceitos = set(intent.obrigatorios) | set(intent.opcionais)
        conhecidos = set(Parametros.model_fields)
        limpos = {k: v for k, v in limpos.items() if k in aceitos or k not in conhecidos}
    dados["parametros"] = limpos
    return dados


def validar_plano(bruto: str) -> PlanoConsulta:
    """Valida a saída da LLM. Formato é normalizado; desvio de sentido ou do contrato vira PlanoInvalido."""
    texto = _CERCA.sub(r"\1", bruto)
    try:
        dados = json.loads(texto)
        if not isinstance(dados, dict):
            raise PlanoInvalido("o plano não é um objeto JSON")
        if "intent" not in dados:
            raise PlanoInvalido("campo obrigatório ausente: intent")
        return PlanoConsulta.model_validate(_normalizar(dados), strict=False)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise PlanoInvalido(str(exc)) from exc
