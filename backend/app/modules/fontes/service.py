"""Fontes de dados e execuções de ingestão (tela de fontes, SPEC §12 item 7)."""

from psycopg.rows import dict_row

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.modules.fontes import queries
from app.modules.fontes.schemas import LIMITE_EXECUCOES, ExecucaoSaida, FonteSaida, UltimaExecucao


def listar_fontes(ctx: ContextoAcesso) -> list[FonteSaida]:
    with sessao(ctx) as conn:
        linhas = conn.cursor(row_factory=dict_row).execute(queries.LISTAR_FONTES).fetchall()
    return [
        FonteSaida(
            id=linha["id"],
            nome=linha["nome"],
            tipo=linha["tipo"],
            ultima_execucao=None
            if linha["execucao_id"] is None
            else UltimaExecucao(
                id=linha["execucao_id"],
                status=linha["status"],
                finalizada_em=linha["finalizada_em"],
                registros_novos=linha["registros_novos"],
            ),
        )
        for linha in linhas
    ]


def listar_execucoes(ctx: ContextoAcesso, fonte_id: str | None) -> list[ExecucaoSaida]:
    with sessao(ctx) as conn:
        linhas = (
            conn.cursor(row_factory=dict_row)
            .execute(queries.LISTAR_EXECUCOES, {"fonte_id": fonte_id, "limite": LIMITE_EXECUCOES})
            .fetchall()
        )
    return [ExecucaoSaida(**linha) for linha in linhas]
