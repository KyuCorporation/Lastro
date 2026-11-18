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
from app.llm.texto_externo import dado_nao_confiavel, limpar
from app.modules.catalogo.executor import ResultadoConsulta
from app.modules.catalogo.registry import CONSULTAS

# SPEC §9: o sinal `concentracao` dispara quando o maior órgão responde por 70% ou mais.
LIMIAR_CONCENTRACAO = 70
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
    # Radicais (sem acento) que precisam aparecer junto do marcador no texto do redator. Vazio = não cobrado
    # (identificação e parâmetros da pergunta). O verificador usa para pegar valor com o sentido trocado.
    ancoras: tuple[str, ...] = ()

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
        self,
        valor: Any,
        tipo: TipoValor,
        significado: str,
        origem: str,
        *,
        essencial: bool = True,
        ancoras: tuple[str, ...] = (),
    ) -> str:
        mid = f"v{len(self.marcadores) + 1}"
        self.marcadores[mid] = Marcador(mid, valor, tipo, significado, origem, ancoras)
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


# ------------------------------------------------------------------ âncoras
# Onde a intent tem mais de um valor do mesmo tipo (resumo: contratado, vigente, pago, empenhado), a âncora é
# estreita, para um não passar pelo outro. Onde só há um valor em reais, "soma" e "total" também valem.
A_CONTRATO = ("contrat",)
A_VIGENTE = ("vigent", "vigor")
A_PAGO = ("pag", "liquid", "receb", "desembols")
A_EMPENHO = ("empenh", "reserv")
A_VENCIMENTO = ("venc", "termin", "fim", "acab", "encerr", "expir")
A_SANCAO = ("sanc", "puni", "penalid")
A_VALOR_UNICO = ("contrat", "soma", "total", "valor")


# No TCE-PE o que entra como "saiu para o fornecedor" é a liquidação (despesa reconhecida pelo órgão), etapa
# anterior ao pagamento. O texto diz as duas coisas para não chamar liquidação de pagamento.
_LIQUIDACAO = "liquidação ou pagamento"
_LIQUIDACOES = "liquidações ou pagamentos"


# ------------------------------------------------------------------ partes comuns
LIMITE_TEXTO_DE_FONTE = 120


def _texto_de_fonte(valor: Any) -> str | None:
    """Texto de fonte (nome de órgão) ou do usuário (termo da busca) que vira valor de marcador.

    O código insere esse valor depois do verificador, então ele não passa pelas regras de lá: sai daqui já sem
    link, marcação, chaves e caractere de controle. Números ficam (nome de órgão pode ter) e não há regra de
    vocabulário (nome oficial pode conter "corrupção", como numa secretaria de prevenção)."""
    return None if valor is None else limpar(valor, limite=LIMITE_TEXTO_DE_FONTE, mascarar_numeros=False)


def _p(n: int, singular: str, plural: str) -> str:
    """Concordância do texto pronto: o código sabe o valor, então escolhe a forma certa (nada de "contrato(s)")."""
    return singular if n == 1 else plural


def _ufs(resultado: ResultadoConsulta) -> str:
    return ", ".join(resultado.parametros.get("ufs", []))


def _cnpj(m: _Montador, resultado: ResultadoConsulta) -> str:
    cnpj = resultado.parametros["cnpj"]
    return m.add(formatar_cnpj(cnpj), "texto", "CNPJ do fornecedor", "parametros.cnpj", essencial=False)


def _ufs_marcador(m: _Montador, resultado: ResultadoConsulta) -> str:
    return m.add(_ufs(resultado), "texto", "UFs consultadas", "parametros.ufs", essencial=False)


