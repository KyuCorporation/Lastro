"""Gravação e leitura de recibos. A gravação roda na mesma transação da consulta (`gravar(conn, ...)`)."""

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.core.errors import ErroApi
from app.modules.recibos import queries
from app.modules.recibos.canonico import hash_recibo
from app.modules.recibos.montagem import DadosRecibo, montar_conteudo


def gravar(conn: psycopg.Connection, dados: DadosRecibo) -> UUID:
    conteudo = montar_conteudo(dados)
    linha = conn.execute(
        queries.INSERIR_RECIBO,
        {
            "consulta_id": dados.consulta_id,
            "conteudo": Jsonb(conteudo),
            "hash": hash_recibo(conteudo),
            "criado_em": dados.criado_em,
        },
    ).fetchone()
    assert linha is not None
    return linha[0]


def obter(ctx: ContextoAcesso, recibo_id: UUID) -> dict[str, Any]:
    """Recibo de outro usuário ou de outro tenant responde 404, igual a inexistente (não revela existência)."""
    with sessao(ctx) as conn:
        linha = conn.cursor(row_factory=dict_row).execute(queries.BUSCAR_RECIBO, {"id": recibo_id}).fetchone()
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Recibo não encontrado.")
    criado: datetime = linha["criado_em"]
    return {"id": linha["id"], "conteudo": linha["conteudo"], "hash": linha["hash"], "criado_em": criado}
