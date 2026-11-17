"""Linhas citáveis do resultado do catálogo → citações da resposta e linhas do recibo.

As citações vêm do código, nunca do texto da LLM (SPEC §3.2, D1): a LLM não pode escrever números, então
não escreve `[n]`. Cada citação aponta para uma linha com proveniência completa (AGENTS.md §3, regra 5).
"""

from typing import Any

from app.llm.formatacao import formatar
from app.llm.texto_externo import limpar
from app.modules.catalogo.executor import ResultadoConsulta
from app.modules.catalogo.registry import CONSULTAS

# Tabela de origem de cada conjunto citável do catálogo. Consulta nova no catálogo precisa entrar aqui
# (o teste test_toda_consulta_citavel_tem_tabela acusa).
TABELA_DO_CONJUNTO: dict[tuple[str, str], str] = {
    ("resumo_fornecedor", "contratos"): "contratos",
    ("resumo_fornecedor", "pagamentos"): "pagamentos",
    ("contratos_vigentes", "linhas"): "contratos",
    ("contratos_vencendo", "linhas"): "contratos",
    ("pagamentos_periodo", "linhas"): "pagamentos",
    ("sancoes_fornecedor", "linhas"): "sancoes",
    ("orgaos_fornecedor", "contratos"): "contratos",
    ("busca_objeto", "linhas"): "contratos",
}

# Quantas linhas viram citação na resposta. O recibo leva todas as linhas usadas.
LIMITE_CITACOES = 50

FONTE_SINTETICA = "demo_sintetico"

# Texto de fonte no resumo: sem link nem marcação (texto_externo.limpar), números mantidos (nome de órgão tem número).
LIMITE_TEXTO_RESUMO = 80


def _texto(valor: object) -> str | None:
    limpo = limpar(valor, limite=LIMITE_TEXTO_RESUMO, mascarar_numeros=False) if valor else ""
    return limpo or None


def _resumo(linha: dict[str, Any]) -> str:
    """Uma linha legível do registro citado, montada pelo código (nunca pela LLM)."""
    tabela = linha["tabela"]
    if tabela == "contratos":
        orgao = _texto(linha.get("orgao_nome"))
        valor, fim = linha.get("valor_global"), linha.get("vigencia_fim")
        partes = [
            f"Contrato com {orgao}" if orgao else "Contrato",
            formatar(valor, "moeda") if valor is not None else None,
            f"até {formatar(fim, 'data')}" if fim else None,
        ]
    elif tabela == "pagamentos":
        origem = str(linha.get("id_origem") or "")
        nome = (
            "Empenho"
            if origem.startswith("emp:")
            else "Liquidação"
            if origem.startswith("liq:")
            else "Pagamento"
        )
        valor, dia = linha.get("valor"), linha.get("data_pagamento")
        cabeca = nome + (f" de {formatar(valor, 'moeda')}" if valor is not None else "")
        cabeca += f" em {formatar(dia, 'data')}" if dia else ""
        partes = [cabeca, _texto(linha.get("orgao_nome"))]
    elif tabela == "sancoes":
        tipo, fim = _texto(linha.get("tipo")), linha.get("data_fim")
        partes = [
            f"Sanção: {tipo}" if tipo else "Sanção",
            _texto(linha.get("orgao_sancionador")),
            f"até {formatar(fim, 'data')}" if fim else "sem data final",
        ]
    else:
        partes = [tabela]
    return " · ".join(p for p in partes if p)


def linhas_citaveis(resultado: ResultadoConsulta) -> list[dict[str, Any]]:
    """Linhas com proveniência, na ordem do catálogo, cada uma com a tabela de origem."""
    linhas: list[dict[str, Any]] = []
    for conjunto in CONSULTAS[resultado.intent].citaveis:
        tabela = TABELA_DO_CONJUNTO[(resultado.intent, conjunto)]
        linhas += [{**linha, "tabela": tabela} for linha in resultado.conjuntos.get(conjunto, [])]
    return linhas


def citacoes(linhas: list[dict[str, Any]], limite: int = LIMITE_CITACOES) -> list[dict[str, Any]]:
    return [
        {
            "n": n,
            "tabela": linha["tabela"],
            "id": str(linha["id"]),
            "id_origem": linha["id_origem"],
            "resumo": _resumo(linha),
            "fonte_id": linha["fonte_id"],
            "url_origem": linha.get("url_origem"),
            "coletado_em": linha["coletado_em"],
        }
        for n, linha in enumerate(linhas[:limite], start=1)
    ]


def tem_dado_sintetico(linhas: list[dict[str, Any]]) -> bool:
    return any(linha["fonte_id"] == FONTE_SINTETICA for linha in linhas)
