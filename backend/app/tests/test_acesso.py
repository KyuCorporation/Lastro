"""Matriz de acesso (SPEC §6.4). Roda contra o Postgres real do Compose, conectado como lastro_app."""

import os

import psycopg


def conectar() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5)


def test_caso_7_sem_contexto_nada_e_visivel():
    """Conexão como lastro_app sem set_config: select count(*) from contratos retorna 0."""
    with conectar() as conn:
        assert conn.execute("select current_user").fetchone() == ("lastro_app",)
        assert conn.execute("select count(*) from contratos").fetchone() == (0,)
