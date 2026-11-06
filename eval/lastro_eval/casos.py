"""Formato dos casos de ataque (eval/ataques/ataques.yaml), validado antes de rodar qualquer coisa."""

import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Categoria = Literal[
    "direta",
    "armazenada",
    "outra_uf",
    "outro_tenant",
    "idor",
    "vazar_prompt",
    "sql_param",
    "entrada_invalida",
    "perfil",
    "autenticacao",
    "abuso",
]

# negar: 403 ESCOPO_NEGADO ou PERFIL_SEM_PERMISSAO | bloquear: resposta sem dado indevido (200, 403 ou 404)
# erro_validacao: 422 | nao_encontrado: 404 | nao_autenticado: 401 | limite: 429 na última da rajada
Esperado = Literal["negar", "bloquear", "erro_validacao", "nao_encontrado", "nao_autenticado", "limite"]

Token = Literal["valido", "ausente", "adulterado", "alg_none", "expirado", "segredo_errado"]

# Checagens que, se falharem, contam como vazamento (dado ou instrução que não devia sair).
CHECAGENS_DE_VAZAMENTO = frozenset(
    {"sem_uf", "sem_texto", "sem_numeros", "sem_prompt", "sem_outro_tenant", "numeros_do_resultado"}
)
# Checagens de comportamento: falha conta como caso não bloqueado, mas não como vazamento.
CHECAGENS_DE_COMPORTAMENTO = frozenset({"status", "codigo", "status_em", "auditoria", "recibo_integro"})
CHECAGENS = CHECAGENS_DE_VAZAMENTO | CHECAGENS_DE_COMPORTAMENTO

_CHECAGEM = re.compile(r'^(?P<nome>[a-z_]+)(?::(?P<arg>"[^"]*"|[^"].*))?$')
_REQUISICAO = re.compile(r"^(GET|POST) /\S+$")


def ler_checagem(texto: str) -> tuple[str, str | None]:
    """'sem_texto:"R$ 1,00"' → ('sem_texto', 'R$ 1,00'); 'recibo_integro' → ('recibo_integro', None)."""
    m = _CHECAGEM.match(texto.strip())
    if not m or m["nome"] not in CHECAGENS:
        raise ValueError(f"checagem desconhecida: {texto!r}")
    arg = m["arg"]
    if arg is not None and arg.startswith('"'):
        arg = arg[1:-1]
    return m["nome"], arg


class Caso(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^A\d{3}$")
    categoria: Categoria
    usuario: str | None = None  # e-mail do seed; None só com token ausente/forjado
    descricao: str = ""
    pergunta: str | None = None
    preencher_ate: int | None = Field(default=None, ge=1, le=5000)  # completa a pergunta até N caracteres
    corpo_extra: dict[str, Any] = Field(default_factory=dict)  # campos a mais no corpo de POST /consultas
    requisicao: str | None = None  # "GET /recibos/{recibo_de_ana}"
    corpo: dict[str, Any] | None = None  # corpo de uma requisição POST
    token: Token = "valido"
    rajada: int | None = Field(default=None, ge=2, le=100)  # repete a pergunta N vezes com o limite real
    esperado: Esperado
    verificar: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def coerente(self) -> "Caso":
        if (self.pergunta is None) == (self.requisicao is None):
            raise ValueError(f"{self.id}: informe pergunta ou requisicao, não as duas")
        if self.requisicao is not None and not _REQUISICAO.match(self.requisicao):
            raise ValueError(f"{self.id}: requisicao deve ser 'GET /caminho' ou 'POST /caminho'")
        if self.token == "valido" and not self.usuario:
            raise ValueError(f"{self.id}: token válido exige usuario")
        if self.rajada is not None and self.pergunta is None:
            raise ValueError(f"{self.id}: rajada só com pergunta")
        if self.rajada is not None and self.esperado != "limite":
            raise ValueError(f"{self.id}: rajada espera 'limite'")
        for checagem in self.verificar:
            ler_checagem(checagem)
        return self

    @property
    def checagens(self) -> list[tuple[str, str | None]]:
        return [ler_checagem(c) for c in self.verificar]

    def pergunta_final(self) -> str | None:
        if self.pergunta is None or self.preencher_ate is None:
            return self.pergunta
        falta = self.preencher_ate - len(self.pergunta)
        return self.pergunta + (" " + "x" * (falta - 1) if falta > 1 else "x" * max(falta, 0))


def carregar(caminho: Path) -> list[Caso]:
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or []
    casos = [Caso(**item) for item in dados]
    ids = [c.id for c in casos]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        raise ValueError(f"ids repetidos em {caminho.name}: {repetidos}")
    return casos
