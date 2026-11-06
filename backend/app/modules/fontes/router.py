from fastapi import APIRouter
from psycopg.rows import dict_row

from app.core.db import sessao
from app.modules.auth.dependencias import Contexto
from app.modules.fontes import queries
from app.modules.fontes.schemas import Fonte, UltimaExecucao

router = APIRouter(tags=["fontes"])


@router.get("/fontes", response_model=list[Fonte])
def listar_fontes(ctx: Contexto) -> list[Fonte]:
    """Fontes públicas e a última coleta concluída. Todos os perfis veem (dado público, sem escopo)."""
    with sessao(ctx) as conn:
        linhas = conn.cursor(row_factory=dict_row).execute(queries.LISTAR_FONTES).fetchall()
    return [
        Fonte(
            id=linha["id"],
            nome=linha["nome"],
            tipo=linha["tipo"],
            ultima_execucao=UltimaExecucao(
                id=linha["execucao_id"],
                status=linha["status"],
                finalizada_em=linha["finalizada_em"],
                registros_novos=linha["registros_novos"],
            )
            if linha["execucao_id"]
            else None,
        )
        for linha in linhas
    ]
