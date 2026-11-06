"""Checagens por código antes do planejador (SPEC §8.5, Plan-Then-Execute).

Não dependem da LLM: mesmo com o Gemini planejando, um pedido de outra UF não vira resposta com dados da UF
do usuário, e um pedido para burlar as regras nem chega ao planejador.
"""

from dataclasses import dataclass, field
from typing import Any

from app.core.contexto import ContextoAcesso
from app.llm.regras import FORA_DO_PERMITIDO, normalizar, ufs_mencionadas

MENSAGEM_FORA_DO_PERMITIDO = "Esse pedido está fora do que você pode consultar."


@dataclass(frozen=True)
class Negacao:
    motivo: str  # vai para auditoria.detalhes.motivo
    mensagem: str  # vai para o usuário; nunca diz quantos registros existem fora do escopo
    detalhes: dict[str, Any] = field(default_factory=dict)


def mensagem_escopo(ufs: list[str]) -> str:
    return f"Você não tem acesso a dados de {', '.join(ufs)}."


def _ufs_citadas(pergunta: str) -> set[str]:
    # Texto todo em maiúsculas faria "SE", "TO", "PA" parecerem siglas: aí só valem os nomes dos estados.
    return ufs_mencionadas(pergunta.lower() if pergunta.isupper() else pergunta)


def checar_pergunta(pergunta: str, ctx: ContextoAcesso) -> Negacao | None:
    if FORA_DO_PERMITIDO.search(normalizar(pergunta)):
        return Negacao("pedido_fora_do_permitido", MENSAGEM_FORA_DO_PERMITIDO)
    if fora := sorted(_ufs_citadas(pergunta) - set(ctx.ufs)):
        return Negacao("uf_fora_do_escopo", mensagem_escopo(fora), {"ufs_pedidas": fora})
    return None
