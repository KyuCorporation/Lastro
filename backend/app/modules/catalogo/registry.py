"""Consultas executáveis do catálogo: intent → versão e conjuntos de SQL (`sql/<intent>.<conjunto>.sql`).

Intents N1 e as N2 `orgaos_fornecedor`, `busca_objeto` e `fila_carteira`. `fora_de_escopo` e `esclarecer` não
consultam o banco.
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
    usa_cnpj: bool = True
    usa_carteira: bool = False

    @property
    def id_versao(self) -> str:
        return f"{self.intent}@{self.versao}"


CONSULTAS: dict[str, ConsultaCatalogo] = {
    c.intent: c
    for c in [
        # v2 em resumo_fornecedor e pagamentos_periodo: empenho separado do pago (o recibo guarda a versão).
        # v3 em resumo_fornecedor e v2 em orgaos_fornecedor: os agregados por órgão deixam de ter limite de linhas.
        # v4 em resumo_fornecedor e v2 em contratos_vigentes e contratos_vencendo: situação da fonte (migration 009).
        ConsultaCatalogo(
            "resumo_fornecedor",
            "v4",
            ("por_uf_orgao", "contratos", "pagamentos"),
            ("contratos", "pagamentos"),
        ),
        ConsultaCatalogo("contratos_vigentes", "v2", ("linhas",), ("linhas",)),
        ConsultaCatalogo("contratos_vencendo", "v2", ("linhas",), ("linhas",)),
        ConsultaCatalogo("pagamentos_periodo", "v2", ("linhas",), ("linhas",)),
        ConsultaCatalogo("sancoes_fornecedor", "v2", ("linhas",), ("linhas",), usa_uf=False),
        ConsultaCatalogo("orgaos_fornecedor", "v2", ("ranking", "contratos"), ("contratos",)),
        ConsultaCatalogo("busca_objeto", "v3", ("linhas",), ("linhas",), usa_cnpj=False),
        # fila: um registro por fornecedor (derivado); contratos vigentes e sanções vigentes são as evidências.
        ConsultaCatalogo(
            "fila_carteira",
            "v1",
            ("fila", "contratos", "sancoes"),
            ("contratos", "sancoes"),
            usa_cnpj=False,
            usa_carteira=True,
        ),
    ]
}


@cache
def sql(intent: str, conjunto: str) -> str:
    return (PASTA_SQL / f"{intent}.{conjunto}.sql").read_text(encoding="utf-8")
