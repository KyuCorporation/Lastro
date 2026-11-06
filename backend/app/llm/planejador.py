"""Planejador (SPEC §8.1): pergunta → plano de consulta. Nunca recebe dado do banco.

Com LLM: monta o prompt versionado, valida a saída (normalizando o que é só formato) e tenta mais uma vez se
vier inválida; na segunda falha, ou com o provedor fora (ou em modo mock), usa o roteador por regras.
"""

from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path

from app.llm.plano import PlanoConsulta, PlanoInvalido, validar_plano
from app.llm.providers import ProvedorIndisponivel, ProvedorLLM
from app.llm.regras import planejar_por_regras
from app.modules.catalogo.intents import descrever_catalogo

VERSAO_PROMPT = "planejador_v1"
TENTATIVAS = 2
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
) -> ResultadoPlanejamento:
    if provedor is None:
        return ResultadoPlanejamento(planejar_por_regras(pergunta, hoje), True, VERSAO_PROMPT, None)

    prompt = montar_prompt(pergunta, ufs=ufs, hoje=hoje)
    for _ in range(TENTATIVAS):
        try:
            bruto = provedor.gerar(prompt, json=True, timeout_s=timeout_s, temperatura=0.0)
        except ProvedorIndisponivel:
            return ResultadoPlanejamento(planejar_por_regras(pergunta, hoje), True, VERSAO_PROMPT, None)
        try:
            return ResultadoPlanejamento(validar_plano(bruto), False, VERSAO_PROMPT, provedor.modelo)
        except PlanoInvalido:
            continue
    # Duas saídas fora do contrato: a pergunta não fica pior do que no modo mock (o roteador por regras decide,
    # e o recibo registra planejador_por_regras). O escopo continua vindo só da sessão.
    return ResultadoPlanejamento(planejar_por_regras(pergunta, hoje), True, VERSAO_PROMPT, None)
