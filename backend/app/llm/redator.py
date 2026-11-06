"""Redator em quarentena (SPEC §8.2) com verificador e modelo determinístico.

- Resultado vazio: abstenção pelo modelo determinístico, sem chamar a LLM.
- Sem provedor (modo mock): modelo determinístico.
- Com provedor: a LLM escreve com marcadores; o verificador aprova ou reprova. Reprovado ou provedor fora,
  a resposta é o modelo determinístico e o status vira "fallback".
O redator não tem ferramentas e não recebe o contexto de acesso: só a pergunta, os marcadores e o texto das
fontes marcado como dado não confiável.
"""

from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from typing import Literal

from app.llm.formatacao import valor_cru
from app.llm.marcadores import Material, montar_material
from app.llm.providers import ProvedorIndisponivel, ProvedorLLM
from app.llm.verificador import MARCADOR, preencher, verificar
from app.modules.catalogo.executor import ResultadoConsulta

VERSAO_PROMPT = "redator_v1"
TEMPERATURA = 0.2

StatusRedacao = Literal["aprovado", "fallback", "abstencao"]


@dataclass(frozen=True)
class RespostaRedigida:
    texto: str
    status: StatusRedacao
    motivos: tuple[str, ...]
    # Para o recibo: marcador → {valor cru, tipo, origem} (contracts/recibo.schema.json, "valores").
    valores: dict[str, dict[str, str]]
    versao_prompt: str
    modelo: str | None
    por_modelo_deterministico: bool


@cache
def _modelo_prompt() -> str:
    texto = (Path(__file__).parent / "prompts" / f"{VERSAO_PROMPT}.md").read_text(encoding="utf-8")
    return texto.split("-->", 1)[1].lstrip() if texto.startswith("<!--") else texto


def montar_prompt(pergunta: str, material: Material) -> str:
    marcadores = "\n".join(f"{{{{{m.id}}}}}: {m.significado}" for m in material.marcadores.values())
    resultado = "\n".join(material.registros) or "(sem registros de texto; use os marcadores)"
    # A pergunta entra por último, para que um "{{...}}" digitado pelo usuário não seja trocado.
    return (
        _modelo_prompt()
        .replace("{{marcadores}}", marcadores)
        .replace("{{resultado}}", resultado)
        .replace("{{pergunta}}", pergunta)
    )


def _anos_do_plano(resultado: ResultadoConsulta) -> set[int]:
    return {v.year for k, v in resultado.parametros.items() if k.startswith("data_") and isinstance(v, date)}


def _valores(material: Material, texto_com_marcadores: str) -> dict[str, dict[str, str]]:
    usados = dict.fromkeys(MARCADOR.findall(texto_com_marcadores))
    return {
        mid: {"valor": valor_cru(m.valor), "tipo": m.tipo, "origem": m.origem}
        for mid, m in material.marcadores.items()
        if mid in usados
    }


def _deterministico(
    material: Material, status: StatusRedacao, motivos: tuple[str, ...], modelo: str | None
) -> RespostaRedigida:
    return RespostaRedigida(
        texto=preencher(material.modelo, material.marcadores),
        status=status,
        motivos=motivos,
        valores=_valores(material, material.modelo),
        versao_prompt=VERSAO_PROMPT,
        modelo=modelo,
        por_modelo_deterministico=True,
    )


def redigir(
    pergunta: str,
    resultado: ResultadoConsulta,
    *,
    ufs_autorizadas: tuple[str, ...],
    provedor: ProvedorLLM | None,
    timeout_s: float = 20.0,
) -> RespostaRedigida:
    material = montar_material(resultado)
    if material.vazio:
        return _deterministico(material, "abstencao", ("resultado_vazio",), None)
    if provedor is None:
        return _deterministico(material, "aprovado", (), None)

    try:
        bruto = provedor.gerar(
            montar_prompt(pergunta, material), json=False, timeout_s=timeout_s, temperatura=TEMPERATURA
        )
    except ProvedorIndisponivel:
        return _deterministico(material, "fallback", ("provedor_indisponivel",), provedor.modelo)

    v = verificar(
        bruto, material.marcadores, ufs_autorizadas=ufs_autorizadas, anos_permitidos=_anos_do_plano(resultado)
    )
    if not v.aprovado:
        return _deterministico(material, "fallback", v.motivos, provedor.modelo)
    return RespostaRedigida(
        texto=v.texto_final,
        status="aprovado",
        motivos=(),
        valores=_valores(material, bruto),
        versao_prompt=VERSAO_PROMPT,
        modelo=provedor.modelo,
        por_modelo_deterministico=False,
    )
