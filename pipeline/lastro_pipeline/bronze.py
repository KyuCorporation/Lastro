"""Camada bronze: cada resposta bruta vai para `data/raw/<fonte>/<data>/` e para `arquivos_brutos` (sha256).

Mesmo sha256 na mesma fonte não duplica arquivo nem linha: devolve o id já registrado.
"""

from pathlib import Path
from uuid import UUID

import psycopg

from lastro_pipeline.modelos import RespostaBruta

SQL_REGISTRAR = """
insert into arquivos_brutos (execucao_id, fonte_id, caminho, url_origem, sha256, bytes, coletado_em)
values (%(execucao_id)s, %(fonte_id)s, %(caminho)s, %(url_origem)s, %(sha256)s, %(bytes)s, %(coletado_em)s)
on conflict (fonte_id, sha256) do nothing
returning id
"""

SQL_EXISTENTE = "select id from arquivos_brutos where fonte_id = %(fonte_id)s and sha256 = %(sha256)s"


def salvar_em_disco(raw_dir: Path, fonte_id: str, resposta: RespostaBruta) -> Path:
    """Grava o arquivo bruto. O nome leva o prefixo do sha256 para não sobrescrever respostas diferentes."""
    destino = raw_dir / fonte_id / resposta.coletado_em.date().isoformat()
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{resposta.sha256[:12]}_{resposta.nome}"
    if not caminho.exists():
        caminho.write_bytes(resposta.conteudo)
    return caminho


def registrar(
    conn: psycopg.Connection, fonte_id: str, execucao_id: UUID, resposta: RespostaBruta, caminho: str
) -> UUID:
    params = {
        "execucao_id": execucao_id,
        "fonte_id": fonte_id,
        "caminho": caminho,
        "url_origem": resposta.url_origem,
        "sha256": resposta.sha256,
        "bytes": len(resposta.conteudo),
        "coletado_em": resposta.coletado_em,
    }
    linha = conn.execute(SQL_REGISTRAR, params).fetchone()
    if linha is None:
        linha = conn.execute(SQL_EXISTENTE, params).fetchone()
    assert linha is not None
    return linha[0]
