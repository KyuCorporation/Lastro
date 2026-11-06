from typing import Any

from psycopg.types.json import Jsonb

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.modules.auditoria import queries


def registrar(ctx: ContextoAcesso, evento: str, detalhes: dict[str, Any]) -> None:
    """Grava um evento na trilha do tenant da sessão.

    Usa transação própria, então o evento fica gravado mesmo se a rota falhar depois.
    """
    with sessao(ctx) as conn:
        conn.execute(queries.INSERIR_EVENTO, {"evento": evento, "detalhes": Jsonb(detalhes)})
