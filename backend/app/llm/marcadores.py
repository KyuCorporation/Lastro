"""Marcadores e modelos determinísticos por intent.

Todo número, valor, data e CNPJ da resposta sai daqui, do resultado do catálogo. O redator só vê os marcadores
(`{{v1}}`) e o significado de cada um. O modelo determinístico é o texto pronto da intent, usado no modo mock,
quando o verificador reprova o redator e quando o resultado vem vazio (abstenção).

Intent nova do catálogo = uma função `@modelo_da_intent("<intent>")` que devolve o `Material`.
`intents_sem_modelo()` acusa, na importação, consulta do catálogo sem modelo.
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Any

from app.llm.formatacao import TipoValor, formatar, formatar_cnpj
from app.llm.texto_externo import dado_nao_confiavel
from app.modules.catalogo.executor import ResultadoConsulta
from app.modules.catalogo.registry import CONSULTAS

LIMITE_REGISTROS_TEXTO = 5

# Compatibilidade: nome usado antes da quarentena ir para texto_externo.py.
nao_confiavel = dado_nao_confiavel


@dataclass(frozen=True)
class Marcador:
    id: str
    valor: Any
    tipo: TipoValor
    significado: str
    origem: str

    @property
    def texto(self) -> str:
        return formatar(self.valor, self.tipo)


@dataclass(frozen=True)
class Material:
    """O que a intent entrega para a redação."""

    marcadores: dict[str, Marcador]
    modelo: str
    vazio: bool
    # Texto vindo das fontes (nome de órgão, objeto, tipo de sanção), já em quarentena e sem números.
    registros: tuple[str, ...] = field(default_factory=tuple)
    # Marcadores que carregam a resposta (contagens, valores, datas do resultado). Identificação (CNPJ, UFs)
    # e parâmetros da pergunta (prazo, período) não contam: um texto só com eles não respondeu nada.
    essenciais: frozenset[str] = field(default_factory=frozenset)


class _Montador:
    def __init__(self, inicial: dict[str, Marcador] | None = None) -> None:
        self.marcadores: dict[str, Marcador] = dict(inicial or {})
        self.essenciais: set[str] = set()

    def add(
        self, valor: Any, tipo: TipoValor, significado: str, origem: str, *, essencial: bool = True
    ) -> str:
        mid = f"v{len(self.marcadores) + 1}"
        self.marcadores[mid] = Marcador(mid, valor, tipo, significado, origem)
        if essencial:
            self.essenciais.add(mid)
        return "{{" + mid + "}}"

    def material(self, modelo: str, vazio: bool, registros: tuple[str, ...] = ()) -> Material:
        return Material(self.marcadores, modelo, vazio, registros, frozenset(self.essenciais))


# ------------------------------------------------------------------ registro das intents
ModeloDaIntent = Callable[[ResultadoConsulta], Material]
_POR_INTENT: dict[str, ModeloDaIntent] = {}


def modelo_da_intent(intent: str) -> Callable[[ModeloDaIntent], ModeloDaIntent]:
    def registrar(funcao: ModeloDaIntent) -> ModeloDaIntent:
        if intent in _POR_INTENT:
            raise RuntimeError(f"modelo duplicado para a intent {intent}")
        _POR_INTENT[intent] = funcao
        return funcao

    return registrar


def intents_sem_modelo() -> set[str]:
    return set(CONSULTAS) - set(_POR_INTENT)


# ------------------------------------------------------------------ partes comuns
def _ufs(resultado: ResultadoConsulta) -> str:
    return ", ".join(resultado.parametros.get("ufs", []))


def _cnpj(m: _Montador, resultado: ResultadoConsulta) -> str:
    cnpj = resultado.parametros["cnpj"]
    return m.add(formatar_cnpj(cnpj), "texto", "CNPJ do fornecedor", "parametros.cnpj", essencial=False)


def _ufs_marcador(m: _Montador, resultado: ResultadoConsulta) -> str:
    return m.add(_ufs(resultado), "texto", "UFs consultadas", "parametros.ufs", essencial=False)


def _frase_empenho(m: _Montador, t: dict[str, Any]) -> str:
    """Empenho é reserva no orçamento, não pagamento: aparece à parte e só quando existe.

    Os marcadores entram depois dos demais, então a numeração de quem não tem empenho não muda.
    """
    if not t["n_empenhos"]:
        return ""
    v_e = m.add(
        t["valor_empenhado"], "moeda", "valor empenhado (reservado, ainda não pago)", "sum(empenhos.valor)"
    )
    n_e = m.add(t["n_empenhos"], "inteiro", "número de empenhos", "count(empenhos)")
    return f" Há ainda {v_e} empenhado(s) em {n_e} empenho(s): reserva no orçamento, que só conta como pago depois de liquidada."


def _registros_contratos(linhas: list[dict]) -> tuple[str, ...]:
    return tuple(
        f"- Contrato com o órgão {dado_nao_confiavel(c.get('orgao_nome'))} (UF {c['uf']}), "
        f"objeto: {dado_nao_confiavel(c.get('objeto'))}"
        for c in linhas[:LIMITE_REGISTROS_TEXTO]
    )


# ------------------------------------------------------------------ intents
@modelo_da_intent("resumo_fornecedor")
def _resumo(r: ResultadoConsulta) -> Material:
    m, t = _Montador(), r.totais
    cnpj = _cnpj(m, r)
    n_c = m.add(t["n_contratos"], "inteiro", "número de contratos", "count(contratos)")
    v_c = m.add(t["valor_contratado"], "moeda", "valor contratado somado", "sum(contratos.valor_global)")
    v_v = m.add(
        t["valor_vigente"], "moeda", "valor dos contratos ainda vigentes", "sum(valor_global) vigentes"
    )
    n_p = m.add(
        t["n_pagamentos"], "inteiro", "número de pagamentos (sem contar empenhos)", "count(pagamentos)"
    )
    v_p = m.add(t["valor_pago"], "moeda", "valor pago somado (sem contar empenhos)", "sum(pagamentos.valor)")
    ufs = _ufs_marcador(m, r)
    vazio = t["n_contratos"] == 0 and t["n_pagamentos"] == 0 and t["n_empenhos"] == 0
    if vazio:
        modelo = (
            f"Não encontrei contratos nem pagamentos do fornecedor {cnpj} "
            f"nas fontes autorizadas para você ({ufs})."
        )
    else:
        modelo = (
            f"Nas fontes autorizadas para você ({ufs}), o fornecedor {cnpj} tem {n_c} contrato(s), "
            f"somando {v_c}, dos quais {v_v} em contratos ainda vigentes. "
            f"Foram registrados {n_p} pagamento(s), num total de {v_p}."
        ) + _frase_empenho(m, t)
    registros = tuple(
        f"- Órgão {dado_nao_confiavel(g.get('orgao_nome'))} (UF {g['uf']})"
        for g in r.conjuntos["por_uf_orgao"][:LIMITE_REGISTROS_TEXTO]
    )
    return m.material(modelo, vazio, registros)


@modelo_da_intent("contratos_vigentes")
def _vigentes(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    cnpj = _cnpj(m, r)
    n = m.add(t["n_contratos"], "inteiro", "número de contratos vigentes", "count(contratos vigentes)")
    valor = m.add(t["valor_total"], "moeda", "valor somado dos contratos vigentes", "sum(valor_global)")
    proximo = m.add(
        min((c["vigencia_fim"] for c in linhas), default=None),
        "data",
        "data do próximo fim de vigência",
        "min(vigencia_fim)",
    )
    ufs = _ufs_marcador(m, r)
    if not linhas:
        modelo = (
            f"Não encontrei contratos vigentes do fornecedor {cnpj} nas fontes autorizadas para você ({ufs})."
        )
    else:
        modelo = (
            f"O fornecedor {cnpj} tem {n} contrato(s) vigente(s) nas fontes autorizadas para você ({ufs}), "
            f"somando {valor}. O próximo a terminar vence em {proximo}."
        )
    return m.material(modelo, not linhas, _registros_contratos(linhas))


@modelo_da_intent("contratos_vencendo")
def _vencendo(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    cnpj = _cnpj(m, r)
    dias = m.add(r.parametros["dias"], "inteiro", "prazo em dias", "parametros.dias", essencial=False)
    n = m.add(t["n_contratos"], "inteiro", "número de contratos que vencem no prazo", "count(contratos)")
    valor = m.add(t["valor_vencendo"], "moeda", "valor somado dos contratos que vencem", "sum(valor_global)")
    primeiro = m.add(
        min((c["vigencia_fim"] for c in linhas), default=None),
        "data",
        "data do primeiro vencimento",
        "min(vigencia_fim)",
    )
    ufs = _ufs_marcador(m, r)
    if not linhas:
        modelo = (
            f"Não encontrei contratos do fornecedor {cnpj} que vençam nos próximos {dias} dias "
            f"nas fontes autorizadas para você ({ufs})."
        )
        return m.material(modelo, True)
    modelo = f"Nos próximos {dias} dias vencem {n} contrato(s) do fornecedor {cnpj} ({ufs}), somando {valor}."
    if t.get("percentual_do_vigente") is not None:
        pct = m.add(
            t["percentual_do_vigente"],
            "percentual",
            "parte do valor vigente que vence no prazo",
            "valor_vencendo / valor_vigente_total",
        )
        modelo += f" Isso é {pct} do valor vigente."
    modelo += f" O primeiro vence em {primeiro}."
    return m.material(modelo, False, _registros_contratos(linhas))


@modelo_da_intent("pagamentos_periodo")
def _pagamentos(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    cnpj = _cnpj(m, r)
    inicio = m.add(
        r.parametros["data_inicio"], "data", "início do período", "parametros.data_inicio", essencial=False
    )
    fim = m.add(r.parametros["data_fim"], "data", "fim do período", "parametros.data_fim", essencial=False)
    n = m.add(
        t["n_pagamentos"],
        "inteiro",
        "número de pagamentos no período (sem contar empenhos)",
        "count(pagamentos)",
    )
    valor = m.add(
        t["valor_total"], "moeda", "valor pago no período (sem contar empenhos)", "sum(pagamentos.valor)"
    )
    ufs = _ufs_marcador(m, r)
    if not linhas:
        modelo = (
            f"Não encontrei pagamentos ao fornecedor {cnpj} entre {inicio} e {fim} "
            f"nas fontes autorizadas para você ({ufs})."
        )
    else:
        modelo = (
            f"Entre {inicio} e {fim}, o fornecedor {cnpj} recebeu {n} pagamento(s) "
            f"nas fontes autorizadas para você ({ufs}), num total de {valor}."
        ) + _frase_empenho(m, t)
    registros = tuple(
        f"- Pagamento do órgão {dado_nao_confiavel(p.get('orgao_nome'))} (UF {p['uf']}): "
        f"{dado_nao_confiavel(p.get('descricao'))}"
        for p in linhas[:LIMITE_REGISTROS_TEXTO]
    )
    return m.material(modelo, not linhas, registros)


@modelo_da_intent("sancoes_fornecedor")
def _sancoes(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    cnpj = _cnpj(m, r)
    n = m.add(t["n_sancoes"], "inteiro", "número de sanções registradas", "count(sancoes)")
    vig = m.add(t["n_vigentes"], "inteiro", "número de sanções vigentes", "count(sancoes vigentes)")
    if not linhas:
        return m.material(f"Não encontrei sanções do fornecedor {cnpj} no CEIS nem no CNEP.", True)
    modelo = (
        f"O fornecedor {cnpj} tem {n} sanção(ões) registradas no CEIS ou no CNEP, das quais {vig} vigente(s)."
    )
    if t["n_vigentes"]:
        modelo += " Sanção vigente é um sinal para investigar."
    registros = tuple(
        f"- Sanção ({s['fonte_id'].upper()}, {'vigente' if s['vigente'] else 'encerrada'}): "
        f"{dado_nao_confiavel(s.get('tipo'))}, aplicada por {dado_nao_confiavel(s.get('orgao_sancionador'))}"
        for s in linhas[:LIMITE_REGISTROS_TEXTO]
    )
    return m.material(modelo, False, registros)


if faltando := intents_sem_modelo():
    raise RuntimeError(f"consulta do catálogo sem marcadores e modelo: {sorted(faltando)}")


# ------------------------------------------------------------------ entrada
def _com_data_da_coleta(material: Material, coletado_em: date | datetime) -> Material:
    """SPEC §8.4: a abstenção diz até quando as fontes foram coletadas."""
    m = _Montador(material.marcadores)
    data = coletado_em.date() if isinstance(coletado_em, datetime) else coletado_em
    marcador = m.add(
        data, "data", "data da coleta mais recente das fontes", "fontes.coletado_em", essencial=False
    )
    return replace(
        material, marcadores=m.marcadores, modelo=f"{material.modelo} Fontes coletadas até {marcador}."
    )


def montar_material(
    resultado: ResultadoConsulta, *, fontes_coletadas_em: date | datetime | None = None
) -> Material:
    material = _POR_INTENT[resultado.intent](resultado)
    if material.vazio and fontes_coletadas_em is not None:
        return _com_data_da_coleta(material, fontes_coletadas_em)
    return material
