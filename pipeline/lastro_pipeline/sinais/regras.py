"""Regras dos sinais de risco, v1 (SPEC §9). Funções puras: recebem fatos já lidos do banco e devolvem sinais.

Sinal não é acusação: só `sancao_direta` é "forte"; o resto é "atenção". Toda explicação é uma frase e toda
evidência aponta para a linha de origem (`{tabela, id, url_origem}`).

Por UF: `penhasco` e `concentracao` são calculados por (fornecedor, UF) e só usam fatos daquela UF, para que a
RLS da tabela `sinais` não deixe vazar nada de uma UF fora do escopo. `sancao_direta` é nacional (uf nula): a
sanção do CEIS/CNEP vale em todo o país e a tabela `sancoes` já é visível a qualquer usuário autenticado.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal
from uuid import UUID

VERSAO_REGRA = "v1"

TipoSinal = Literal["sancao_direta", "penhasco", "concentracao"]
Gravidade = Literal["forte", "atencao", "info"]
TIPOS_CALCULADOS: tuple[TipoSinal, ...] = ("sancao_direta", "penhasco", "concentracao")

PENHASCO_DIAS = 180
PENHASCO_LIMIAR = Decimal("0.50")
CONCENTRACAO_MESES = 24
CONCENTRACAO_LIMIAR = Decimal("0.70")
# Evidências guardadas por sinal (as de maior valor). A explicação traz o total, então nada se perde no texto.
MAX_EVIDENCIAS = 50

NOME_FONTE_SANCAO = {"ceis": "CEIS", "cnep": "CNEP"}


# ===================== Entradas =====================


@dataclass(frozen=True)
class ContratoFato:
    id: UUID
    cnpj: str
    uf: str
    orgao_id: str | None
    valor: Decimal | None
    data_assinatura: date | None
    vigencia_inicio: date | None
    vigencia_fim: date | None
    url_origem: str | None


@dataclass(frozen=True)
class PagamentoFato:
    """Valor que saiu para o fornecedor (liquidação ou pagamento). Empenho não entra: é reserva, não recebimento."""

    id: UUID
    cnpj: str
    uf: str
    orgao_id: str | None
    valor: Decimal | None
    data: date | None
    url_origem: str | None


@dataclass(frozen=True)
class SancaoFato:
    id: UUID
    fonte_id: str
    cnpj: str
    tipo: str | None
    data_inicio: date | None
    data_fim: date | None
    url_origem: str | None


# ===================== Saída =====================


@dataclass(frozen=True)
class Sinal:
    fornecedor_cnpj: str
    uf: str | None
    tipo: TipoSinal
    gravidade: Gravidade
    valor: Decimal
    explicacao: str
    evidencias: list[dict[str, Any]] = field(default_factory=list)
    versao_regra: str = VERSAO_REGRA

    @property
    def chave(self) -> tuple[str, str | None, str]:
        """Identidade do sinal entre recálculos: o mesmo fornecedor, UF e tipo atualiza a mesma linha."""
        return (self.fornecedor_cnpj, self.uf, self.tipo)


# ===================== Formatação (só para a explicação) =====================


def moeda(valor: Decimal) -> str:
    inteiro, _, centavos = f"{valor.quantize(Decimal('0.01'), ROUND_HALF_UP):,.2f}".partition(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def percentual(fracao: Decimal) -> Decimal:
    return (fracao * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)


def pct(fracao: Decimal) -> str:
    return f"{percentual(fracao)}%".replace(".", ",")


def data_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _nome_curto(nome: str, limite: int = 120) -> str:
    """Nome de órgão vem da fonte externa: uma linha só e tamanho limitado na explicação."""
    nome = " ".join(nome.split())
    return nome if len(nome) <= limite else nome[: limite - 1].rstrip() + "…"


def _evidencia(tabela: str, id_: UUID, url: str | None) -> dict[str, Any]:
    return {"tabela": tabela, "id": str(id_), "url_origem": url}


def subtrair_meses(d: date, meses: int) -> date:
    ano, mes = divmod(d.year * 12 + d.month - 1 - meses, 12)
    mes += 1
    # dia 29–31 em mês mais curto: último dia do mês
    for dia in (d.day, 30, 29, 28):
        try:
            return date(ano, mes, dia)
        except ValueError:
            continue
    raise AssertionError("inalcançável")


# ===================== sancao_direta =====================


def sancao_vigente(s: SancaoFato, hoje: date) -> bool:
    """Começou (ou não tem início informado) e não terminou (sem data final = prazo indeterminado)."""
    comecou = s.data_inicio is None or s.data_inicio <= hoje
    nao_terminou = s.data_fim is None or s.data_fim >= hoje
    return comecou and nao_terminou


def sancao_direta(sancoes: Iterable[SancaoFato], hoje: date) -> list[Sinal]:
    por_cnpj: dict[str, list[SancaoFato]] = defaultdict(list)
    for s in sancoes:
        if sancao_vigente(s, hoje):
            por_cnpj[s.cnpj].append(s)

    sinais = []
    for cnpj, vigentes in sorted(por_cnpj.items()):
        vigentes.sort(key=lambda s: (s.data_inicio or date.min, str(s.id)))
        cadastros = sorted({NOME_FONTE_SANCAO.get(s.fonte_id, s.fonte_id.upper()) for s in vigentes})
        datas_fim = [s.data_fim for s in vigentes]
        if any(d is None for d in datas_fim):
            prazo = "uma delas sem prazo final" if len(vigentes) > 1 else "sem prazo final"
        else:
            prazo = f"até {data_br(max(d for d in datas_fim if d is not None))}"
        if len(vigentes) == 1:
            explicacao = f"Consta 1 sanção vigente no {cadastros[0]}, {prazo}."
        else:
            explicacao = f"Constam {len(vigentes)} sanções vigentes ({', '.join(cadastros)}), {prazo}."
        sinais.append(
            Sinal(
                fornecedor_cnpj=cnpj,
                uf=None,
                tipo="sancao_direta",
                gravidade="forte",
                valor=Decimal(len(vigentes)),
                explicacao=explicacao,
                evidencias=[_evidencia("sancoes", s.id, s.url_origem) for s in vigentes][:MAX_EVIDENCIAS],
            )
        )
    return sinais


# ===================== penhasco =====================


def contrato_vigente(c: ContratoFato, hoje: date) -> bool:
    """Mesmo critério do catálogo (`contratos_vigentes`): termina hoje ou depois e tem valor."""
    return c.vigencia_fim is not None and c.vigencia_fim >= hoje and c.valor is not None and c.valor > 0


def penhasco(contratos: Iterable[ContratoFato], hoje: date) -> list[Sinal]:
    limite = hoje + timedelta(days=PENHASCO_DIAS)
    grupos: dict[tuple[str, str], list[ContratoFato]] = defaultdict(list)
    for c in contratos:
        if contrato_vigente(c, hoje):
            grupos[(c.cnpj, c.uf)].append(c)

    sinais = []
    for (cnpj, uf), vigentes in sorted(grupos.items()):
        total = sum((c.valor for c in vigentes if c.valor is not None), Decimal(0))
        vencendo = [c for c in vigentes if c.vigencia_fim is not None and c.vigencia_fim <= limite]
        valor_vencendo = sum((c.valor for c in vencendo if c.valor is not None), Decimal(0))
        if total <= 0 or not vencendo:
            continue
        fracao = valor_vencendo / total
        if fracao < PENHASCO_LIMIAR:
            continue
        vencendo.sort(key=lambda c: (-(c.valor or 0), c.vigencia_fim or date.max, str(c.id)))
        n = len(vencendo)
        explicacao = (
            f"{pct(fracao)} do valor vigente em {uf} ({moeda(valor_vencendo)} de {moeda(total)}) termina "
            f"em até {PENHASCO_DIAS} dias, em {n} contrato{'s' if n > 1 else ''}."
        )
        sinais.append(
            Sinal(
                fornecedor_cnpj=cnpj,
                uf=uf,
                tipo="penhasco",
                gravidade="atencao",
                valor=percentual(fracao),
                explicacao=explicacao,
                evidencias=[_evidencia("contratos", c.id, c.url_origem) for c in vencendo][:MAX_EVIDENCIAS],
            )
        )
    return sinais


# ===================== concentracao =====================


@dataclass(frozen=True)
class _Recebimento:
    tabela: str
    id: UUID
    orgao_id: str | None
    valor: Decimal
    url_origem: str | None


def _recebimentos_por_grupo(
    contratos: Iterable[ContratoFato], pagamentos: Iterable[PagamentoFato], inicio: date, hoje: date
) -> dict[tuple[str, str], tuple[str, list[_Recebimento]]]:
    """Recebido na janela, por (fornecedor, UF).

    Usa os pagamentos (liquidações) quando a UF tem algum para o fornecedor. Fontes sem pagamento (o PNCP só
    traz contratos) usam o valor dos contratos assinados na janela, e a explicação diz isso.
    """
    pagos: dict[tuple[str, str], list[_Recebimento]] = defaultdict(list)
    for p in pagamentos:
        if p.data is not None and inicio <= p.data <= hoje and p.valor is not None and p.valor > 0:
            pagos[(p.cnpj, p.uf)].append(_Recebimento("pagamentos", p.id, p.orgao_id, p.valor, p.url_origem))

    contratados: dict[tuple[str, str], list[_Recebimento]] = defaultdict(list)
    for c in contratos:
        assinado = c.data_assinatura or c.vigencia_inicio
        if assinado is not None and inicio <= assinado <= hoje and c.valor is not None and c.valor > 0:
            contratados[(c.cnpj, c.uf)].append(
                _Recebimento("contratos", c.id, c.orgao_id, c.valor, c.url_origem)
            )

    grupos: dict[tuple[str, str], tuple[str, list[_Recebimento]]] = {}
    for chave in pagos.keys() | contratados.keys():
        if pagos.get(chave):
            grupos[chave] = ("pagamentos", pagos[chave])
        else:
            grupos[chave] = ("contratos", contratados[chave])
    return grupos


def concentracao(
    contratos: Iterable[ContratoFato],
    pagamentos: Iterable[PagamentoFato],
    hoje: date,
    nomes_orgaos: dict[str, str] | None = None,
) -> list[Sinal]:
    nomes_orgaos = nomes_orgaos or {}
    inicio = subtrair_meses(hoje, CONCENTRACAO_MESES)
    sinais = []
    for (cnpj, uf), (base, itens) in sorted(
        _recebimentos_por_grupo(contratos, pagamentos, inicio, hoje).items()
    ):
        total = sum((r.valor for r in itens), Decimal(0))
        por_orgao: dict[str, Decimal] = defaultdict(Decimal)
        for r in itens:
            if r.orgao_id is not None:  # órgão desconhecido conta no total, mas nunca como "o maior órgão"
                por_orgao[r.orgao_id] += r.valor
        if total <= 0 or not por_orgao:
            continue
        orgao, valor_orgao = max(por_orgao.items(), key=lambda kv: (kv[1], kv[0]))
        fracao = valor_orgao / total
        if fracao < CONCENTRACAO_LIMIAR:
            continue
        do_orgao = sorted((r for r in itens if r.orgao_id == orgao), key=lambda r: (-r.valor, str(r.id)))
        nome = _nome_curto(nomes_orgaos.get(orgao, orgao))
        medida = (
            "do valor recebido"
            if base == "pagamentos"
            else "do valor contratado (a fonte não traz pagamentos)"
        )
        explicacao = (
            f"{pct(fracao)} {medida} em {uf} nos últimos {CONCENTRACAO_MESES} meses "
            f"({moeda(valor_orgao)} de {moeda(total)}) vem de um único órgão: {nome}."
        )
        sinais.append(
            Sinal(
                fornecedor_cnpj=cnpj,
                uf=uf,
                tipo="concentracao",
                gravidade="atencao",
                valor=percentual(fracao),
                explicacao=explicacao,
                evidencias=[_evidencia(r.tabela, r.id, r.url_origem) for r in do_orgao][:MAX_EVIDENCIAS],
            )
        )
    return sinais


def calcular_todos(
    contratos: list[ContratoFato],
    pagamentos: list[PagamentoFato],
    sancoes: list[SancaoFato],
    hoje: date,
    nomes_orgaos: dict[str, str] | None = None,
) -> list[Sinal]:
    return [
        *sancao_direta(sancoes, hoje),
        *penhasco(contratos, hoje),
        *concentracao(contratos, pagamentos, hoje, nomes_orgaos),
    ]
