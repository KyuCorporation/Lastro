from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.modules.auditoria import queries


def registrar_em(conn: psycopg.Connection, evento: str, detalhes: dict[str, Any]) -> None:
    """Grava um evento dentro de uma transação que já tem o contexto de acesso aplicado.

    Usado quando o evento precisa entrar junto com outras linhas (consulta e recibo): ou tudo, ou nada.
    O lock vale até o fim da transação, como o do trigger; pegar de novo na mesma transação não bloqueia.
    """
    conn.execute(queries.TRAVAR_CADEIA)
    conn.execute(queries.INSERIR_EVENTO, {"evento": evento, "detalhes": Jsonb(detalhes)})


def registrar(ctx: ContextoAcesso, evento: str, detalhes: dict[str, Any]) -> None:
    """Grava um evento na trilha do tenant da sessão.

    Usa transação própria, então o evento fica gravado mesmo se a rota falhar depois.
    """
    with sessao(ctx) as conn:
        registrar_em(conn, evento, detalhes)


def listar(ctx: ContextoAcesso, evento: str | None, limite: int) -> list[dict[str, Any]]:
    with sessao(ctx) as conn:
        return (
            conn.cursor(row_factory=dict_row)
            .execute(queries.LISTAR_EVENTOS, {"evento": evento, "limite": limite})
            .fetchall()
        )


@dataclass(frozen=True)
class VerificacaoCadeia:
    integra: bool
    n_eventos: int
    primeiro_seq_quebrado: int | None


def verificar_em(conn: psycopg.Connection) -> VerificacaoCadeia:
    """Verifica a cadeia do tenant da sessão já aberta (o contexto define qual trilha)."""
    linha = conn.execute(queries.VERIFICAR_CADEIA).fetchone()
    assert linha is not None
    n_eventos, quebrado = linha
    return VerificacaoCadeia(integra=quebrado is None, n_eventos=n_eventos, primeiro_seq_quebrado=quebrado)


def verificar(ctx: ContextoAcesso) -> VerificacaoCadeia:
    with sessao(ctx) as conn:
        return verificar_em(conn)
