"""Alertas por carteira (SPEC §3.3 I7). A geração por evento é da T28; aqui fica a leitura."""

from psycopg.rows import dict_row

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.modules.alertas import queries
from app.modules.alertas.schemas import LIMITE_ALERTAS, AlertaSaida, SinalAlerta, StatusAlerta


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
            if linha["sinal_id"] is None
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
