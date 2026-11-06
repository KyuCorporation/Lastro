import psycopg


def db_disponivel(database_url: str) -> bool:
    """Confere só se o banco responde. Não lê nenhuma tabela, então não depende do contexto de acesso."""
    try:
        with psycopg.connect(database_url, connect_timeout=2) as conn:
            conn.execute("select 1")
        return True
    except psycopg.Error:
        return False
