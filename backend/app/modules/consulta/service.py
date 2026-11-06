"""Orquestração de POST /consultas (SPEC §4.3).

    pergunta → guardas por código → planejador → executor do catálogo (RLS) → redator + verificador
             → consulta + recibo + auditoria, numa transação só → resposta com citações e recibo_id

Cada caminho termina num `Desfecho`. `_gravar` persiste qualquer desfecho do mesmo jeito: ou entram
consulta, recibo e evento de auditoria juntos, ou nada. Negação grava e só então responde 403.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.core.errors import ErroApi
from app.llm import planejador, redator
from app.llm.plano import PlanoConsulta
from app.llm.providers import ProvedorLLM
from app.llm.redator import RespostaRedigida
from app.modules.auditoria import service as auditoria
from app.modules.catalogo.executor import IntentSemConsulta, ResultadoConsulta, executar
from app.modules.consulta import citacoes as cit
from app.modules.consulta import fontes, guardas, queries
from app.modules.consulta.schemas import ConsultaEntrada, ConsultaListada, ConsultaSaida, StatusConsulta
from app.modules.recibos import service as recibos
from app.modules.recibos.canonico import para_json
from app.modules.recibos.montagem import IA, DadosRecibo, Execucao, StatusVerificacao

log = logging.getLogger("lastro.consulta")

FUSO_RECIFE = timezone(timedelta(hours=-3))  # Pernambuco não tem horário de verão

MENSAGEM_FORA_DO_CATALOGO = (
    "Não consigo responder isso com as fontes do Lastro. Pergunte sobre contratos, pagamentos ou sanções de "
    "um fornecedor, informando o CNPJ."
)
MENSAGEM_INTENT_INDISPONIVEL = (
    "Esse tipo de consulta ainda não está disponível. Por enquanto: resumo, contratos vigentes ou vencendo, "
    "pagamentos num período e sanções de um fornecedor."
)
MENSAGEM_CNPJ_INVALIDO = "O CNPJ informado não é válido (dígito verificador). Pode conferir?"
MENSAGEM_TEMPO_ESGOTADO = "A consulta demorou além do limite. Tente de novo em instantes."

# Motivos do verificador que indicam texto de fonte tentando mandar no redator (injeção armazenada).
MOTIVOS_DE_ATAQUE = frozenset({"vazamento", "uf_fora_do_escopo", "url_fora_do_resultado"})


def hoje_recife() -> date:
    return datetime.now(FUSO_RECIFE).date()


@dataclass(frozen=True)
class Ambiente:
    """O que vem de fora da regra: provedor de LLM e relógio. Os testes trocam por versões fixas."""

    provedor: ProvedorLLM | None
    hoje: Callable[[], date] = hoje_recife
    agora: Callable[[], datetime] = lambda: datetime.now(UTC)


@dataclass
class Desfecho:
    status: StatusConsulta
    resposta: str
    evento: str  # auditoria.evento: consulta | abstencao | negado
    detalhes: dict[str, Any] = field(default_factory=dict)
    planejamento: planejador.ResultadoPlanejamento | None = None
    resultado: ResultadoConsulta | None = None
    redacao: RespostaRedigida | None = None
    linhas: list[dict[str, Any]] = field(default_factory=list)
    duracao_execucao_ms: int = 0
    # Recibo: toda resposta com conteúdo (respondida e abstenção). Esclarecimento e negação não têm.
    verificacao: StatusVerificacao | None = None
    motivos: tuple[str, ...] = ()
    erro: ErroApi | None = None  # negação: respondida como erro depois de gravar


# ------------------------------------------------------------------ caminhos
def _negado(guarda: guardas.Negacao, planejamento=None) -> Desfecho:
    return Desfecho(
        status="negada",
        resposta=guarda.mensagem,
        evento="negado",
        detalhes={"motivo": guarda.motivo, **guarda.detalhes},
        planejamento=planejamento,
        erro=ErroApi(403, "ESCOPO_NEGADO", guarda.mensagem),
    )


def _esclarecimento(mensagem: str, planejamento) -> Desfecho:
    return Desfecho("esclarecimento", mensagem, "consulta", {"status": "esclarecimento"}, planejamento)


def _abstencao(mensagem: str, motivo: str, planejamento) -> Desfecho:
    return Desfecho(
        "abstencao",
        mensagem,
        "abstencao",
        {"motivo": motivo},
        planejamento,
        verificacao="abstencao",
        motivos=(motivo,),
    )


def _executar_e_redigir(
    pergunta: str, plano: PlanoConsulta, ctx: ContextoAcesso, amb: Ambiente, planejamento
) -> Desfecho:
    inicio = time.perf_counter()
    try:
        resultado = executar(plano, ctx, amb.hoje())
    except IntentSemConsulta:
        return _abstencao(MENSAGEM_INTENT_INDISPONIVEL, "intent_sem_consulta", planejamento)
    except ErroApi as erro:
        if erro.codigo == "ESCOPO_NEGADO":
            uf = [plano.parametros.uf] if plano.parametros.uf else []
            negacao = guardas.Negacao("uf_fora_do_escopo", erro.mensagem, {"ufs_pedidas": uf})
            return _negado(negacao, planejamento)
        if erro.codigo == "ENTRADA_INVALIDA":
            return _esclarecimento(MENSAGEM_CNPJ_INVALIDO, planejamento)
        raise
    duracao_ms = round((time.perf_counter() - inicio) * 1000)

    coleta = None
    if not any(resultado.conjuntos.values()):
        with sessao(ctx) as conn:
            coleta = fontes.ultima_coleta(conn, resultado.intent)
    redacao = redator.redigir(
        pergunta, resultado, ufs_autorizadas=ctx.ufs, provedor=amb.provedor, fontes_coletadas_em=coleta
    )
    linhas = cit.linhas_citaveis(resultado)
    respondida = redacao.status != "abstencao"
    return Desfecho(
        status="respondida" if respondida else "abstencao",
        resposta=redacao.texto,
        evento="consulta" if respondida else "abstencao",
        detalhes={"status_redacao": redacao.status, "motivos": list(redacao.motivos)},
        planejamento=planejamento,
        resultado=resultado,
        redacao=redacao,
        linhas=linhas,
        duracao_execucao_ms=duracao_ms,
        verificacao=redacao.status,
        motivos=redacao.motivos,
    )


def _decidir(entrada: ConsultaEntrada, ctx: ContextoAcesso, amb: Ambiente) -> Desfecho:
    if negacao := guardas.checar_pergunta(entrada.pergunta, ctx):
        return _negado(negacao)

    planejamento = planejador.planejar(entrada.pergunta, ufs=ctx.ufs, hoje=amb.hoje(), provedor=amb.provedor)
    plano = planejamento.plano
    if plano.intent == "esclarecer":
        return _esclarecimento(
            plano.parametros.pergunta_de_volta or planejador.PERGUNTA_REFORMULAR, planejamento
        )
    if plano.intent == "fora_de_escopo":
        return _abstencao(MENSAGEM_FORA_DO_CATALOGO, "fora_de_escopo", planejamento)
    return _executar_e_redigir(entrada.pergunta, plano, ctx, amb, planejamento)


# ------------------------------------------------------------------ gravação
def _carteira(ctx: ContextoAcesso, carteira_id: UUID | None) -> dict[str, str] | None:
    """Carteira de outro tenant responde 404, igual a inexistente (a RLS não a mostra)."""
    if carteira_id is None:
        return None
    with sessao(ctx) as conn:
        linha = (
            conn.cursor(row_factory=dict_row).execute(queries.BUSCAR_CARTEIRA, {"id": carteira_id}).fetchone()
        )
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Carteira não encontrada.")
    return {"id": str(linha["id"]), "finalidade": linha["finalidade"]}


def _ia(d: Desfecho, amb: Ambiente) -> IA:
    p = d.planejamento
    provedor = (d.redacao.provedor if d.redacao else None) or (amb.provedor.nome if amb.provedor else "mock")
    modelo = (d.redacao.modelo if d.redacao else None) or (p.modelo if p else None)
    return IA(
        provedor=provedor,
        modelo=modelo,
        versao_prompt_planejador=planejador.VERSAO_PROMPT,
        versao_prompt_redator=d.redacao.versao_prompt if d.redacao else None,
        planejador_por_regras=p.por_regras if p else True,
    )


def _execucao(d: Desfecho) -> Execucao:
    r = d.resultado
    if r is None:
        intent = d.planejamento.plano.intent if d.planejamento else "nenhuma"
        return Execucao(consulta_catalogo=intent)
    return Execucao(
        consulta_catalogo=r.versao,
        parametros_efetivos=para_json(r.parametros),
        ufs_efetivas=tuple(r.parametros.get("ufs", ())),
        n_linhas=len(d.linhas),
        duracao_ms=d.duracao_execucao_ms,
    )


def _versao_prompt(d: Desfecho) -> str:
    redacao = d.redacao.versao_prompt if d.redacao else None
    return "+".join(v for v in (planejador.VERSAO_PROMPT, redacao) if v)


def _gravar(
    entrada: ConsultaEntrada,
    ctx: ContextoAcesso,
    amb: Ambiente,
    d: Desfecho,
    latencia_ms: int,
    carteira: dict[str, str] | None,
) -> tuple[UUID, UUID | None]:
    plano = d.planejamento.plano.model_dump(mode="json", exclude_none=True) if d.planejamento else None
    ia = _ia(d, amb)
    with sessao(ctx) as conn:
        consulta_id = conn.execute(
            queries.INSERIR_CONSULTA,
            {
                "carteira_id": entrada.carteira_id,
                "pergunta": entrada.pergunta,
                "plano": Jsonb(plano) if plano is not None else None,
                "intent": d.planejamento.plano.intent if d.planejamento else None,
                "status": d.status,
                "resposta": d.resposta,
                "modelo": ia.modelo,
                "versao_prompt": _versao_prompt(d),
                "latencia_ms": latencia_ms,
            },
        ).fetchone()[0]

        recibo_id = None
        if d.verificacao is not None:
            recibo_id = recibos.gravar(
                conn,
                DadosRecibo(
                    consulta_id=consulta_id,
                    ctx=ctx,
                    pergunta=entrada.pergunta,
                    plano=plano or {},
                    execucao=_execucao(d),
                    linhas=tuple(d.linhas),
                    fontes=fontes.fontes_das_linhas(conn, d.linhas),
                    valores=d.redacao.valores if d.redacao else {},
                    resposta_final=d.resposta,
                    verificacao_status=d.verificacao,
                    verificacao_motivos=d.motivos,
                    ia=ia,
                    criado_em=amb.agora(),
                    carteira=carteira,
                ),
            )

        intent = d.planejamento.plano.intent if d.planejamento else None
        base = {"consulta_id": str(consulta_id), "intent": intent, "recibo_id": recibo_id and str(recibo_id)}
        auditoria.registrar_em(conn, d.evento, {**base, **d.detalhes})
        if MOTIVOS_DE_ATAQUE.intersection(d.motivos):
            ataque = {**base, "motivos": sorted(MOTIVOS_DE_ATAQUE.intersection(d.motivos))}
            auditoria.registrar_em(conn, "ataque_detectado", ataque)
    return consulta_id, recibo_id


def _registrar_erro(entrada: ConsultaEntrada, ctx: ContextoAcesso, erro: Exception) -> None:
    """Melhor esforço: a falha fica na trilha. Se nem isso der, só o log (sem a pergunta: pode ter dado)."""
    try:
        with sessao(ctx) as conn:
            parametros = {
                "carteira_id": None,
                "pergunta": entrada.pergunta,
                "plano": None,
                "intent": None,
                "status": "erro",
                "resposta": None,
                "modelo": None,
                "versao_prompt": None,
                "latencia_ms": None,
            }
            consulta_id = conn.execute(queries.INSERIR_CONSULTA, parametros).fetchone()[0]
            detalhes = {"consulta_id": str(consulta_id), "tipo": type(erro).__name__}
            auditoria.registrar_em(conn, "erro", detalhes)
    except Exception:  # registrar o erro não pode esconder o erro original
        log.exception("não foi possível registrar o erro da consulta")


# ------------------------------------------------------------------ entrada
def responder(entrada: ConsultaEntrada, ctx: ContextoAcesso, amb: Ambiente) -> ConsultaSaida:
    inicio = time.perf_counter()
    carteira = _carteira(ctx, entrada.carteira_id)  # antes de qualquer LLM: carteira alheia para aqui
    try:
        desfecho = _decidir(entrada, ctx, amb)
        latencia_ms = round((time.perf_counter() - inicio) * 1000)
        consulta_id, recibo_id = _gravar(entrada, ctx, amb, desfecho, latencia_ms, carteira)
    except ErroApi:
        raise
    except psycopg.errors.QueryCanceled as erro:
        _registrar_erro(entrada, ctx, erro)
        raise ErroApi(503, "FONTE_INDISPONIVEL", MENSAGEM_TEMPO_ESGOTADO) from erro
    except Exception as erro:
        _registrar_erro(entrada, ctx, erro)
        raise

    if desfecho.erro is not None:
        raise desfecho.erro
    return ConsultaSaida(
        consulta_id=consulta_id,
        status=desfecho.status,
        resposta=desfecho.resposta,
        citacoes=cit.citacoes(desfecho.linhas),
        recibo_id=recibo_id,
        sintetico=cit.tem_dado_sintetico(desfecho.linhas),
    )


def listar(ctx: ContextoAcesso, limite: int) -> list[ConsultaListada]:
    with sessao(ctx) as conn:
        linhas = (
            conn.cursor(row_factory=dict_row).execute(queries.LISTAR_CONSULTAS, {"limite": limite}).fetchall()
        )
    return [ConsultaListada(**linha) for linha in linhas]
