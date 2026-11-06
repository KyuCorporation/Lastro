import psycopg
from psycopg_pool import PoolTimeout

from app.core.db import sessao


def db_disponivel() -> bool:
    """Confere só se o banco responde. Não lê nenhuma tabela."""
    try:
        with sessao(None) as conn:
            conn.execute("select 1")
        return True
    except (psycopg.Error, PoolTimeout):
        return False
