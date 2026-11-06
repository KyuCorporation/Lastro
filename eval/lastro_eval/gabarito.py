"""Gabarito (SPEC §14.1): perguntas com intent e comportamento esperados e, quando houver, um SQL de referência
escrito à parte do catálogo. Mede acerto de intent, de comportamento e de resultado, citação correta e fallback.

Como na suíte de ataques, a API roda em processo exatamente como em produção, e a verdade (intent gravada,
recibo, linhas citadas, resultado do SQL de referência) é lida à parte.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import psycopg
import yaml
from pydantic import BaseModel, ConfigDict, Field

Comportamento = Literal["responder", "abster", "esclarecer", "negar"]
META_INTENT = 90.0  # SPEC §14.6: ≥ 90% de acerto de intent


class CasoGabarito(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^G\d{3}$")
    usuario: str
    pergunta: str = Field(min_length=1, max_length=500)
    intent_esperada: str
    comportamento: Comportamento
    sql_referencia: str | None = None


def carregar(caminho: Path) -> list[CasoGabarito]:
    casos = [CasoGabarito(**item) for item in yaml.safe_load(caminho.read_text(encoding="utf-8")) or []]
    ids = [c.id for c in casos]
    if repetidos := sorted({i for i in ids if ids.count(i) > 1}):
        raise ValueError(f"ids repetidos no gabarito: {repetidos}")
    return casos


# ===================== Julgamento (puro) =====================


@dataclass(frozen=True)
class Observado:
    """O que o sistema fez com a pergunta, já lido da resposta e do banco."""

    status_http: int
    codigo_erro: str | None
    status: str | None  # respondida | abstencao | esclarecimento | negada | erro
    intent: str | None  # gravada em consultas.intent (nula quando a guarda negou antes do planejador)
    motivo_negacao: str | None  # auditoria.detalhes.motivo da negação
    motivos_verificacao: tuple[str, ...] = ()  # recibo.verificacao.motivos
    verificacao: str | None = None  # recibo.verificacao.status


def comportamento_observado(o: Observado) -> str:
    """Traduz o desfecho para o vocabulário do gabarito.

    Equivalências (documentadas em eval/README.md):
    - resultado vazio é a resposta certa de "responder" quando não há registro (SPEC §8.4: abstenção explícita);
    - pedido para burlar regras negado pela guarda (antes do planejador) conta como "abster", o mesmo efeito.
    """
    if o.status_http == 403 and o.codigo_erro == "ESCOPO_NEGADO":
        return "abster" if o.motivo_negacao == "pedido_fora_do_permitido" else "negar"
    if o.status_http == 403:
        return "negar"
    if o.status == "respondida":
        return "responder"
    if o.status == "abstencao":
        if "resultado_vazio" in o.motivos_verificacao:
            return "responder"
        if "intent_sem_consulta" in o.motivos_verificacao:
            return "intent_indisponivel"
        return "abster"
    if o.status == "esclarecimento":
        return "esclarecer"
    return f"erro_{o.status_http}"


@dataclass
class ResultadoGabarito:
    id: str
    comportamento_esperado: str
    comportamento_obtido: str
    intent_esperada: str
    intent_obtida: str | None
    acerto_intent: bool | None  # None = não avaliável (guarda negou antes do planejador)
    acerto_comportamento: bool
    acerto_resultado: bool | None = None  # None = caso sem sql_referencia ou sem execução
    citacao_correta: bool | None = None  # None = sem citações
    fallback: bool = False
    observacoes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        checagens = [
            self.acerto_comportamento,
            self.acerto_intent,
            self.acerto_resultado,
            self.citacao_correta,
        ]
        return all(c is not False for c in checagens)

    def como_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ok": self.ok,
            "comportamento": f"{self.comportamento_obtido} (esperado {self.comportamento_esperado})",
            "intent": f"{self.intent_obtida} (esperada {self.intent_esperada})",
            "acerto_intent": self.acerto_intent,
            "acerto_comportamento": self.acerto_comportamento,
            "acerto_resultado": self.acerto_resultado,
            "citacao_correta": self.citacao_correta,
            "fallback": self.fallback,
            "motivo": "; ".join(self.observacoes) if self.observacoes else "ok",
        }


def julgar(caso: CasoGabarito, o: Observado) -> ResultadoGabarito:
    obtido = comportamento_observado(o)
    if o.intent is None:
        acerto_intent = None
    else:
        acerto_intent = o.intent == caso.intent_esperada
    r = ResultadoGabarito(
        id=caso.id,
        comportamento_esperado=caso.comportamento,
        comportamento_obtido=obtido,
        intent_esperada=caso.intent_esperada,
        intent_obtida=o.intent,
        acerto_intent=acerto_intent,
        acerto_comportamento=obtido == caso.comportamento
        # recusa da guarda (pedido para burlar regras) satisfaz tanto "abster" quanto "negar"
        or (o.motivo_negacao == "pedido_fora_do_permitido" and caso.comportamento in ("abster", "negar")),
        fallback=o.verificacao == "fallback",
    )
    if not r.acerto_comportamento:
        r.observacoes.append(f"comportamento {obtido}, esperado {caso.comportamento}")
    if acerto_intent is False:
        r.observacoes.append(f"intent {o.intent}, esperada {caso.intent_esperada}")
    return r


def pct(parte: int, total: int) -> float | None:
    return round(100 * parte / total, 1) if total else None


def metricas(resultados: list[ResultadoGabarito]) -> dict[str, Any]:
    def taxa(atributo: str) -> tuple[float | None, int]:
        avaliados = [getattr(r, atributo) for r in resultados if getattr(r, atributo) is not None]
        return pct(sum(avaliados), len(avaliados)), len(avaliados)

    intent, n_intent = taxa("acerto_intent")
    comportamento, _ = taxa("acerto_comportamento")
    resultado, n_resultado = taxa("acerto_resultado")
    citacao, n_citacao = taxa("citacao_correta")
    respondidas = [r for r in resultados if r.comportamento_obtido == "responder"]
    return {
        "n_casos": len(resultados),
        "ok": sum(r.ok for r in resultados),
        "acerto_intent": intent,
        "n_intent_avaliada": n_intent,
        "acerto_comportamento": comportamento,
        "acerto_resultado": resultado,
        "n_com_sql_referencia": n_resultado,
        "citacao_correta": citacao,
        "n_com_citacao": n_citacao,
        "taxa_fallback": pct(sum(r.fallback for r in respondidas), len(respondidas)),
        "meta_intent": META_INTENT,
    }


# ===================== Execução =====================


class ExecutorGabarito:
    def __init__(self, cliente: Any, conn_verdade: psycopg.Connection) -> None:
        self.cliente = cliente
        self.conn = conn_verdade
        self.tokens: dict[str, dict[str, Any]] = {}

    def _sessao(self, email: str) -> dict[str, Any]:
        if email not in self.tokens:
            r = self.cliente.post("/auth/login", json={"email": email, "senha": "demo123"})
            if r.status_code != 200:
                raise SystemExit(f"login de {email} falhou ({r.status_code}): rode `make seed`.")
            self.tokens[email] = r.json()
        return self.tokens[email]

    def _um(self, sql: str, params: tuple = ()) -> Any:
        linha = self.conn.execute(sql, params).fetchone()
        return None if linha is None else linha

    def _ids_de_referencia(self, sql: str, usuario: dict[str, Any]) -> set[str]:
        """Roda o SQL de referência como lastro_app com o contexto do usuário, numa transação desfeita."""
        with self.conn.transaction(force_rollback=True):
            self.conn.execute("set local role lastro_app")
            self.conn.execute("set local statement_timeout = 5000")
            self.conn.execute(
                "select set_config('app.tenant_id', %s, true), set_config('app.usuario_id', %s, true), "
                "set_config('app.perfil', %s, true), set_config('app.ufs', %s, true)",
                (usuario["tenant"]["id"], usuario["id"], usuario["perfil"], ",".join(usuario["ufs"])),
            )
            return {str(linha[0]) for linha in self.conn.execute(sql).fetchall()}

    PROVENIENCIA: dict[str, str] = {  # noqa: RUF012
        "contratos": "select fonte_id, url_origem from contratos where id = %s",
        "pagamentos": "select fonte_id, url_origem from pagamentos where id = %s",
        "sancoes": "select fonte_id, url_origem from sancoes where id = %s",
    }

    def _citacoes_corretas(self, citacoes: list[dict[str, Any]], linhas_recibo: set[str]) -> bool:
        for c in citacoes:
            if c["id"] not in linhas_recibo:
                return False
            if c["tabela"] == "sinais":
                continue
            sql = self.PROVENIENCIA.get(c["tabela"])
            if sql is None:
                return False
            linha = self._um(sql, (c["id"],))
            if linha is None or (linha[0], linha[1]) != (c["fonte_id"], c["url_origem"]):
                return False
        return True

    def executar(self, caso: CasoGabarito) -> ResultadoGabarito:
        sessao = self._sessao(caso.usuario)
        usuario = sessao["usuario"]
        seq_antes = self._um("select coalesce(max(seq), 0) from auditoria")[0]
        r = self.cliente.post(
            "/consultas",
            json={"pergunta": caso.pergunta},
            headers={"Authorization": f"Bearer {sessao['token']}"},
        )
        corpo = r.json()
        erro = corpo.get("erro") if isinstance(corpo, dict) else None
        consulta_id = corpo.get("consulta_id") if not erro else None
        intent = status = None
        if consulta_id:
            intent, status = self._um("select intent, status from consultas where id = %s", (consulta_id,))
        else:
            linha = self._um(
                "select c.intent, c.status from consultas c where c.usuario_id = %s and c.pergunta = %s "
                "order by c.criada_em desc limit 1",
                (usuario["id"], caso.pergunta),
            )
            if linha:
                intent, status = linha
        motivo_negacao = None
        if r.status_code == 403:
            linha = self._um(
                "select detalhes->>'motivo' from auditoria where usuario_id = %s and seq > %s and evento = 'negado' "
                "order by seq desc limit 1",
                (usuario["id"], seq_antes),
            )
            motivo_negacao = linha[0] if linha else None
        recibo = None
        if not erro and corpo.get("recibo_id"):
            recibo = self._um("select conteudo from recibos where id = %s", (corpo["recibo_id"],))[0]
        verificacao = (recibo or {}).get("verificacao", {})
        observado = Observado(
            status_http=r.status_code,
            codigo_erro=erro.get("codigo") if erro else None,
            status=status,
            intent=intent,
            motivo_negacao=motivo_negacao,
            motivos_verificacao=tuple(verificacao.get("motivos", [])),
            verificacao=verificacao.get("status"),
        )
        resultado = julgar(caso, observado)

        linhas_recibo = {linha["id"] for linha in (recibo or {}).get("linhas", [])}
        if caso.sql_referencia and caso.comportamento == "responder" and r.status_code == 200:
            referencia = self._ids_de_referencia(caso.sql_referencia, usuario)
            resultado.acerto_resultado = referencia == linhas_recibo
            if not resultado.acerto_resultado:
                resultado.observacoes.append(
                    f"resultado difere do SQL de referência (só na referência: {len(referencia - linhas_recibo)}, "
                    f"só no recibo: {len(linhas_recibo - referencia)})"
                )
        citacoes = corpo.get("citacoes") if not erro else None
        if citacoes:
            resultado.citacao_correta = self._citacoes_corretas(citacoes, linhas_recibo)
            if not resultado.citacao_correta:
                resultado.observacoes.append("citação não confere com o recibo ou com a linha no banco")
        return resultado
