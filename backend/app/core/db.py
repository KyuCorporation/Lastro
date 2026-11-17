"""Sessão de banco da API.

Toda consulta da API passa por `sessao()`: abre uma transação e aplica o contexto de acesso com
`set_config(..., true)`, que vale só até o fim da transação. As políticas de RLS (002_rls.sql) leem esse
contexto. Sem contexto, nada com RLS é visível.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool

from app.core.config import get_settings
from app.core.contexto import ContextoAcesso

STATEMENT_TIMEOUT_MS = 5000

SQL_APLICAR_CONTEXTO = """
select set_config('app.tenant_id', %(tenant_id)s, true),
       set_config('app.usuario_id', %(usuario_id)s, true),
       set_config('app.perfil', %(perfil)s, true),
       set_config('app.ufs', %(ufs)s, true),
       set_config('statement_timeout', %(timeout)s, true)
"""

_pool: ConnectionPool | None = None


def _verificar_conexao(conn: psycopg.Connection) -> None:
    """Testa a conexão antes de entregar (SPEC §14.5: reinício no meio da consulta).

    Postgres reiniciado mata todas as conexões ociosas de uma vez. Descartá-las uma a uma faz o pool esperar
    com backoff a cada uma e estourar o tempo; na primeira morta, o pool inteiro é verificado e reposto.
    """
    try:
        ConnectionPool.check_connection(conn)
    except psycopg.OperationalError:
        if _pool is not None:
            _pool.check()
        raise


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            get_settings().database_url,
            min_size=1,
            max_size=10,
            kwargs={"autocommit": True},
            check=_verificar_conexao,
            open=True,
        )
    return _pool


def fechar_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def parametros_contexto(ctx: ContextoAcesso | None, timeout_ms: int) -> dict[str, str]:
    if ctx is None:
        return {"tenant_id": "", "usuario_id": "", "perfil": "", "ufs": "", "timeout": str(timeout_ms)}
    return {
        "tenant_id": str(ctx.tenant_id),
        "usuario_id": str(ctx.usuario_id),
        "perfil": ctx.perfil,
        "ufs": ",".join(ctx.ufs),
        "timeout": str(timeout_ms),
    }


@contextmanager
def sessao(
    ctx: ContextoAcesso | None, *, timeout_ms: int = STATEMENT_TIMEOUT_MS
) -> Iterator[psycopg.Connection]:
    """Transação com o contexto de acesso aplicado. `ctx=None` só para o que não depende de escopo (login)."""
    with get_pool().connection() as conn, conn.transaction():
        conn.execute(SQL_APLICAR_CONTEXTO, parametros_contexto(ctx, timeout_ms))
        yield conn
