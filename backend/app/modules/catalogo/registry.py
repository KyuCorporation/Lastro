"""Consultas executáveis do catálogo: intent → versão e conjuntos de SQL (`sql/<intent>.<conjunto>.sql`).

Só as intents N1 com SQL estão aqui. `fora_de_escopo` e `esclarecer` não consultam o banco.
"""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

PASTA_SQL = Path(__file__).parent / "sql"

# Colunas de proveniência que toda linha citável traz (AGENTS.md §3, regra 5).
PROVENIENCIA = (
    "id",
    "fonte_id",
    "id_origem",
    "url_origem",
    "coletado_em",
    "hash_conteudo",
    "arquivo_bruto_id",
)


@dataclass(frozen=True)
class ConsultaCatalogo:
    intent: str
    versao: str
    conjuntos: tuple[str, ...]
    # Conjuntos com linhas citáveis (têm proveniência). Os demais são derivados delas.
    citaveis: tuple[str, ...]
    usa_uf: bool = True

    @property
    def id_versao(self) -> str:
        return f"{self.intent}@{self.versao}"


CONSULTAS: dict[str, ConsultaCatalogo] = {
    c.intent: c
    for c in [
        ConsultaCatalogo(
            "resumo_fornecedor",
            "v1",
            ("por_uf_orgao", "contratos", "pagamentos"),
            ("contratos", "pagamentos"),
        ),
        ConsultaCatalogo("contratos_vigentes", "v1", ("linhas",), ("linhas",)),
        ConsultaCatalogo("contratos_vencendo", "v1", ("linhas",), ("linhas",)),
        ConsultaCatalogo("pagamentos_periodo", "v1", ("linhas",), ("linhas",)),
        ConsultaCatalogo("sancoes_fornecedor", "v1", ("linhas",), ("linhas",), usa_uf=False),
    ]
}


@cache
def sql(intent: str, conjunto: str) -> str:
    return (PASTA_SQL / f"{intent}.{conjunto}.sql").read_text(encoding="utf-8")
