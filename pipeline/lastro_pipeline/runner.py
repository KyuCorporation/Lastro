"""Orquestra uma execução de ingestão, igual para todas as fontes.

1. abre `execucoes_ingestao` (fica gravada mesmo se a execução falhar);
2. para cada resposta bruta: bronze (disco + `arquivos_brutos`) → interpretar → normalizar → upsert;
3. qualidade e queda de volume → status `ok` ou `parcial`;
4. erro → status `falhou` com a mensagem, sem gravar nada parcial dos fatos (transação única).
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import psycopg

from lastro_pipeline import bronze, db
from lastro_pipeline.connectors.base import Conector
from lastro_pipeline.modelos import Descarte, RespostaBruta
from lastro_pipeline.quality.relatorio import AvaliadorQualidade

log = logging.getLogger(__name__)

Modo = Literal["online", "offline", "manual"]


@dataclass(frozen=True)
class ResumoExecucao:
    execucao_id: UUID
    fonte_id: str
    status: str
    contagem: db.Contagem
    qualidade: dict[str, Any]


def executar(
    conn: psycopg.Connection,
    conector: Conector,
    respostas: Iterable[RespostaBruta],
    modo: Modo,
    raw_dir: Path | None,
) -> ResumoExecucao:
    """`raw_dir=None` não copia para o disco (offline: o arquivo já está versionado em `data/fixtures/`)."""
    filtros = {**conector.filtros(), "modo": modo}
    parametros: dict[str, Any] = {"filtros": filtros}
    with conn.transaction():
        execucao_id = db.abrir_execucao(conn, conector.fonte_id, parametros)

    contagem = db.Contagem()
    qualidade = AvaliadorQualidade()
    try:
        with conn.transaction():
            for resposta in respostas:
                arquivo_id = _registrar_bronze(conn, conector.fonte_id, execucao_id, resposta, raw_dir)
                for registro in conector.interpretar(resposta):
                    contagem.lidos += 1
                    normalizado = conector.normalizar(registro, resposta)
                    if isinstance(normalizado, Descarte):
                        contagem.descartados += 1
                        qualidade.descartar(normalizado)
                        continue
                    qualidade.observar(normalizado.fato)
                    if normalizado.orgao:
                        db.gravar_orgao(conn, normalizado.orgao)
                    if normalizado.fornecedor:
                        db.gravar_fornecedor(conn, normalizado.fornecedor)
                    contagem.somar(db.gravar_fato(conn, normalizado.fato, arquivo_id, resposta.coletado_em))

            antes = db.lidos_na_execucao_anterior(conn, conector.fonte_id, execucao_id, filtros)
            parametros["qualidade"] = qualidade.relatorio(contagem.lidos, antes)
            status = "parcial" if parametros["qualidade"]["queda_de_volume"] else "ok"
            db.fechar_execucao(conn, execucao_id, status, contagem, parametros)
    except Exception as erro:
        with conn.transaction():
            db.fechar_execucao(
                conn,
                execucao_id,
                "falhou",
                db.Contagem(),
                parametros,
                f"{type(erro).__name__}: {erro}"[:2000],
            )
        raise

    log.info(
        "%s: %s lidos=%d novos=%d atualizados=%d descartados=%d",
        conector.fonte_id,
        status,
        contagem.lidos,
        contagem.novos,
        contagem.atualizados,
        contagem.descartados,
    )
    return ResumoExecucao(execucao_id, conector.fonte_id, status, contagem, parametros["qualidade"])


def _registrar_bronze(
    conn: psycopg.Connection,
    fonte_id: str,
    execucao_id: UUID,
    resposta: RespostaBruta,
    raw_dir: Path | None,
) -> UUID:
    if raw_dir is None:
        caminho = f"fixture:{fonte_id}/{resposta.nome}"
    else:
        caminho = str(bronze.salvar_em_disco(raw_dir, fonte_id, resposta).relative_to(raw_dir.parent))
    return bronze.registrar(conn, fonte_id, execucao_id, resposta, caminho)
