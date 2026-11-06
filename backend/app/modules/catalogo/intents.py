"""Intents do catálogo (SPEC §7): identificador, parâmetros e descrição curta para o prompt do planejador.

Só metadados. O SQL de cada intent fica em `sql/<intent>.sql`, e a execução no executor do catálogo.
"""

from dataclasses import dataclass
from typing import Literal

IntentId = Literal[
    "resumo_fornecedor",
    "contratos_vigentes",
    "contratos_vencendo",
    "pagamentos_periodo",
    "sancoes_fornecedor",
    "orgaos_fornecedor",
    "busca_objeto",
    "fila_carteira",
    "socios_sancionados",
    "fora_de_escopo",
    "esclarecer",
]

UFS = frozenset("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split())


@dataclass(frozen=True)
class Intent:
    id: IntentId
    descricao: str
    obrigatorios: tuple[str, ...] = ()
    opcionais: tuple[str, ...] = ()


_LISTA = [
    Intent(
        "resumo_fornecedor",
        "Nº de contratos, valor contratado e valor pago, por UF e órgão",
        ("cnpj",),
        ("uf",),
    ),
    Intent("contratos_vigentes", "Contratos com vigência até hoje ou depois", ("cnpj",), ("uf",)),
    Intent(
        "contratos_vencendo",
        "Contratos vigentes que terminam em até 'dias' dias (padrão 180), com % do valor vigente",
        ("cnpj",),
        ("dias", "uf"),
    ),
    Intent(
        "pagamentos_periodo",
        "Pagamentos ao fornecedor entre data_inicio e data_fim, com total",
        ("cnpj", "data_inicio", "data_fim"),
        ("uf",),
    ),
    Intent("sancoes_fornecedor", "Sanções CEIS/CNEP vigentes e passadas do fornecedor", ("cnpj",)),
    Intent(
        "orgaos_fornecedor", "Ranking de órgãos por valor e participação (concentração)", ("cnpj",), ("uf",)
    ),
    Intent(
        "busca_objeto",
        "Contratos cujo objeto casa com o termo (texto, até 80 caracteres)",
        ("termo",),
        ("uf",),
    ),
    Intent(
        "fila_carteira", "Fornecedores da carteira ordenados por prioridade, com sinais", ("carteira_id",)
    ),
    Intent("socios_sancionados", "Sócios em comum com empresas sancionadas", ("cnpj",)),
    Intent(
        "fora_de_escopo", "Pergunta fora do catálogo ou pedido não permitido; gera abstenção", (), ("motivo",)
    ),
    Intent(
        "esclarecer",
        "Falta informação essencial; devolve uma pergunta ao usuário",
        (),
        ("pergunta_de_volta",),
    ),
]

INTENTS: dict[str, Intent] = {i.id: i for i in _LISTA}


def descrever_catalogo() -> str:
    """Texto do catálogo para o prompt do planejador. Não contém nenhum dado do banco."""
    linhas = []
    for i in _LISTA:
        params = [*i.obrigatorios, *(f"{p}?" for p in i.opcionais)]
        linhas.append(f"- {i.id}({', '.join(params)}): {i.descricao}")
    return "\n".join(linhas)
