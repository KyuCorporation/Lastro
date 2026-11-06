"""Marcadores e modelos determinísticos por intent.

Todo número, valor, data e CNPJ da resposta sai daqui, do resultado do catálogo. O redator só vê os marcadores
(`{{v1}}`) e o significado de cada um. O modelo determinístico é o texto pronto da intent, usado no modo mock,
quando o verificador reprova o redator e quando o resultado vem vazio (abstenção).
"""

from dataclasses import dataclass, field
from typing import Any

from app.llm.formatacao import TipoValor, formatar, formatar_cnpj
from app.modules.catalogo.executor import ResultadoConsulta
from app.modules.catalogo.registry import CONSULTAS

LIMITE_REGISTROS_TEXTO = 5


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
    # Texto vindo das fontes (nome de órgão, objeto, tipo de sanção), sem nenhum número do resultado.
    registros: tuple[str, ...] = field(default_factory=tuple)


class _Montador:
    def __init__(self) -> None:
        self.marcadores: dict[str, Marcador] = {}

    def add(self, valor: Any, tipo: TipoValor, significado: str, origem: str) -> str:
        mid = f"v{len(self.marcadores) + 1}"
        self.marcadores[mid] = Marcador(mid, valor, tipo, significado, origem)
        return "{{" + mid + "}}"


def nao_confiavel(texto: Any) -> str:
    """Envolve texto de fonte externa. O próprio texto não pode abrir nem fechar a marcação."""
    limpo = str(texto or "").replace("<dado_nao_confiavel>", "").replace("</dado_nao_confiavel>", "")
    return f"<dado_nao_confiavel>{limpo[:300]}</dado_nao_confiavel>"


def _ufs(resultado: ResultadoConsulta) -> str:
    return ", ".join(resultado.parametros.get("ufs", []))


def _cnpj(m: _Montador, resultado: ResultadoConsulta) -> str:
    cnpj = resultado.parametros["cnpj"]
    return m.add(formatar_cnpj(cnpj), "texto", "CNPJ do fornecedor", "parametros.cnpj")


def _registros_contratos(linhas: list[dict]) -> tuple[str, ...]:
    return tuple(
        f"- Contrato com o órgão {nao_confiavel(c.get('orgao_nome'))} (UF {c['uf']}), "
        f"objeto: {nao_confiavel(c.get('objeto'))}"
        for c in linhas[:LIMITE_REGISTROS_TEXTO]
    )


def _resumo(r: ResultadoConsulta) -> Material:
    m, t = _Montador(), r.totais
    cnpj = _cnpj(m, r)
    n_c = m.add(t["n_contratos"], "inteiro", "número de contratos", "count(contratos)")
    v_c = m.add(t["valor_contratado"], "moeda", "valor contratado somado", "sum(contratos.valor_global)")
    v_v = m.add(
        t["valor_vigente"], "moeda", "valor dos contratos ainda vigentes", "sum(valor_global) vigentes"
    )
    n_p = m.add(t["n_pagamentos"], "inteiro", "número de pagamentos", "count(pagamentos)")
    v_p = m.add(t["valor_pago"], "moeda", "valor pago somado", "sum(pagamentos.valor)")
    ufs = m.add(_ufs(r), "texto", "UFs consultadas", "parametros.ufs")
    vazio = t["n_contratos"] == 0 and t["n_pagamentos"] == 0
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
        )
    registros = tuple(
        f"- Órgão {nao_confiavel(g.get('orgao_nome'))} (UF {g['uf']})"
        for g in r.conjuntos["por_uf_orgao"][:LIMITE_REGISTROS_TEXTO]
    )
    return Material(m.marcadores, modelo, vazio, registros)


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
    ufs = m.add(_ufs(r), "texto", "UFs consultadas", "parametros.ufs")
    if not linhas:
        modelo = (
            f"Não encontrei contratos vigentes do fornecedor {cnpj} nas fontes autorizadas para você ({ufs})."
        )
    else:
        modelo = (
            f"O fornecedor {cnpj} tem {n} contrato(s) vigente(s) nas fontes autorizadas para você ({ufs}), "
            f"somando {valor}. O próximo a terminar vence em {proximo}."
        )
    return Material(m.marcadores, modelo, not linhas, _registros_contratos(linhas))


