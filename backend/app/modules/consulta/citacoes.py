"""Linhas citáveis do resultado do catálogo → citações da resposta e linhas do recibo.

As citações vêm do código, nunca do texto da LLM (SPEC §3.2, D1): a LLM não pode escrever números, então
não escreve `[n]`. Cada citação aponta para uma linha com proveniência completa (AGENTS.md §3, regra 5).
"""

from typing import Any

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
}

# Quantas linhas viram citação na resposta. O recibo leva todas as linhas usadas.
LIMITE_CITACOES = 50

FONTE_SINTETICA = "demo_sintetico"


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
            "fonte_id": linha["fonte_id"],
            "url_origem": linha.get("url_origem"),
            "coletado_em": linha["coletado_em"],
        }
        for n, linha in enumerate(linhas[:limite], start=1)
    ]


def tem_dado_sintetico(linhas: list[dict[str, Any]]) -> bool:
    return any(linha["fonte_id"] == FONTE_SINTETICA for linha in linhas)
