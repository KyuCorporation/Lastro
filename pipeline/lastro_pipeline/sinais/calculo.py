"""Recálculo dos sinais no banco (papel `lastro_ingest`). SQL explícito e parametrizado.

Idempotente: o mesmo fornecedor, UF e tipo atualiza a mesma linha (o `id` do sinal fica estável, então um alerta
que aponte para ele continua válido); sinal que deixou de valer é apagado; sinal novo é inserido. Tudo numa
transação com lock consultivo, então dois `make sinais` ao mesmo tempo não se misturam e quem lê nunca vê a
tabela pela metade.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from lastro_pipeline.sinais.regras import (
    CONCENTRACAO_MESES,
    TIPOS_CALCULADOS,
    VERSAO_REGRA,
    ContratoFato,
    PagamentoFato,
    SancaoFato,
    Sinal,
    calcular_todos,
    subtrair_meses,
)

log = logging.getLogger(__name__)

SQL_TRAVAR = "select pg_advisory_xact_lock(hashtext('lastro_sinais'))"

# Só o que as regras usam: contratos que ainda podem estar vigentes ou foram assinados na janela da concentração.
SQL_CONTRATOS = """
select id, fornecedor_cnpj, uf, orgao_id, valor_global, data_assinatura, vigencia_inicio, vigencia_fim, url_origem
  from contratos
 where vigencia_fim >= %(hoje)s
    or coalesce(data_assinatura, vigencia_inicio) between %(inicio)s and %(hoje)s
"""

# Empenho (id_origem 'emp:', TCE-PE) não é recebimento: mesmo critério do catálogo (resumo_fornecedor@v2).
SQL_PAGAMENTOS = """
select id, fornecedor_cnpj, uf, orgao_id, valor, data_pagamento, url_origem
  from pagamentos
 where id_origem not like 'emp:%%'
   and data_pagamento between %(inicio)s and %(hoje)s
"""

SQL_SANCOES = """
select id, fonte_id, cnpj, tipo, data_inicio, data_fim, url_origem
  from sancoes
 where (data_inicio is null or data_inicio <= %(hoje)s)
   and (data_fim is null or data_fim >= %(hoje)s)
"""

SQL_ORGAOS = "select id, nome from orgaos"

SQL_SINAIS_EXISTENTES = """
select id, fornecedor_cnpj, uf, tipo
  from sinais
 where tipo = any(%(tipos)s)
"""

SQL_INSERIR = """
insert into sinais (fornecedor_cnpj, uf, tipo, gravidade, valor, explicacao, evidencias, versao_regra, calculado_em)
values (%(fornecedor_cnpj)s, %(uf)s, %(tipo)s, %(gravidade)s, %(valor)s, %(explicacao)s, %(evidencias)s,
        %(versao_regra)s, now())
"""

SQL_ATUALIZAR = """
update sinais
   set gravidade = %(gravidade)s, valor = %(valor)s, explicacao = %(explicacao)s, evidencias = %(evidencias)s,
       versao_regra = %(versao_regra)s, calculado_em = now()
 where id = %(id)s
