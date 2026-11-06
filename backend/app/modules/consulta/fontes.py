"""Proveniência no nível da fonte: para o recibo (`fontes[]`) e para a abstenção ("coletadas até")."""

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg

from app.modules.consulta import queries
from app.modules.recibos.montagem import Fonte

# Fontes que cada intent consulta (para a data da última coleta na abstenção).
FONTES_DA_INTENT: dict[str, tuple[str, ...]] = {"sancoes_fornecedor": ("ceis", "cnep")}
FONTES_PADRAO = ("pe_portal", "pncp")


def fontes_das_linhas(conn: psycopg.Connection, linhas: list[dict[str, Any]]) -> tuple[Fonte, ...]:
    """Uma entrada por fonte citada: coleta mais recente das linhas dela e a execução que a gravou."""
    if not linhas:
        return ()
    ids_fonte = sorted({linha["fonte_id"] for linha in linhas})
    meta = {r[0]: (r[1], r[2]) for r in conn.execute(queries.FONTES, {"ids": ids_fonte}).fetchall()}
    ids_arquivo = [linha["arquivo_bruto_id"] for linha in linhas if linha.get("arquivo_bruto_id")]
    execucao_do_arquivo: dict[UUID, UUID | None] = (
        dict(conn.execute(queries.EXECUCAO_DOS_ARQUIVOS, {"ids": ids_arquivo}).fetchall())
        if ids_arquivo
        else {}
    )

    fontes = []
    for fonte_id in ids_fonte:
        da_fonte = [linha for linha in linhas if linha["fonte_id"] == fonte_id]
        mais_recente = max(da_fonte, key=lambda linha: linha["coletado_em"])
        nome, tipo = meta.get(fonte_id, (fonte_id, ""))
        fontes.append(
            Fonte(
                fonte_id=fonte_id,
                nome=nome,
                coletado_em=mais_recente["coletado_em"],
                execucao_id=execucao_do_arquivo.get(mais_recente.get("arquivo_bruto_id")),
                sintetico=tipo == "sintetico",
            )
        )
    return tuple(fontes)


def ultima_coleta(conn: psycopg.Connection, intent: str) -> datetime | None:
    fontes = list(FONTES_DA_INTENT.get(intent, FONTES_PADRAO))
    linha = conn.execute(queries.ULTIMA_COLETA, {"fontes": fontes}).fetchone()
    return linha[0] if linha else None
