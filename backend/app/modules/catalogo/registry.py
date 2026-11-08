"""Consultas executáveis do catálogo: intent → versão e conjuntos de SQL (`sql/<intent>.<conjunto>.sql`).

Intents N1 e as N2 `orgaos_fornecedor` e `busca_objeto`. `fora_de_escopo` e `esclarecer` não consultam o banco.
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

    @property
    def id_versao(self) -> str:
        return f"{self.intent}@{self.versao}"


CONSULTAS: dict[str, ConsultaCatalogo] = {
    c.intent: c
    for c in [
        # v2 em resumo_fornecedor e pagamentos_periodo: empenho separado do pago (o recibo guarda a versão).
        ConsultaCatalogo(
            "resumo_fornecedor",
            "v2",
            ("por_uf_orgao", "contratos", "pagamentos"),
            ("contratos", "pagamentos"),
        ),
        ConsultaCatalogo("contratos_vigentes", "v1", ("linhas",), ("linhas",)),
        ConsultaCatalogo("contratos_vencendo", "v1", ("linhas",), ("linhas",)),
        ConsultaCatalogo("pagamentos_periodo", "v2", ("linhas",), ("linhas",)),
        ConsultaCatalogo("sancoes_fornecedor", "v1", ("linhas",), ("linhas",), usa_uf=False),
        ConsultaCatalogo("orgaos_fornecedor", "v1", ("ranking", "contratos"), ("contratos",)),
        ConsultaCatalogo("busca_objeto", "v1", ("linhas",), ("linhas",), usa_cnpj=False),
    ]
}


@cache
def sql(intent: str, conjunto: str) -> str:
    return (PASTA_SQL / f"{intent}.{conjunto}.sql").read_text(encoding="utf-8")
