"""Redator em quarentena (SPEC §8.2) com verificador e modelo determinístico.

Fluxo de `redigir`:
1. `montar_material`: marcadores e modelo determinístico da intent, a partir do resultado do catálogo.
2. Resultado vazio: abstenção pelo modelo determinístico, sem chamar a LLM.
3. Sem provedor (modo mock): modelo determinístico, status "aprovado".
4. Com provedor: a LLM escreve com marcadores; o texto é limpo do embrulho comum e o verificador aprova
   ou reprova. Reprovado, ou qualquer falha do provedor: modelo determinístico com status "fallback".

O redator não tem ferramentas e não recebe o contexto de acesso: só a pergunta (em quarentena), os
marcadores e o texto das fontes marcado como dado não confiável.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from functools import cache
from pathlib import Path
from typing import Literal

from app.llm.formatacao import valor_cru
from app.llm.marcadores import Material, montar_material
from app.llm.providers import ProvedorIndisponivel, ProvedorLLM
from app.llm.texto_externo import pergunta_do_usuario
from app.llm.verificador import MARCADOR, preencher, verificar
from app.modules.catalogo.executor import ResultadoConsulta

log = logging.getLogger("lastro.llm")

VERSAO_PROMPT = "redator_v2"
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
    provedor: str | None = None


# ------------------------------------------------------------------ prompt
_PLACEHOLDER = re.compile(r"\{\{(pergunta|marcadores|resultado)\}\}")


@cache
def _modelo_prompt(versao: str = VERSAO_PROMPT) -> str:
    texto = (Path(__file__).parent / "prompts" / f"{versao}.md").read_text(encoding="utf-8")
    return texto.split("-->", 1)[1].lstrip() if texto.startswith("<!--") else texto


def montar_prompt(pergunta: str, material: Material) -> str:
    """Uma passada só: nada do que é inserido (pergunta, texto de fonte) é relido como placeholder."""
    partes = {
        "pergunta": pergunta_do_usuario(pergunta),
        "marcadores": "\n".join(f"{{{{{m.id}}}}}: {m.significado}" for m in material.marcadores.values()),
        "resultado": "\n".join(material.registros) or "(sem registros de texto; use os marcadores)",
    }
    return _PLACEHOLDER.sub(lambda m: partes[m.group(1)], _modelo_prompt())


# ------------------------------------------------------------------ saída da LLM
_CERCA = re.compile(r"^```[\w-]*\s*\n?(.*?)\n?```$", re.DOTALL)
_ASPAS = (('"', '"'), ("“", "”"), ("'", "'"))


def limpar_saida(bruto: str) -> str:
    """Tira só o embrulho que a LLM costuma pôr (cerca de código, aspas em volta). Não mexe no conteúdo."""
    texto = bruto.strip()
    if cerca := _CERCA.match(texto):
        texto = cerca.group(1).strip()
    for abre, fecha in _ASPAS:
        if len(texto) >= 2 and texto.startswith(abre) and texto.endswith(fecha):
            texto = texto[len(abre) : -len(fecha)].strip()
            break
    return texto


# ------------------------------------------------------------------ respostas
def _anos_do_plano(resultado: ResultadoConsulta) -> set[int]:
    return {v.year for k, v in resultado.parametros.items() if k.startswith("data_") and isinstance(v, date)}


def _valores(material: Material, texto_com_marcadores: str) -> dict[str, dict[str, str]]:
    usados = dict.fromkeys(MARCADOR.findall(texto_com_marcadores))
    return {
        mid: {"valor": valor_cru(m.valor, m.tipo), "tipo": m.tipo, "origem": m.origem}
        for mid, m in material.marcadores.items()
        if mid in usados
    }


def _deterministico(
    material: Material, status: StatusRedacao, motivos: tuple[str, ...], provedor: ProvedorLLM | None
) -> RespostaRedigida:
    return RespostaRedigida(
        texto=preencher(material.modelo, material.marcadores),
        status=status,
        motivos=motivos,
        valores=_valores(material, material.modelo),
        versao_prompt=VERSAO_PROMPT,
        modelo=provedor.modelo if provedor else None,
        por_modelo_deterministico=True,
        provedor=provedor.nome if provedor else None,
    )


def redigir(
    pergunta: str,
    resultado: ResultadoConsulta,
    *,
    ufs_autorizadas: tuple[str, ...],
    provedor: ProvedorLLM | None,
    timeout_s: float = 20.0,
    fontes_coletadas_em: date | datetime | None = None,
) -> RespostaRedigida:
    """`fontes_coletadas_em`: coleta mais recente das fontes consultadas, citada na abstenção (SPEC §8.4)."""
    material = montar_material(resultado, fontes_coletadas_em=fontes_coletadas_em)
    if material.vazio:
        return _deterministico(material, "abstencao", ("resultado_vazio",), None)
    if provedor is None:
        return _deterministico(material, "aprovado", (), None)

    try:
        bruto = provedor.gerar(
            montar_prompt(pergunta, material), json=False, timeout_s=timeout_s, temperatura=TEMPERATURA
        )
    except ProvedorIndisponivel:
        return _deterministico(material, "fallback", ("provedor_indisponivel",), provedor)
    # Qualquer outra falha (SDK com defeito, resposta inesperada) também cai no fallback: a demo não pode
    # cair por causa da LLM (AGENTS.md §3.9).
    except Exception as erro:  # noqa: BLE001
        log.warning("redator: falha inesperada do provedor %s: %s", provedor.nome, type(erro).__name__)
        return _deterministico(material, "fallback", ("erro_provedor",), provedor)

    texto = limpar_saida(bruto if isinstance(bruto, str) else "")
    v = verificar(
        texto,
        material.marcadores,
        ufs_autorizadas=ufs_autorizadas,
        anos_permitidos=_anos_do_plano(resultado),
        essenciais=material.essenciais,
        resultado_vazio=material.vazio,
    )
    if not v.aprovado:
        return _deterministico(material, "fallback", v.motivos, provedor)
    return RespostaRedigida(
        texto=v.texto_final,
        status="aprovado",
        motivos=(),
        valores=_valores(material, texto),
        versao_prompt=VERSAO_PROMPT,
        modelo=provedor.modelo,
        por_modelo_deterministico=False,
        provedor=provedor.nome,
    )
