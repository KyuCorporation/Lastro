"""Acesso ao banco da pipeline (papel `lastro_ingest`). SQL explícito e parametrizado, sem ORM.

Idempotência: chave `(fonte_id, id_origem)`. Reingestão só atualiza a linha se `hash_conteudo` mudou;
`coletado_em` e `arquivo_bruto_id` mudam junto com o conteúdo, nunca sozinhos.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from lastro_pipeline.modelos import Contrato, Fato, Fornecedor, Orgao, Pagamento, Sancao


class Resultado(StrEnum):
    NOVO = "novo"
    ATUALIZADO = "atualizado"
    INALTERADO = "inalterado"


def conectar(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url, autocommit=True, connect_timeout=10)


# ===================== Execuções =====================

SQL_ABRIR_EXECUCAO = """
insert into execucoes_ingestao (fonte_id, parametros, iniciada_em)
values (%(fonte_id)s, %(parametros)s, clock_timestamp())
returning id
"""

SQL_FECHAR_EXECUCAO = """
update execucoes_ingestao
   set finalizada_em = clock_timestamp(), status = %(status)s, parametros = %(parametros)s,
       registros_lidos = %(lidos)s, registros_novos = %(novos)s,
       registros_atualizados = %(atualizados)s, registros_descartados = %(descartados)s, erro = %(erro)s
 where id = %(id)s
"""

SQL_ULTIMA_EXECUCAO = """
select registros_lidos
  from execucoes_ingestao
 where fonte_id = %(fonte_id)s and status in ('ok', 'parcial') and id <> %(id)s
   and parametros -> 'filtros' = %(filtros)s
 order by iniciada_em desc
 limit 1
"""


@dataclass
class Contagem:
    lidos: int = 0
    novos: int = 0
    atualizados: int = 0
    descartados: int = 0

    def somar(self, resultado: Resultado) -> None:
        if resultado is Resultado.NOVO:
            self.novos += 1
        elif resultado is Resultado.ATUALIZADO:
            self.atualizados += 1


def abrir_execucao(conn: psycopg.Connection, fonte_id: str, parametros: dict[str, Any]) -> UUID:
    linha = conn.execute(
        SQL_ABRIR_EXECUCAO, {"fonte_id": fonte_id, "parametros": Jsonb(parametros)}
    ).fetchone()
    assert linha is not None
    return linha[0]


def fechar_execucao(
    conn: psycopg.Connection,
    execucao_id: UUID,
    status: str,
    contagem: Contagem,
    parametros: dict[str, Any],
    erro: str | None = None,
) -> None:
    conn.execute(
        SQL_FECHAR_EXECUCAO,
        {
            "id": execucao_id,
            "status": status,
            "parametros": Jsonb(parametros),
            "lidos": contagem.lidos,
            "novos": contagem.novos,
            "atualizados": contagem.atualizados,
            "descartados": contagem.descartados,
            "erro": erro,
        },
    )


def lidos_na_execucao_anterior(
    conn: psycopg.Connection, fonte_id: str, execucao_id: UUID, filtros: dict[str, Any]
) -> int | None:
    """Volume da última execução comparável (mesma fonte e mesmos filtros), para detectar queda."""
    linha = conn.execute(
        SQL_ULTIMA_EXECUCAO, {"fonte_id": fonte_id, "id": execucao_id, "filtros": Jsonb(filtros)}
    ).fetchone()
    return None if linha is None else linha[0]


# ===================== Dimensões =====================

SQL_UPSERT_ORGAO = """
insert into orgaos (id, nome, uf, esfera) values (%(id)s, %(nome)s, %(uf)s, %(esfera)s)
on conflict (id) do update set nome = excluded.nome, uf = excluded.uf, esfera = excluded.esfera
 where (orgaos.nome, orgaos.uf, orgaos.esfera) is distinct from (excluded.nome, excluded.uf, excluded.esfera)
"""

SQL_UPSERT_FORNECEDOR = """
insert into fornecedores (cnpj, razao_social, uf_sede) values (%(cnpj)s, %(razao_social)s, %(uf_sede)s)
on conflict (cnpj) do update
   set razao_social = coalesce(excluded.razao_social, fornecedores.razao_social),
       uf_sede = coalesce(excluded.uf_sede, fornecedores.uf_sede),
       atualizado_em = now()
 where (fornecedores.razao_social is null and excluded.razao_social is not null)
    or (fornecedores.uf_sede is null and excluded.uf_sede is not null)
"""


def gravar_orgao(conn: psycopg.Connection, orgao: Orgao) -> None:
    conn.execute(SQL_UPSERT_ORGAO, orgao.model_dump())


def gravar_fornecedor(conn: psycopg.Connection, fornecedor: Fornecedor) -> None:
    conn.execute(SQL_UPSERT_FORNECEDOR, fornecedor.model_dump())


# ===================== Fatos =====================
# `xmax = 0` distingue insert de update; sem linha devolvida = conteúdo igual, nada mudou.

_PROVENIENCIA = ("url_origem", "arquivo_bruto_id", "coletado_em", "hash_conteudo")


def _sql_upsert_fato(tabela: str, colunas: tuple[str, ...]) -> str:
    todas = ("fonte_id", "id_origem", *colunas, *_PROVENIENCIA)
    nomes = ", ".join(todas)
    valores = ", ".join(f"%({c})s" for c in todas)
    atualizar = ", ".join(f"{c} = excluded.{c}" for c in (*colunas, *_PROVENIENCIA))
    return (
        f"insert into {tabela} ({nomes}) values ({valores}) "
        f"on conflict (fonte_id, id_origem) do update set {atualizar} "
        f"where {tabela}.hash_conteudo is distinct from excluded.hash_conteudo "
        "returning (xmax = 0) as inserido"
    )


_COLUNAS: dict[type[Fato], tuple[str, ...]] = {
    Contrato: (
        "uf",
        "orgao_id",
        "fornecedor_cnpj",
        "objeto",
        "valor_global",
        "data_assinatura",
        "vigencia_inicio",
        "vigencia_fim",
    ),
    Pagamento: ("uf", "orgao_id", "fornecedor_cnpj", "data_pagamento", "valor", "descricao"),
    Sancao: (
        "cnpj",
        "tipo",
        "orgao_sancionador",
        "uf_orgao",
        "data_inicio",
        "data_fim",
        "fundamentacao",
    ),
}

SQL_UPSERT_FATO: dict[type[Fato], str] = {
    modelo: _sql_upsert_fato(modelo.tabela, colunas) for modelo, colunas in _COLUNAS.items()
}


def gravar_fato(
    conn: psycopg.Connection, fato: Fato, arquivo_bruto_id: UUID, coletado_em: datetime
) -> Resultado:
    params = fato.model_dump()
    params.update(
        arquivo_bruto_id=arquivo_bruto_id, coletado_em=coletado_em, hash_conteudo=fato.hash_conteudo
    )
    linha = conn.execute(SQL_UPSERT_FATO[type(fato)], params).fetchone()
    if linha is None:
        return Resultado.INALTERADO
    return Resultado.NOVO if linha[0] else Resultado.ATUALIZADO