"""

SQL_APAGAR = "delete from sinais where id = %(id)s"

# Trilha global (tenant nulo): a política auditoria_ingest só deixa a pipeline gravar aí.
SQL_AUDITAR = """
insert into auditoria (tenant_id, usuario_id, evento, detalhes, hash_anterior, hash)
values (null, null, 'sinais_recalculados', %(detalhes)s, '', '')
"""


@dataclass(frozen=True)
class ResumoSinais:
    hoje: date
    novos: int
    atualizados: int
    apagados: int
    mantidos_por_alerta: int
    por_tipo: dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.por_tipo.values())


def _ler_fatos(
    conn: psycopg.Connection, hoje: date
) -> tuple[list[ContratoFato], list[PagamentoFato], list[SancaoFato], dict[str, str]]:
    params = {"hoje": hoje, "inicio": subtrair_meses(hoje, CONCENTRACAO_MESES)}
    contratos = [ContratoFato(*linha) for linha in conn.execute(SQL_CONTRATOS, params)]
    pagamentos = [PagamentoFato(*linha) for linha in conn.execute(SQL_PAGAMENTOS, params)]
    sancoes = [SancaoFato(*linha) for linha in conn.execute(SQL_SANCOES, params)]
    orgaos = {id_: nome for id_, nome in conn.execute(SQL_ORGAOS)}
    return contratos, pagamentos, sancoes, orgaos


def _parametros(sinal: Sinal) -> dict[str, Any]:
    return {
        "fornecedor_cnpj": sinal.fornecedor_cnpj,
        "uf": sinal.uf,
        "tipo": sinal.tipo,
        "gravidade": sinal.gravidade,
        "valor": sinal.valor,
        "explicacao": sinal.explicacao,
        "evidencias": Jsonb(sinal.evidencias),
        "versao_regra": sinal.versao_regra,
    }


def _apagar(conn: psycopg.Connection, sinal_id: UUID) -> bool:
    """Apaga um sinal que deixou de valer. Se um alerta (T28) ainda aponta para ele, o banco recusa: fica."""
    try:
        with conn.transaction():
            conn.execute(SQL_APAGAR, {"id": sinal_id})
        return True
    except psycopg.errors.ForeignKeyViolation:
        log.warning("sinal %s deixou de valer, mas um alerta aponta para ele; mantido", sinal_id)
        return False


def gravar(conn: psycopg.Connection, sinais: list[Sinal]) -> tuple[int, int, int, int]:
    """Sincroniza a tabela com a lista calculada. Devolve (novos, atualizados, apagados, mantidos_por_alerta)."""
    existentes: dict[tuple[str, str | None, str], list[UUID]] = {}
    for id_, cnpj, uf, tipo in conn.execute(SQL_SINAIS_EXISTENTES, {"tipos": list(TIPOS_CALCULADOS)}):
        existentes.setdefault((cnpj, uf, tipo), []).append(id_)

    novos = atualizados = 0
    for sinal in sinais:
        ids = existentes.pop(sinal.chave, [])
        if ids:
            conn.execute(SQL_ATUALIZAR, {**_parametros(sinal), "id": ids[0]})
            atualizados += 1
            ids = ids[1:]  # duplicata de uma versão anterior: some junto com os obsoletos
            if ids:
                existentes[sinal.chave] = ids
        else:
            conn.execute(SQL_INSERIR, _parametros(sinal))
            novos += 1

    apagados = mantidos = 0
    for ids in existentes.values():
        for sinal_id in ids:
            if _apagar(conn, sinal_id):
                apagados += 1
            else:
                mantidos += 1
    return novos, atualizados, apagados, mantidos


def recalcular(conn: psycopg.Connection, hoje: date) -> ResumoSinais:
    """Lê os fatos, aplica as regras v1 e grava. `hoje` é parâmetro para os testes serem determinísticos."""
    with conn.transaction():
        conn.execute(SQL_TRAVAR)
        contratos, pagamentos, sancoes, orgaos = _ler_fatos(conn, hoje)
        sinais = calcular_todos(contratos, pagamentos, sancoes, hoje, orgaos)
        novos, atualizados, apagados, mantidos = gravar(conn, sinais)
        por_tipo = {tipo: sum(1 for s in sinais if s.tipo == tipo) for tipo in TIPOS_CALCULADOS}
        resumo = ResumoSinais(hoje, novos, atualizados, apagados, mantidos, por_tipo)
        conn.execute(
            SQL_AUDITAR,
            {
                "detalhes": Jsonb(
                    {
                        "versao_regra": VERSAO_REGRA,
                        "hoje": hoje.isoformat(),
                        "por_tipo": por_tipo,
                        "novos": novos,
                        "atualizados": atualizados,
                        "apagados": apagados,
                        "mantidos_por_alerta": mantidos,
                    }
                )
            },
        )
    return resumo
