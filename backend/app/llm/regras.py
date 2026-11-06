"""Planejador por regras: CNPJ, UF, período e palavras-chave. Sem rede e determinístico.

É o planejador do modo `LLM_PROVIDER=mock` e o fallback quando a LLM falha. Devolve o mesmo
PlanoConsulta que o planejador com LLM.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from app.llm.plano import Parametros, PlanoConsulta, esclarecer, fora_de_escopo
from app.modules.catalogo.intents import UFS

PERGUNTA_CNPJ = "De qual fornecedor? Informe o CNPJ com 14 dígitos."
PERGUNTA_CNPJ_INVALIDO = "O CNPJ informado não tem 14 dígitos. Pode conferir?"
PERGUNTA_PERIODO = "Qual período? Por exemplo: em 2025, ou entre 01/01/2025 e 30/06/2025."
PERGUNTA_CARTEIRA = "De qual carteira? Abra a carteira e pergunte por lá."
PERGUNTA_GENERICA = (
    "Pode detalhar? Diga o CNPJ do fornecedor e o que quer saber (contratos, pagamentos, sanções)."
)

ESTADOS = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM", "bahia": "BA", "ceara": "CE",
    "distrito federal": "DF", "espirito santo": "ES", "goias": "GO", "maranhao": "MA",
    "mato grosso do sul": "MS", "mato grosso": "MT", "minas gerais": "MG", "para": "PA",
    "paraiba": "PB", "parana": "PR",
    "pernambuco": "PE", "piaui": "PI", "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rio grande do sul": "RS", "rondonia": "RO", "roraima": "RR", "santa catarina": "SC",
    "sao paulo": "SP", "sergipe": "SE", "tocantins": "TO",
}  # fmt: skip

NUMEROS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
           "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12}  # fmt: skip

# Pedidos que tentam mudar as regras, ver instruções ou sair do escopo da sessão.
FORA_DO_PERMITIDO = re.compile(
    r"ignor\w*\s+(as\s+|todas\s+as\s+)?(instruc|regras|ordens)"
    r"|prompt|instrucoes do sistema|modo desenvolvedor|sem restric"
    r"|todos os (clientes|estados|tenants)|outros? (clientes?|tenants?)|de outro cliente"
)

# Assuntos do catálogo, em ordem de prioridade.
ASSUNTOS: list[tuple[str, re.Pattern[str]]] = [
    ("socios_sancionados", re.compile(r"\bsoci[oa]s?\b|quadro societario")),
    ("sancoes_fornecedor", re.compile(r"sanc|sancion|\bceis\b|\bcnep\b|inidone|punid|impedid")),
    ("contratos_vencendo", re.compile(r"\bvenc|terminam|\btermina\b|\bacaba|expira")),
    ("contratos_vigentes", re.compile(r"vigent|em vigor|contratos ativos")),
    ("pagamentos_periodo", re.compile(r"pagament|\bpag[oa]s?\b|\bpagou|liquidac|empenh")),
    ("orgaos_fornecedor", re.compile(r"\borgao|\borgaos|concentra|\bdepende")),
    ("resumo_fornecedor", re.compile(r"resum|receb|\btotal\b|\bvalor|historico|panorama|faturou")),
]

DOMINIO = re.compile(r"gast|govern|contrat|fornecedor|empresa|cnpj|pag|receb|licitac|despesa|orgao|valor")
# Em ordem: "objeto" tem prioridade, então em "contratos com objeto de X" o termo é X.
_TERMO = r"\s+(?:de\s+|do\s+|da\s+)?(?P<termo>[a-z0-9 ]{2,80})"
BUSCAS = [re.compile(r"objeto" + _TERMO), re.compile(r"(?:sobre|contratos? (?:de|para|com))" + _TERMO)]
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
DATA_BR = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
CANDIDATO_NUMERICO = re.compile(r"\d[\d./-]*\d")
DURACAO = re.compile(r"\b(\d{1,3}|" + "|".join(NUMEROS) + r")\s+(dias?|semanas?|mes|meses|anos?)\b")
ANO = re.compile(r"\b(20\d{2})\b")


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


@dataclass(frozen=True)
class Cnpj:
    valor: str | None
    invalido: bool


def extrair_cnpj(texto: str) -> Cnpj:
    sem_datas = DATA_BR.sub(" ", texto)
    invalido = False
    for m in CANDIDATO_NUMERICO.finditer(sem_datas):
        digitos = re.sub(r"\D", "", m.group())
        if len(digitos) == 14:
            return Cnpj(digitos, False)
        if 9 <= len(digitos) <= 18:
            invalido = True
    return Cnpj(None, invalido)


def extrair_uf(original: str, normalizado: str) -> str | None:
    for nome in sorted(ESTADOS, key=len, reverse=True):
        # "para" sem acento é também a preposição: só vale como Pará com artigo antes.
        padrao = r"\b(?:no|do|estado do) para\b" if nome == "para" else rf"\b{nome}\b"
        if re.search(padrao, normalizado):
            return ESTADOS[nome]
    for sigla in re.findall(r"\b([A-Z]{2})\b", original):
        if sigla in UFS:
            return sigla
    return None


def extrair_dias(t: str) -> int | None:
    m = DURACAO.search(t)
    if not m:
        return None
    n = int(m.group(1)) if m.group(1).isdigit() else NUMEROS[m.group(1)]
    unidade = m.group(2)
    fator = (
        1
        if unidade.startswith("dia")
        else 7
        if unidade.startswith("semana")
        else 365
        if unidade.startswith("ano")
        else 30
    )
    return max(1, min(365, n * fator))


def extrair_periodo(t: str, hoje: date) -> tuple[date, date] | None:
    datas = DATA_BR.findall(t)
    if len(datas) >= 2:
        try:
            inicio, fim = (date(int(a), int(m), int(d)) for d, m, a in datas[:2])
        except ValueError:
            return None
        return (inicio, fim) if inicio <= fim else (fim, inicio)
    if re.search(r"ultim[oa]s?", t) and (dias := extrair_dias(t)):
        return hoje - timedelta(days=dias), hoje
    if m := ANO.search(DATA_BR.sub(" ", t)):
        ano = int(m.group(1))
        return date(ano, 1, 1), date(ano, 12, 31)
    return None


def planejar_por_regras(pergunta: str, hoje: date) -> PlanoConsulta:
    t = normalizar(pergunta)

    if FORA_DO_PERMITIDO.search(t):
        return fora_de_escopo("pedido fora do permitido")

    cnpj = extrair_cnpj(pergunta)
    uf = extrair_uf(pergunta, t)

    if re.search(r"\bcarteira\b|\bfila\b", t):
        if m := UUID_RE.search(pergunta):
            return PlanoConsulta(intent="fila_carteira", parametros=Parametros(carteira_id=UUID(m.group())))
        return esclarecer(PERGUNTA_CARTEIRA)

    assunto = next((intent for intent, padrao in ASSUNTOS if padrao.search(t)), None)

    busca = next((m for padrao in BUSCAS if (m := padrao.search(t))), None)
    if assunto is None and cnpj.valor is None and (m := busca):
        termo = m.group("termo").strip()
        if len(termo) >= 2:
            return PlanoConsulta(
                intent="busca_objeto", parametros=Parametros(termo=termo[:80].strip(), uf=uf)
            )

    if assunto is None:
        if DOMINIO.search(t) or cnpj.valor or cnpj.invalido:
            return esclarecer(PERGUNTA_GENERICA)
        return fora_de_escopo("pergunta fora do catálogo")

    if cnpj.valor is None:
        return esclarecer(PERGUNTA_CNPJ_INVALIDO if cnpj.invalido else PERGUNTA_CNPJ)

    p = Parametros(cnpj=cnpj.valor)
    if assunto in ("resumo_fornecedor", "contratos_vigentes", "orgaos_fornecedor"):
        p.uf = uf
    elif assunto == "contratos_vencendo":
        p.uf = uf
        p.dias = extrair_dias(t) or 180
    elif assunto == "pagamentos_periodo":
        periodo = extrair_periodo(t, hoje)
        if periodo is None:
            return esclarecer(PERGUNTA_PERIODO)
        p.data_inicio, p.data_fim = periodo
        p.uf = uf
    return PlanoConsulta(intent=assunto, parametros=p)
