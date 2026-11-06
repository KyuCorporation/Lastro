"""Gravação, leitura e verificação de recibos.

A gravação roda na mesma transação da consulta (`gravar(conn, ...)`). A verificação (T15) recalcula o hash
canônico do conteúdo lido do banco e compara com o hash gravado junto: qualquer alteração posterior em uma das
duas colunas, mesmo feita por quem tem acesso direto ao banco, aparece como "alterado".
"""

import hmac
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Verificacao:
    integro: bool
    hash_gravado: str
    hash_recalculado: str


def verificar_conteudo(conteudo: dict[str, Any], hash_gravado: str) -> Verificacao:
    """Função pura: recalcula o hash do conteúdo e compara com o gravado em tempo constante."""
    gravado = hash_gravado.strip().lower()  # a coluna é char(64): normaliza preenchimento e caixa
    recalculado = hash_recibo(conteudo)
    return Verificacao(
        integro=hmac.compare_digest(gravado, recalculado),
        hash_gravado=gravado,
        hash_recalculado=recalculado,
    )


def _buscar(ctx: ContextoAcesso, recibo_id: UUID) -> dict[str, Any]:
    """Recibo de outro usuário ou de outro tenant responde 404, igual a inexistente (não revela existência).

    Quem pode ver (dono, auditor e admin do tenant) é decidido pela RLS de `recibos`.
    """
    with sessao(ctx) as conn:
        linha = conn.cursor(row_factory=dict_row).execute(queries.BUSCAR_RECIBO, {"id": recibo_id}).fetchone()
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Recibo não encontrado.")
    return linha


def obter(ctx: ContextoAcesso, recibo_id: UUID) -> dict[str, Any]:
    linha = _buscar(ctx, recibo_id)
    criado: datetime = linha["criado_em"]
    return {"id": linha["id"], "conteudo": linha["conteudo"], "hash": linha["hash"], "criado_em": criado}


def verificar(ctx: ContextoAcesso, recibo_id: UUID) -> Verificacao:
    linha = _buscar(ctx, recibo_id)
    return verificar_conteudo(linha["conteudo"], linha["hash"])
