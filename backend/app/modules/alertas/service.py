"""Alertas por carteira (SPEC §3.3 I7, T28): geração quando a carteira é criada ou a fila é aberta, e leitura."""

from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.core.errors import ErroApi
from app.modules.alertas import queries
from app.modules.alertas.schemas import (
    LIMITE_ALERTAS,
    ORDEM_STATUS,
    AlertaAtualizacao,
    AlertaAtualizado,
    AlertaSaida,
    SinalAlerta,
    StatusAlerta,
)
from app.modules.auditoria import service as auditoria


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


def atualizar(ctx: ContextoAcesso, alerta_id: UUID, entrada: AlertaAtualizacao) -> AlertaAtualizado:
    """Marca como visto ou resolvido. O status só avança; a mudança entra na trilha junto com o update."""
    with sessao(ctx) as conn:
        linha = conn.execute(queries.STATUS_DO_ALERTA, {"id": alerta_id}).fetchone()
        if linha is None:
            raise ErroApi(404, "NAO_ENCONTRADO", "Alerta não encontrado.")
        atual: str = linha[0]
        if ORDEM_STATUS[entrada.status] <= ORDEM_STATUS[atual]:
            raise ErroApi(422, "ENTRADA_INVALIDA", f"O alerta já está {atual}; o status só avança.")
        conn.execute(queries.ATUALIZAR_STATUS, {"id": alerta_id, "status": entrada.status})
        auditoria.registrar_em(
            conn, "alerta_atualizado", {"alerta_id": str(alerta_id), "de": atual, "para": entrada.status}
        )
    return AlertaAtualizado(id=alerta_id, status=entrada.status)
