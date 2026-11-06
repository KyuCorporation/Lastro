"""Vocabulário que o verificador procura no texto do redator (SPEC §8.3).

Tudo aqui é comparado com o texto já normalizado (minúsculas, sem acento: `regras.normalizar`).
Incluir uma palavra só deixa o verificador mais rígido: na dúvida, o texto cai no modelo determinístico.
"""

import re

# Quantidades escritas por extenso. "um/uma" ficam de fora porque são também artigo ("um contrato");
# "um milhão" é pego por "milhao". Ordinais ("primeiro") são permitidos: não afirmam quantidade nem valor.
NUMEROS_POR_EXTENSO = (
    "zero", "dois", "duas", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez",
    "onze", "doze", "treze", "catorze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove",
    "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa",
    "cem", "cento", "duzentos", "duzentas", "trezentos", "trezentas", "quatrocentos", "quatrocentas",
    "quinhentos", "quinhentas", "seiscentos", "seiscentas", "setecentos", "setecentas",
    "oitocentos", "oitocentas", "novecentos", "novecentas",
    "mil", "milhao", "milhoes", "bilhao", "bilhoes", "trilhao", "trilhoes",
    "dezena", "dezenas", "centena", "centenas", "duzia", "duzias", "milhar", "milhares",
    "metade", "dobro", "triplo", "ambos", "ambas",
)  # fmt: skip

# Datas sem número: mês por nome e referências relativas ao dia de hoje.
DATAS_POR_EXTENSO = (
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro",
    "outubro", "novembro", "dezembro", "amanha", "ontem", "anteontem",
)  # fmt: skip

# SPEC §4.1 e AGENTS.md §3.7: sinal não é acusação. Raízes, para pegar flexões.
ACUSACAO = (
    r"fraud", r"irregular", r"suspeit", r"corrup", r"ilicit", r"ilegal", r"criminos", r"\bcrime",
    r"superfatur", r"sobrepreco", r"propina", r"desvio de (?:dinheiro|recurso|verba)", r"lavagem de dinheiro",
    r"conluio", r"\bcartel", r"\bgolpe", r"\bpeculato", r"improbidade",
)  # fmt: skip

# Texto que revela o funcionamento interno ou fala das próprias instruções.
VAZAMENTO = (
    r"instruc(?:ao|oes) (?:do sistema|anteriores|que recebi)", r"\bprompt\b", r"minhas regras",
    r"regras (?:acima|do sistema)", r"dado_nao_confiavel", r"pergunta_do_usuario", r"modelo de linguagem",
    r"\bsou uma ia\b", r"\bmarcador(?:es)?\b",
)  # fmt: skip

# Afirmar ausência de registros quando o resultado tem linhas contradiz o resultado.
NEGA_REGISTROS = (
    r"nao encontr", r"nao (?:ha|existem?|constam?|foram encontrad\w*) (?:nenhum\w* )?(?:registro|dado|informac)",
    r"nenhum (?:registro|dado|resultado)", r"sem (?:registros|dados|resultados)\b",
)  # fmt: skip


def _alternativas(palavras: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(palavras) + r")\b")


def _padroes(padroes: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{p})" for p in padroes))


RE_NUMERO_POR_EXTENSO = _alternativas(NUMEROS_POR_EXTENSO)
RE_DATA_POR_EXTENSO = _alternativas(DATAS_POR_EXTENSO)
RE_ACUSACAO = _padroes(ACUSACAO)
RE_VAZAMENTO = _padroes(VAZAMENTO)
RE_NEGA_REGISTROS = _padroes(NEGA_REGISTROS)
