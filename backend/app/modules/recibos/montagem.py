"""Conteúdo do recibo (contracts/recibo.schema.json, v1). Função pura: tudo vem do backend.

O único texto que passou por LLM é `resposta_final`, e ele já saiu do verificador (SPEC §8.3).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from app.core.contexto import ContextoAcesso
from app.modules.recibos.canonico import para_json

StatusVerificacao = Literal["aprovado", "fallback", "abstencao", "negado"]

# Colunas de cada linha citada que vão para o recibo (schema: linhas[].*).
CAMPOS_LINHA = ("tabela", "id", "fonte_id", "id_origem", "url_origem", "coletado_em", "hash_conteudo")


@dataclass(frozen=True)
class Execucao:
    consulta_catalogo: str  # "<intent>@<versão>" ou a intent sem consulta (ex.: "fora_de_escopo")
    parametros_efetivos: dict[str, Any] = field(default_factory=dict)
    ufs_efetivas: tuple[str, ...] = ()
    n_linhas: int = 0
    duracao_ms: int = 0


@dataclass(frozen=True)
class Fonte:
    fonte_id: str
    nome: str
    coletado_em: datetime
    execucao_id: UUID | None
    sintetico: bool


@dataclass(frozen=True)
class IA:
    provedor: str
    modelo: str | None
    versao_prompt_planejador: str
    versao_prompt_redator: str | None
    planejador_por_regras: bool


@dataclass(frozen=True)
class DadosRecibo:
    consulta_id: UUID
    ctx: ContextoAcesso
    pergunta: str
    plano: dict[str, Any]
    execucao: Execucao
    linhas: tuple[dict[str, Any], ...]
    fontes: tuple[Fonte, ...]
    valores: dict[str, dict[str, str]]
    resposta_final: str
    verificacao_status: StatusVerificacao
    verificacao_motivos: tuple[str, ...]
    ia: IA
    criado_em: datetime
    carteira: dict[str, str] | None = None


def montar_conteudo(d: DadosRecibo) -> dict[str, Any]:
    ia: dict[str, Any] = {
        "provedor": d.ia.provedor,
        "versao_prompt_planejador": d.ia.versao_prompt_planejador,
        "planejador_por_regras": d.ia.planejador_por_regras,
    }
    if d.ia.modelo:
        ia["modelo"] = d.ia.modelo
    if d.ia.versao_prompt_redator:
        ia["versao_prompt_redator"] = d.ia.versao_prompt_redator

    conteudo: dict[str, Any] = {
        "versao": "v1",
        "consulta_id": d.consulta_id,
        "tenant_id": d.ctx.tenant_id,
        "usuario_id": d.ctx.usuario_id,
        "perfil": d.ctx.perfil,
        "ufs_autorizadas": sorted(d.ctx.ufs),
        "carteira": d.carteira,
        "pergunta": d.pergunta,
        "plano": d.plano,
        "execucao": {
            "consulta_catalogo": d.execucao.consulta_catalogo,
            "parametros_efetivos": d.execucao.parametros_efetivos,
            "ufs_efetivas": list(d.execucao.ufs_efetivas),
            "n_linhas": d.execucao.n_linhas,
            "duracao_ms": d.execucao.duracao_ms,
        },
        "linhas": [{c: linha.get(c) for c in CAMPOS_LINHA} for linha in d.linhas],
        "valores": d.valores,
        "fontes": [
            {
                "fonte_id": f.fonte_id,
                "nome": f.nome,
                "coletado_em": f.coletado_em,
                "execucao_id": f.execucao_id,
                "sintetico": f.sintetico,
            }
            for f in d.fontes
        ],
        "resposta_final": d.resposta_final,
        "verificacao": {"status": d.verificacao_status, "motivos": list(d.verificacao_motivos)},
        "ia": ia,
        "criado_em": d.criado_em,
    }
    return para_json(conteudo)
