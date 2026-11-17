"""Alertas por carteira (SPEC §3.3 I7, T28): geração quando a carteira é criada ou a fila é aberta, e leitura."""

from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.modules.alertas import queries
from app.modules.alertas.schemas import LIMITE_ALERTAS, AlertaSaida, SinalAlerta, StatusAlerta


def gerar_da_carteira(conn: psycopg.Connection, carteira_id: UUID) -> int:
    """Um alerta aberto para cada sinal novo de fornecedor da carteira. Devolve quantos nasceram."""
    return conn.execute(queries.GERAR_ALERTAS_DA_CARTEIRA, {"carteira_id": carteira_id}).rowcount


def listar(ctx: ContextoAcesso, status: StatusAlerta | None) -> list[AlertaSaida]:
    with sessao(ctx) as conn:
        linhas = (
            conn.cursor(row_factory=dict_row)
            .execute(queries.LISTAR_ALERTAS, {"status": status, "limite": LIMITE_ALERTAS})
            .fetchall()
        )
    return [
        AlertaSaida(
            id=linha["id"],
            carteira_id=linha["carteira_id"],
            cnpj=linha["cnpj"],
            status=linha["status"],
            criado_em=linha["criado_em"],
            sinal=None
            if not linha["sinal_visivel"]
            else SinalAlerta(
                id=linha["sinal_id"],
                tipo=linha["tipo"],
                gravidade=linha["gravidade"],
                uf=linha["uf"],
                explicacao=linha["explicacao"],
            ),
        )
        for linha in linhas
    ]
