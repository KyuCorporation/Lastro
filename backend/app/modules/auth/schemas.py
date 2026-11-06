from uuid import UUID

from pydantic import BaseModel, Field

from app.core.contexto import Perfil
from app.core.tipos import TextoSemNulo


class LoginEntrada(BaseModel):
    email: TextoSemNulo = Field(min_length=3, max_length=254)
    senha: TextoSemNulo = Field(min_length=1, max_length=200)


class TenantSaida(BaseModel):
    id: UUID
    nome: str


class UsuarioSaida(BaseModel):
    id: UUID
    nome: str
    perfil: Perfil
    tenant: TenantSaida
    ufs: list[str]


class LoginSaida(BaseModel):
    token: str
    usuario: UsuarioSaida
