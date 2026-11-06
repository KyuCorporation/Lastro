from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.modules.auditoria import queries


def registrar_em(conn: psycopg.Connection, evento: str, detalhes: dict[str, Any]) -> None:
    """Grava um evento dentro de uma transação que já tem o contexto de acesso aplicado.

    Usado quando o evento precisa entrar junto com outras linhas (consulta e recibo): ou tudo, ou nada.
    """
    conn.execute(queries.INSERIR_EVENTO, {"evento": evento, "detalhes": Jsonb(detalhes)})


def registrar(ctx: ContextoAcesso, evento: str, detalhes: dict[str, Any]) -> None:
    """Grava um evento na trilha do tenant da sessão.

    Usa transação própria, então o evento fica gravado mesmo se a rota falhar depois.
    """
    with sessao(ctx) as conn:
        registrar_em(conn, evento, detalhes)
