"""Carteiras do tenant e fila priorizada por sinais (SPEC §3.3 I3, §9)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from psycopg.rows import dict_row

from app.core.cnpj import cnpj_valido, normalizar_cnpj
from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.core.errors import ErroApi
from app.modules.auditoria import service as auditoria
from app.modules.carteiras import queries
from app.modules.carteiras.prioridade import prioridade
from app.modules.carteiras.schemas import (
    CarteiraCriada,
    CarteiraEntrada,
    CarteiraListada,
    CarteiraResumo,
    Fila,
    ItemFila,
    SinalFila,
)

LIMITE_LISTAGEM = 200


def separar_cnpjs(brutos: list[str]) -> tuple[list[str], list[str]]:
    """(válidos sem máscara e sem repetição, na ordem em que vieram; inválidos como vieram, sem repetição)."""
    validos: dict[str, None] = {}
    invalidos: dict[str, None] = {}
    for bruto in brutos:
        cnpj = normalizar_cnpj(bruto)
        if cnpj_valido(cnpj):
            validos[cnpj] = None
        elif bruto.strip():
            invalidos[bruto.strip()] = None
    return list(validos), list(invalidos)


def criar(ctx: ContextoAcesso, entrada: CarteiraEntrada) -> CarteiraCriada:
    validos, invalidos = separar_cnpjs(entrada.cnpjs)
    with sessao(ctx) as conn:
        linha = conn.execute(
            queries.INSERIR_CARTEIRA, {"nome": entrada.nome, "finalidade": entrada.finalidade}
        ).fetchone()
        assert linha is not None
        carteira_id: UUID = linha[0]
        conn.cursor().executemany(
            queries.INSERIR_ITEM, [{"carteira_id": carteira_id, "cnpj": c} for c in validos]
        )
        auditoria.registrar_em(
            conn,
            "carteira_criada",
            {
                "carteira_id": str(carteira_id),
                "finalidade": entrada.finalidade,
                "n_itens": len(validos),
                "n_invalidos": len(invalidos),
            },
        )
    return CarteiraCriada(
        id=carteira_id,
        nome=entrada.nome,
        finalidade=entrada.finalidade,
        n_itens=len(validos),
        cnpjs_invalidos=invalidos,
    )


def listar(ctx: ContextoAcesso) -> list[CarteiraListada]:
    with sessao(ctx) as conn:
        linhas = (
            conn.cursor(row_factory=dict_row)
            .execute(queries.LISTAR_CARTEIRAS, {"limite": LIMITE_LISTAGEM})
            .fetchall()
        )
    return [CarteiraListada(**linha) for linha in linhas]


def fila(ctx: ContextoAcesso, carteira_id: UUID, hoje: date) -> Fila:
    """Carteira de outro tenant responde 404, igual a inexistente (a RLS não devolve a linha)."""
    with sessao(ctx) as conn:
        cur = conn.cursor(row_factory=dict_row)
        carteira = cur.execute(queries.BUSCAR_CARTEIRA, {"id": carteira_id}).fetchone()
        if carteira is None:
            raise ErroApi(404, "NAO_ENCONTRADO", "Carteira não encontrada.")
        linhas = cur.execute(queries.FILA, {"id": carteira_id, "hoje": hoje}).fetchall()

    itens = []
    for linha in linhas:
        sinais = [SinalFila(**s) for s in linha["sinais"]]
        valor: Decimal = linha["valor_exposto"]
        itens.append(
            ItemFila(
                cnpj=linha["cnpj"],
                razao_social=linha["razao_social"],
                prioridade=prioridade((s.gravidade for s in sinais), valor),
                valor_exposto=valor,
                sinais=sinais,
            )
        )
    itens.sort(key=lambda i: (-i.prioridade, -i.valor_exposto, i.cnpj))
    return Fila(carteira=CarteiraResumo(**carteira), itens=itens)
