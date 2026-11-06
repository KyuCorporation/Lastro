"""Trilha de auditoria com escrita concorrente: a ordem do seq tem de ser a ordem da cadeia de hashes.

Sem o lock antes do insert (queries.TRAVAR_CADEIA), o seq é sorteado antes do lock do trigger e duas
transações simultâneas encadeiam fora da ordem do seq: a verificação da cadeia (T16) acusaria quebra falsa.
"""

from concurrent.futures import ThreadPoolExecutor

from app.core.db import sessao
from app.modules.auditoria import service as auditoria
from app.modules.catalogo.tests.conftest import _superusuario

ESCRITAS = 40


def _quebras_desde(seq_inicial: int, tenant_id) -> list[int]:
    """Seqs novos cujo hash_anterior não é o hash do evento anterior (por seq) do mesmo tenant."""
    with _superusuario() as su:
        linhas = su.execute(
            """
            select seq, hash_anterior,
                   coalesce(lag(hash) over (order by seq), repeat('0', 64)) as anterior
              from auditoria
             where tenant_id = %s
             order by seq
            """,
            (tenant_id,),
        ).fetchall()
    return [seq for seq, hash_anterior, anterior in linhas if seq > seq_inicial and hash_anterior != anterior]


def test_escritas_simultaneas_mantem_seq_e_cadeia_na_mesma_ordem(ctx_ana):
    with _superusuario() as su:
        inicio = su.execute("select coalesce(max(seq), 0) from auditoria").fetchone()[0]

    def escrever(i: int) -> None:
        auditoria.registrar(ctx_ana, "consulta", {"teste": "cadeia_concorrente", "i": i})

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(escrever, range(ESCRITAS)))

    with sessao(None):  # só para garantir que o pool continua saudável depois da rajada
        pass
    assert _quebras_desde(inicio, ctx_ana.tenant_id) == []