def _frase_empenho(m: _Montador, t: dict[str, Any]) -> str:
    """Empenho é reserva no orçamento, etapa anterior à liquidação: aparece à parte e só quando existe.

    Os marcadores entram depois dos demais, então a numeração de quem não tem empenho não muda.
    """
    if not t["n_empenhos"]:
        return ""
    v_e = m.add(
        t["valor_empenhado"],
        "moeda",
        "valor empenhado (reservado no orçamento)",
        "sum(empenhos.valor)",
        ancoras=A_EMPENHO,
    )
    n_e = m.add(t["n_empenhos"], "inteiro", "número de empenhos", "count(empenhos)", ancoras=A_EMPENHO)
    empenhos = _p(t["n_empenhos"], "empenho", "empenhos")
    return (
        f" Há ainda {v_e} empenhados em {n_e} {empenhos}: reserva no orçamento, etapa anterior à liquidação."
    )


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
    n_c = m.add(t["n_contratos"], "inteiro", "número de contratos", "count(contratos)", ancoras=A_CONTRATO)
    v_c = m.add(
        t["valor_contratado"],
        "moeda",
        "valor contratado somado",
        "sum(contratos.valor_global)",
        ancoras=A_CONTRATO,
    )
    v_v = m.add(
        t["valor_vigente"],
        "moeda",
        "valor dos contratos ainda vigentes",
        "sum(valor_global) vigentes",
        ancoras=A_VIGENTE,
    )
    n_p = m.add(
        t["n_pagamentos"],
        "inteiro",
        "número de liquidações e pagamentos (sem contar empenhos)",
        "count(pagamentos)",
        ancoras=A_PAGO,
    )
    v_p = m.add(
        t["valor_pago"],
        "moeda",
        "valor liquidado ou pago (sem contar empenhos)",
        "sum(pagamentos.valor)",
        ancoras=A_PAGO,
    )
    ufs = _ufs_marcador(m, r)
    vazio = t["n_contratos"] == 0 and t["n_pagamentos"] == 0 and t["n_empenhos"] == 0
    if vazio:
        modelo = (
            f"Não encontrei contratos, liquidações nem pagamentos do fornecedor {cnpj} "
            f"nas fontes autorizadas para você ({ufs})."
        )
    else:
        modelo = (
            f"Nas fontes autorizadas para você ({ufs}), o fornecedor {cnpj} tem {n_c} "
            f"{_p(t['n_contratos'], 'contrato', 'contratos')}, somando {v_c}, dos quais {v_v} em contratos "
            f"ainda vigentes. {_p(t['n_pagamentos'], 'Foi registrada', 'Foram registradas')} {n_p} "
            f"{_p(t['n_pagamentos'], _LIQUIDACAO, _LIQUIDACOES)}, num total de {v_p}."
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
    n = m.add(
        t["n_contratos"],
        "inteiro",
        "número de contratos vigentes",
        "count(contratos vigentes)",
        ancoras=A_CONTRATO + A_VIGENTE,
    )
    valor = m.add(
        t["valor_total"],
        "moeda",
        "valor somado dos contratos vigentes",
        "sum(valor_global)",
        ancoras=A_VALOR_UNICO + A_VIGENTE,
    )
    proximo = m.add(
        min((c["vigencia_fim"] for c in linhas), default=None),
        "data",
        "data do próximo fim de vigência",
        "min(vigencia_fim)",
        ancoras=A_VENCIMENTO,
    )
    ufs = _ufs_marcador(m, r)
    if not linhas:
        modelo = (
            f"Não encontrei contratos vigentes do fornecedor {cnpj} nas fontes autorizadas para você ({ufs})."
        )
    else:
        modelo = (
            f"O fornecedor {cnpj} tem {n} {_p(t['n_contratos'], 'contrato vigente', 'contratos vigentes')} "
            f"nas fontes autorizadas para você ({ufs}), "
            f"somando {valor}. O próximo a terminar vence em {proximo}."
        )
    return m.material(modelo, not linhas, _registros_contratos(linhas))


@modelo_da_intent("contratos_vencendo")
def _vencendo(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    cnpj = _cnpj(m, r)
    dias = m.add(r.parametros["dias"], "inteiro", "prazo em dias", "parametros.dias", essencial=False)
    n = m.add(
        t["n_contratos"],
        "inteiro",
        "número de contratos que vencem no prazo",
        "count(contratos)",
        ancoras=A_CONTRATO + A_VENCIMENTO,
    )
    valor = m.add(
        t["valor_vencendo"],
        "moeda",
        "valor somado dos contratos que vencem",
        "sum(valor_global)",
        ancoras=A_VALOR_UNICO + A_VENCIMENTO,
    )
    primeiro = m.add(
        min((c["vigencia_fim"] for c in linhas), default=None),
        "data",
        "data do primeiro vencimento",
        "min(vigencia_fim)",
        ancoras=A_VENCIMENTO,
    )
    ufs = _ufs_marcador(m, r)
    if not linhas:
        modelo = (
            f"Não encontrei contratos do fornecedor {cnpj} que vençam nos próximos {dias} dias "
            f"nas fontes autorizadas para você ({ufs})."
        )
        return m.material(modelo, True)
    vence = _p(t["n_contratos"], "vence", "vencem")
    contratos = _p(t["n_contratos"], "contrato", "contratos")
    modelo = (
        f"Nos próximos {dias} dias {vence} {n} {contratos} do fornecedor {cnpj} ({ufs}), somando {valor}."
    )
    if t.get("percentual_do_vigente") is not None:
        pct = m.add(
            t["percentual_do_vigente"],
            "percentual",
            "parte do valor vigente que vence no prazo",
            "valor_vencendo / valor_vigente_total",
            ancoras=A_VIGENTE + A_VENCIMENTO,
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
        "número de liquidações e pagamentos no período (sem contar empenhos)",
        "count(pagamentos)",
        ancoras=A_PAGO,
    )
    valor = m.add(
        t["valor_total"],
        "moeda",
        "valor liquidado ou pago no período (sem contar empenhos)",
        "sum(pagamentos.valor)",
        ancoras=A_PAGO,
    )
    ufs = _ufs_marcador(m, r)
    if not linhas:
        modelo = (
            f"Não encontrei liquidações nem pagamentos ao fornecedor {cnpj} entre {inicio} e {fim} "
            f"nas fontes autorizadas para você ({ufs})."
        )
    else:
        modelo = (
            f"Entre {inicio} e {fim}, o fornecedor {cnpj} teve {n} "
            f"{_p(t['n_pagamentos'], _LIQUIDACAO + ' registrado', _LIQUIDACOES + ' registrados')} "
            f"nas fontes autorizadas para você ({ufs}), num total de {valor}."
        ) + _frase_empenho(m, t)
    registros = tuple(
        f"- Liquidação ou pagamento do órgão {dado_nao_confiavel(p.get('orgao_nome'))} (UF {p['uf']}): "
        f"{dado_nao_confiavel(p.get('descricao'))}"
        for p in linhas[:LIMITE_REGISTROS_TEXTO]
    )
    return m.material(modelo, not linhas, registros)


def _situacao_sancao(s: dict) -> str:
    if s["vigente"]:
        return "vigente"
    return "retirada do cadastro" if s.get("removida_em") else "encerrada"


@modelo_da_intent("sancoes_fornecedor")
def _sancoes(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    cnpj = _cnpj(m, r)
    n = m.add(t["n_sancoes"], "inteiro", "número de sanções registradas", "count(sancoes)", ancoras=A_SANCAO)
    vig = m.add(
        t["n_vigentes"],
        "inteiro",
        "número de sanções vigentes",
        "count(sancoes vigentes)",
        ancoras=(*A_VIGENTE, "ativ", "valend"),
    )
    if not linhas:
        return m.material(f"Não encontrei sanções do fornecedor {cnpj} no CEIS nem no CNEP.", True)
    registradas = _p(t["n_sancoes"], "sanção registrada", "sanções registradas")
    vigentes = _p(t["n_vigentes"], "vigente", "vigentes")
    modelo = (
        f"O fornecedor {cnpj} tem {n} {registradas} no CEIS ou no CNEP, das quais {vig} {vigentes}."
        if t["n_sancoes"] > 1
        else f"O fornecedor {cnpj} tem {n} {registradas} no CEIS ou no CNEP"
        + (
            ", ainda vigente."
            if t["n_vigentes"]
            else ", retirada do cadastro pela fonte."
            if linhas[0].get("removida_em")
            else ", já encerrada."
        )
    )
    if t["n_vigentes"]:
        modelo += " Sanção vigente é um sinal para investigar."
    registros = tuple(
        f"- Sanção ({s['fonte_id'].upper()}, {_situacao_sancao(s)}): "
        f"{dado_nao_confiavel(s.get('tipo'))}, aplicada por {dado_nao_confiavel(s.get('orgao_sancionador'))}"
        for s in linhas[:LIMITE_REGISTROS_TEXTO]
    )
    return m.material(modelo, False, registros)


@modelo_da_intent("orgaos_fornecedor")
def _orgaos(r: ResultadoConsulta) -> Material:
    m, t, ranking = _Montador(), r.totais, r.conjuntos["ranking"]
    cnpj = _cnpj(m, r)
    n_o = m.add(t["n_orgaos"], "inteiro", "número de órgãos contratantes", "count(orgaos)", ancoras=("orga",))
    valor = m.add(
        t["valor_total"],
        "moeda",
        "valor contratado somado",
        "sum(contratos.valor_global)",
        ancoras=A_VALOR_UNICO,
    )
    ufs = _ufs_marcador(m, r)
    if not ranking:
        modelo = f"Não encontrei contratos do fornecedor {cnpj} nas fontes autorizadas para você ({ufs})."
        return m.material(modelo, True)
    maior = m.add(
        _texto_de_fonte(t["maior_orgao"]),
        "texto",
        "nome do órgão com maior valor",
        "ranking[0].orgao_nome",
        essencial=False,
    )
    pct = m.add(
        t["maior_participacao"],
        "percentual",
        "participação do maior órgão no valor contratado",
        "ranking[0].participacao",
        ancoras=("particip", "concentr", "maior", "parte", "valor"),
    )
    orgaos = _p(t["n_orgaos"], "órgão", "órgãos")
    modelo = (
        f"Nas fontes autorizadas para você ({ufs}), o fornecedor {cnpj} tem contratos com {n_o} {orgaos}, "
        f"somando {valor}. O maior é {maior}, com {pct} do valor contratado."
    )
    # A base é o valor contratado; o sinal `concentracao` da pipeline (SPEC §9) mede o recebido. O texto diz a base
    # para "dinheiro" não ser lido como recebido (G100).
    if t["maior_participacao"] is not None and t["maior_participacao"] >= LIMIAR_CONCENTRACAO:
        modelo += " Concentração do valor contratado em um só órgão é um sinal para investigar."
    registros = tuple(
        f"- Órgão {dado_nao_confiavel(g.get('orgao_nome'))} (UF {g['uf']})"
        for g in ranking[:LIMITE_REGISTROS_TEXTO]
    )
    return m.material(modelo, False, registros)


@modelo_da_intent("busca_objeto")
def _busca(r: ResultadoConsulta) -> Material:
    m, t, linhas = _Montador(), r.totais, r.conjuntos["linhas"]
    termo = m.add(
        _texto_de_fonte(r.parametros["termo"]),
        "texto",
        "termo pesquisado",
        "parametros.termo",
        essencial=False,
    )
    n = m.add(
        t["n_contratos"],
        "inteiro",
        "número de contratos encontrados",
        "count(contratos)",
        ancoras=(*A_CONTRATO, "encontr", "resultado"),
    )
    valor = m.add(
        t["valor_total"],
        "moeda",
        "valor somado dos contratos encontrados",
        "sum(valor_global)",
        ancoras=A_VALOR_UNICO,
    )
    ufs = _ufs_marcador(m, r)
    if not linhas:
        modelo = f"Não encontrei contratos com objeto relacionado a {termo} nas fontes autorizadas para você ({ufs})."
        return m.material(modelo, True)
    contratos = _p(t["n_contratos"], "contrato", "contratos")
    modelo = (
        f"Encontrei {n} {contratos} com objeto relacionado a {termo} nas fontes autorizadas para você ({ufs}), "
        f"somando {valor}."
    )
    if t["n_contratos"] > len(linhas):
        modelo += " Os mais relevantes estão citados abaixo."
    return m.material(modelo, False, _registros_contratos(linhas))


# Nome de cada sinal no texto, igual ao da interface (frontend/src/lib/apresentacao.ts). Vocabulário do código.
NOME_SINAL = {
    "sancao_direta": "sanção vigente",
    "penhasco": "vencimentos concentrados",
    "concentracao": "concentração em um órgão",
    "contagio": "sócio em comum com empresa sancionada",
    "liquidez": "liquidez",
}


def _nomes_sinais(tipos: Any) -> str:
    return ", ".join(NOME_SINAL.get(t, t) for t in tipos)


@modelo_da_intent("fila_carteira")
def _fila(r: ResultadoConsulta) -> Material:
    m, t, fila = _Montador(), r.totais, r.conjuntos["fila"]
    if not fila:
        # Carteira sem itens ou de outro tenant (a RLS não mostra): mesma resposta, sem dizer qual dos dois.
        return m.material("Não encontrei fornecedores nesta carteira.", True)
    n = m.add(
        t["n_fornecedores"],
        "inteiro",
        "número de fornecedores na carteira",
        "count(carteira_itens)",
        ancoras=("fornec", "empresa", "carteira"),
    )
    n_s = m.add(
        t["n_com_sinal"],
        "inteiro",
        "número de fornecedores da carteira com sinal para investigar",
        "count(fornecedores com sinal)",
        ancoras=("sina",),
    )
    valor = m.add(
        t["valor_exposto"],
        "moeda",
        "valor somado dos contratos vigentes dos fornecedores da carteira",
        "sum(contratos.valor_global) vigentes",
        ancoras=(*A_VIGENTE, "expost", "exposi"),
    )
    ufs = _ufs_marcador(m, r)
    fornecedores = _p(t["n_fornecedores"], "fornecedor", "fornecedores")
    modelo = f"A carteira tem {n} {fornecedores}"
    if t["n_com_sinal"]:
        modelo += f": {n_s} com sinal para investigar"
        if t["n_com_sinal_forte"]:
            n_f = m.add(
                t["n_com_sinal_forte"],
                "inteiro",
                "número de fornecedores com sinal forte",
                "count(fornecedores com sinal forte)",
                ancoras=("fort",),
            )
            modelo += f" ({n_f} com sinal forte)"
        modelo += "."
    else:
        modelo += ", nenhum com sinal para investigar."
    modelo += f" Nas fontes autorizadas para você ({ufs}), os contratos vigentes deles somam {valor}."
    if t["primeiro_cnpj"]:
        cnpj = m.add(
            formatar_cnpj(t["primeiro_cnpj"]),
            "texto",
            "CNPJ do primeiro fornecedor da fila",
            "fila[0].cnpj",
            essencial=False,
        )
        sinais = m.add(
            _nomes_sinais(t["primeiro_tipos"]),
            "texto",
            "sinais do primeiro fornecedor da fila",
            "fila[0].tipos",
            essencial=False,
        )
        modelo += f" O primeiro da fila é o fornecedor {cnpj}, com {sinais}: sinal para investigar."
    registros = tuple(
        f"- Fornecedor {dado_nao_confiavel(f.get('razao_social'))}: "
        + (f"sinais: {_nomes_sinais(f['tipos'])}" if f["tipos"] else "sem sinal")
        for f in fila[:LIMITE_REGISTROS_TEXTO]
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
