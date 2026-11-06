"""Executor do catálogo (SPEC §7): plano validado → SQL fixo, sob a sessão com contexto de acesso.

- A UF do plano é interseccionada com as UFs da sessão. Pedido fora do escopo vira ESCOPO_NEGADO.
- A RLS filtra de novo no banco: mesmo um parâmetro errado não traz linha fora do escopo.
- Totais vêm do SQL (funções de janela antes do LIMIT), então ficam certos mesmo com a lista truncada.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from psycopg.rows import dict_row

from app.core.cnpj import cnpj_valido
from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.core.errors import ErroApi
from app.llm.plano import PlanoConsulta
from app.modules.catalogo.registry import CONSULTAS, sql

LIMITE_LINHAS = 200
DIAS_PADRAO = 180
# Colunas de janela (iguais em todas as linhas) que viram totais e saem das linhas. Os nomes não podem
# coincidir com colunas de dado de nenhum conjunto: elas também seriam tiradas.
_COLUNAS_DE_TOTAL = (
    "total_linhas",
    "valor_total",
    "valor_vigente_total",
    "total_pagos",
    "total_empenhos",
    "valor_empenhado_total",
)


class IntentSemConsulta(ValueError):
    """A intent não consulta o banco (fora_de_escopo, esclarecer) ou ainda não tem SQL."""


@dataclass(frozen=True)
class ResultadoConsulta:
    intent: str
    versao: str
    parametros: dict[str, Any]
    conjuntos: dict[str, list[dict[str, Any]]]
    totais: dict[str, Any] = field(default_factory=dict)
    truncado: bool = False


def ufs_efetivas(uf_pedida: str | None, ctx: ContextoAcesso) -> tuple[str, ...]:
    if uf_pedida is None:
        return ctx.ufs
    if uf_pedida not in ctx.ufs:
        raise ErroApi(403, "ESCOPO_NEGADO", f"Você não tem acesso a dados de {uf_pedida}.")
    return (uf_pedida,)


def _parametros(plano: PlanoConsulta, ctx: ContextoAcesso, hoje: date, usa_uf: bool) -> dict[str, Any]:
    p = plano.parametros
    if p.cnpj is None or not cnpj_valido(p.cnpj):
        raise ErroApi(422, "ENTRADA_INVALIDA", "CNPJ inválido: confira os 14 dígitos.")
    params: dict[str, Any] = {"cnpj": p.cnpj, "hoje": hoje, "limite": LIMITE_LINHAS + 1}
    if usa_uf:
        params["ufs"] = list(ufs_efetivas(p.uf, ctx))
    if plano.intent == "contratos_vencendo":
        params["dias"] = p.dias or DIAS_PADRAO
    if plano.intent == "pagamentos_periodo":
        params["data_inicio"], params["data_fim"] = p.data_inicio, p.data_fim
    return params


def _separar_totais(linhas: list[dict[str, Any]]) -> dict[str, Any]:
    """Tira as colunas de janela das linhas e devolve os valores (iguais em todas as linhas)."""
    totais = {k: linhas[0][k] for k in _COLUNAS_DE_TOTAL if linhas and k in linhas[0]}
    for linha in linhas:
        for k in _COLUNAS_DE_TOTAL:
            linha.pop(k, None)
    return totais


def _percentual(parte: Decimal | None, todo: Decimal | None) -> Decimal | None:
    if not todo:
        return None
    return (Decimal(parte or 0) * 100 / todo).quantize(Decimal("0.01"), ROUND_HALF_UP)


def _totais(intent: str, conjuntos: dict[str, list[dict]], janelas: dict[str, dict]) -> dict[str, Any]:
    if intent == "resumo_fornecedor":
        grupos = conjuntos["por_uf_orgao"]
        contagens = {k: sum(g[k] for g in grupos) for k in ("n_contratos", "n_pagamentos", "n_empenhos")}
        valores = {
            k: sum((g[k] for g in grupos), Decimal(0))
            for k in ("valor_contratado", "valor_vigente", "valor_pago", "valor_empenhado")
        }
        return {**contagens, **valores}
    j = janelas.get("linhas", {})
    n = j.get("total_linhas", 0)
    if intent == "contratos_vigentes":
        return {"n_contratos": n, "valor_total": j.get("valor_total") or Decimal(0)}
    if intent == "contratos_vencendo":
        vencendo, vigente = j.get("valor_total") or Decimal(0), j.get("valor_vigente_total")
        return {
            "n_contratos": n,
            "valor_vencendo": vencendo,
            "valor_vigente_total": vigente,
            "percentual_do_vigente": _percentual(vencendo, vigente),
        }
    if intent == "pagamentos_periodo":
        # Empenho não é pagamento: n e valor contam só o que saiu; o empenhado vem à parte (SQL v2).
        return {
            "n_pagamentos": j.get("total_pagos", 0),
            "valor_total": j.get("valor_total") or Decimal(0),
            "n_empenhos": j.get("total_empenhos", 0),
            "valor_empenhado": j.get("valor_empenhado_total") or Decimal(0),
        }
    if intent == "sancoes_fornecedor":
        return {"n_sancoes": n, "n_vigentes": sum(1 for s in conjuntos["linhas"] if s["vigente"])}
    return {}


def executar(plano: PlanoConsulta, ctx: ContextoAcesso, hoje: date) -> ResultadoConsulta:
    consulta = CONSULTAS.get(plano.intent)
    if consulta is None:
        raise IntentSemConsulta(plano.intent)
    params = _parametros(plano, ctx, hoje, consulta.usa_uf)

    conjuntos: dict[str, list[dict[str, Any]]] = {}
    janelas: dict[str, dict[str, Any]] = {}
    truncado = False
    with sessao(ctx) as conn:
        cur = conn.cursor(row_factory=dict_row)
        for nome in consulta.conjuntos:
            linhas = cur.execute(sql(consulta.intent, nome), params).fetchall()
            if len(linhas) > LIMITE_LINHAS:
                linhas, truncado = linhas[:LIMITE_LINHAS], True
            janelas[nome] = _separar_totais(linhas)
            conjuntos[nome] = linhas

    efetivos = {k: v for k, v in params.items() if k != "limite"}
    return ResultadoConsulta(
        intent=consulta.intent,
        versao=consulta.id_versao,
        parametros=efetivos,
        conjuntos=conjuntos,
        totais=_totais(consulta.intent, conjuntos, janelas),
        truncado=truncado,
    )