def _vencendo(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    cnpj = _cnpj(m, r)
    dias = m.add(r.parametros["dias"], "inteiro", "prazo em dias", "parametros.dias")
    n = m.add(t["n_contratos"], "inteiro", "número de contratos que vencem no prazo", "count(contratos)")
    valor = m.add(t["valor_vencendo"], "moeda", "valor somado dos contratos que vencem", "sum(valor_global)")
    primeiro = m.add(
        min((c["vigencia_fim"] for c in linhas), default=None),
        "data",
        "data do primeiro vencimento",
        "min(vigencia_fim)",
    )
    ufs = m.add(_ufs(r), "texto", "UFs consultadas", "parametros.ufs")
    if not linhas:
        modelo = (
            f"Não encontrei contratos do fornecedor {cnpj} que vençam nos próximos {dias} dias "
            f"nas fontes autorizadas para você ({ufs})."
        )
        return Material(m.marcadores, modelo, True)
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
    return Material(m.marcadores, modelo, False, _registros_contratos(linhas))


def _pagamentos(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    cnpj = _cnpj(m, r)
    inicio = m.add(r.parametros["data_inicio"], "data", "início do período", "parametros.data_inicio")
    fim = m.add(r.parametros["data_fim"], "data", "fim do período", "parametros.data_fim")
    n = m.add(t["n_pagamentos"], "inteiro", "número de pagamentos no período", "count(pagamentos)")
    valor = m.add(t["valor_total"], "moeda", "valor pago no período", "sum(pagamentos.valor)")
    ufs = m.add(_ufs(r), "texto", "UFs consultadas", "parametros.ufs")
    if not linhas:
        modelo = (
            f"Não encontrei pagamentos ao fornecedor {cnpj} entre {inicio} e {fim} "
            f"nas fontes autorizadas para você ({ufs})."
        )
    else:
        modelo = (
            f"Entre {inicio} e {fim}, o fornecedor {cnpj} recebeu {n} pagamento(s) "
            f"nas fontes autorizadas para você ({ufs}), num total de {valor}."
        )
    registros = tuple(
        f"- Pagamento do órgão {nao_confiavel(p.get('orgao_nome'))} (UF {p['uf']}): "
        f"{nao_confiavel(p.get('descricao'))}"
        for p in linhas[:LIMITE_REGISTROS_TEXTO]
    )
    return Material(m.marcadores, modelo, not linhas, registros)


def _sancoes(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    cnpj = _cnpj(m, r)
    n = m.add(t["n_sancoes"], "inteiro", "número de sanções registradas", "count(sancoes)")
    vig = m.add(t["n_vigentes"], "inteiro", "número de sanções vigentes", "count(sancoes vigentes)")
    if not linhas:
        return Material(
            m.marcadores, f"Não encontrei sanções do fornecedor {cnpj} no CEIS nem no CNEP.", True
        )
    modelo = (
        f"O fornecedor {cnpj} tem {n} sanção(ões) registradas no CEIS ou no CNEP, das quais {vig} vigente(s)."
    )
    if t["n_vigentes"]:
        modelo += " Sanção vigente é um sinal para investigar."
    registros = tuple(
        f"- Sanção ({s['fonte_id'].upper()}, {'vigente' if s['vigente'] else 'encerrada'}): "
        f"{nao_confiavel(s.get('tipo'))}, aplicada por {nao_confiavel(s.get('orgao_sancionador'))}"
        for s in linhas[:LIMITE_REGISTROS_TEXTO]
    )
    return Material(m.marcadores, modelo, False, registros)


_POR_INTENT = {
    "resumo_fornecedor": _resumo,
    "contratos_vigentes": _vigentes,
    "contratos_vencendo": _vencendo,
    "pagamentos_periodo": _pagamentos,
    "sancoes_fornecedor": _sancoes,
}

assert set(_POR_INTENT) == set(CONSULTAS), "toda consulta do catálogo precisa de marcadores e modelo"


def montar_material(resultado: ResultadoConsulta) -> Material:
    return _POR_INTENT[resultado.intent](resultado)
