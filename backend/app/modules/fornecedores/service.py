"""Dossiê de uma página do fornecedor (SPEC §12, tela 5): resumo, vigentes, vencimentos, sanções e sinais.

Escopo: só o que a RLS mostra ao usuário (UFs do escopo). Sem nenhum registro visível, responde 404, igual a
fornecedor inexistente: o dossiê não revela que há dados do CNPJ numa UF fora do escopo.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.cnpj import cnpj_valido, normalizar_cnpj
from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.core.errors import ErroApi
from app.modules.auditoria import service as auditoria
from app.modules.fornecedores import queries
from app.modules.fornecedores.schemas import (
    ContratoDossie,
    Dossie,
    FonteDossie,
    Fornecedor,
    ResumoUf,
    SancaoDossie,
    SinalDossie,
    SocioDossie,
)
from app.modules.policy.service import Acao, pode

DIAS_VENCENDO = 180
LIMITE_LINHAS = 200  # mesmo teto do executor do catálogo (SPEC §7)

MENSAGEM_SEM_REGISTROS = "Não há registros deste fornecedor nas fontes autorizadas para você."


def validar_cnpj(bruto: str) -> str:
    cnpj = normalizar_cnpj(bruto)
    if not cnpj_valido(cnpj):
        raise ErroApi(422, "ENTRADA_INVALIDA", "CNPJ inválido (14 dígitos com dígito verificador).")
    return cnpj


def sancao_vigente(inicio: date | None, fim: date | None, hoje: date) -> bool:
    """Mesmo critério do sinal `sancao_direta` (pipeline/lastro_pipeline/sinais/regras.py)."""
    return (inicio is None or inicio <= hoje) and (fim is None or fim >= hoje)


def _linhas(conn: psycopg.Connection, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return conn.cursor(row_factory=dict_row).execute(sql, params).fetchall()


def _fontes(conn: psycopg.Connection, grupos: list[list[dict[str, Any]]]) -> list[FonteDossie]:
    coleta: dict[str, datetime] = {}
    for linhas in grupos:
        for linha in linhas:
            fonte, quando = linha["fonte_id"], linha["coletado_em"]
            if fonte not in coleta or quando > coleta[fonte]:
                coleta[fonte] = quando
    if not coleta:
        return []
    meta = {f["id"]: f for f in _linhas(conn, queries.FONTES, {"ids": list(coleta)})}
    return [
        FonteDossie(
            fonte_id=fonte,
            nome=meta[fonte]["nome"] if fonte in meta else fonte,
            coletado_em=quando,
            sintetico=fonte in meta and meta[fonte]["tipo"] == "sintetico",
        )
        for fonte, quando in sorted(coleta.items())
    ]


@dataclass(frozen=True)
class _Lido:
    fornecedor: dict[str, Any] | None
    resumo: list[dict[str, Any]]
    vigentes: list[dict[str, Any]]
    sancoes: list[dict[str, Any]]
    sinais: list[dict[str, Any]]
    socios: list[dict[str, Any]] | None
    fontes: list[FonteDossie]


def _ler(conn: psycopg.Connection, ctx: ContextoAcesso, params: dict[str, Any]) -> _Lido | None:
    """Tudo numa transação só (mesmo instante). None quando o usuário não vê nenhum registro do CNPJ."""
    resumo = _linhas(conn, queries.RESUMO_POR_UF, params)
    sancoes = _linhas(conn, queries.SANCOES, params)
    sinais = _linhas(conn, queries.SINAIS, params)
    if not (resumo or sancoes or sinais):
        return None
    fornecedor = _linhas(conn, queries.FORNECEDOR, params)
    vigentes = _linhas(conn, queries.CONTRATOS_VIGENTES, params)
    socios = _linhas(conn, queries.SOCIOS, params) if pode(ctx.perfil, Acao.VER_SOCIOS) else None
    return _Lido(
        fornecedor=fornecedor[0] if fornecedor else None,
        resumo=resumo,
        vigentes=vigentes,
        sancoes=sancoes,
        sinais=sinais,
        socios=socios,
        fontes=_fontes(conn, [vigentes, sancoes, socios or []]),
    )


def montar(ctx: ContextoAcesso, cnpj_bruto: str, hoje: date) -> Dossie:
    cnpj = validar_cnpj(cnpj_bruto)
    params = {"cnpj": cnpj, "hoje": hoje, "limite": LIMITE_LINHAS}
    with sessao(ctx) as conn:
        lido = _ler(conn, ctx, params)
        # Quem abriu qual dossiê fica na trilha do tenant, inclusive quando não havia nada visível.
        auditoria.registrar_em(conn, "dossie", {"cnpj": cnpj, "encontrado": lido is not None})
    if lido is None:
        raise ErroApi(404, "NAO_ENCONTRADO", MENSAGEM_SEM_REGISTROS)

    limite_vencendo = hoje + timedelta(days=DIAS_VENCENDO)
    contratos = [ContratoDossie(**c) for c in lido.vigentes]
    identidade = lido.fornecedor or {"cnpj": cnpj, "razao_social": None, "uf_sede": None}
    return Dossie(
        fornecedor=Fornecedor(**identidade),
        resumo_por_uf=[ResumoUf(**r) for r in lido.resumo],
        contratos_vigentes=contratos,
        vencendo_180d=[
            c for c in contratos if c.vigencia_fim is not None and c.vigencia_fim <= limite_vencendo
        ],
        sancoes=[
            SancaoDossie(**s, vigente=sancao_vigente(s["data_inicio"], s["data_fim"], hoje))
            for s in lido.sancoes
        ],
        sinais=[SinalDossie(**s) for s in lido.sinais],
        socios=None if lido.socios is None else [SocioDossie(**s) for s in lido.socios],
        fontes=lido.fontes,
    )
