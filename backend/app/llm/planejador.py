"""Planejador (SPEC §8.1): pergunta → plano de consulta. Nunca recebe dado do banco.

Com LLM: monta o prompt versionado, valida a saída (normalizando o que é só formato) e tenta mais uma vez se
vier inválida; na segunda falha, ou com o provedor fora (ou em modo mock), usa o roteador por regras.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from uuid import UUID

from app.llm.plano import PlanoConsulta, PlanoInvalido, validar_plano
from app.llm.providers import ProvedorIndisponivel, ProvedorLLM
from app.llm.regras import planejar_por_regras
from app.modules.catalogo.intents import descrever_catalogo

VERSAO_PROMPT = "planejador_v1"
TENTATIVAS = 2
# Com menos tempo do que isto no orçamento da consulta, não vale começar uma chamada à LLM.
MARGEM_MINIMA_S = 2.0
PERGUNTA_REFORMULAR = "Não entendi o pedido. Pode reformular, com o CNPJ e o que quer saber?"


@dataclass(frozen=True)
class ResultadoPlanejamento:
    plano: PlanoConsulta
    por_regras: bool
    versao_prompt: str
    modelo: str | None


@cache
def _modelo_prompt() -> str:
    texto = (Path(__file__).parent / "prompts" / f"{VERSAO_PROMPT}.md").read_text(encoding="utf-8")
    return texto.split("-->", 1)[1].lstrip() if texto.startswith("<!--") else texto


def _neutralizar(pergunta: str) -> str:
    """A pergunta não pode fechar a tag que a delimita no prompt."""
    return pergunta.replace("<pergunta_usuario>", "").replace("</pergunta_usuario>", "")


def montar_prompt(pergunta: str, *, ufs: tuple[str, ...], hoje: date) -> str:
    return (
        _modelo_prompt()
        .replace("{{hoje}}", hoje.isoformat())
        .replace("{{ufs}}", ", ".join(ufs) or "nenhuma")
        .replace("{{catalogo}}", descrever_catalogo())
        .replace("{{pergunta}}", _neutralizar(pergunta))
    )


def planejar(
    pergunta: str,
    *,
    ufs: tuple[str, ...],
    hoje: date,
    provedor: ProvedorLLM | None,
    timeout_s: float = 20.0,
    restante: Callable[[], float] | None = None,
    carteira_id: UUID | None = None,
) -> ResultadoPlanejamento:
    """`restante`: segundos que sobram no orçamento da consulta. Cada tentativa recebe no máximo isso, e sem
    margem para uma tentativa o roteador por regras decide.

    `carteira_id`: a carteira escolhida como contexto da consulta. Não vai para o prompt; preenche o plano de
    `fila_carteira` depois."""
    if provedor is None:
        return ResultadoPlanejamento(
            planejar_por_regras(pergunta, hoje, carteira_id), True, VERSAO_PROMPT, None
        )

    prompt = montar_prompt(pergunta, ufs=ufs, hoje=hoje)
    for _ in range(TENTATIVAS):
        prazo = timeout_s if restante is None else min(timeout_s, restante())
        if prazo < MARGEM_MINIMA_S:
            break
        try:
            bruto = provedor.gerar(prompt, json=True, timeout_s=prazo, temperatura=0.0)
        except ProvedorIndisponivel:
            return ResultadoPlanejamento(
                planejar_por_regras(pergunta, hoje, carteira_id), True, VERSAO_PROMPT, None
            )
        try:
            return ResultadoPlanejamento(
                validar_plano(bruto, carteira_id), False, VERSAO_PROMPT, provedor.modelo
            )
        except PlanoInvalido:
            continue
    # Duas saídas fora do contrato, ou sem tempo para tentar: a pergunta não fica pior do que no modo mock (o roteador por regras decide,
    # e o recibo registra planejador_por_regras). O escopo continua vindo só da sessão.
    return ResultadoPlanejamento(planejar_por_regras(pergunta, hoje, carteira_id), True, VERSAO_PROMPT, None)
