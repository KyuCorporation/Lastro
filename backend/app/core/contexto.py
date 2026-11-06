"""Contexto de acesso de uma requisição. Vem só da sessão autenticada (AGENTS.md §3, regra 3)."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

Perfil = Literal["analista", "gestor", "auditor", "admin"]


@dataclass(frozen=True)
class ContextoAcesso:
    tenant_id: UUID
    usuario_id: UUID
    perfil: Perfil
    ufs: tuple[str, ...]
