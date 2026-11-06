"""Verificador (SPEC §8.3): confere o texto do redator antes de qualquer valor chegar ao usuário.

O texto é analisado uma vez (`analisar`) e passa por regras independentes (`REGRAS`). Cada regra devolve o
motivo da reprovação ou `None`. Qualquer motivo reprova: o redator cai no modelo determinístico (fallback).
Aprovado, cada marcador é trocado pelo valor formatado que veio do resultado (`preencher`).

O que é reprovado (motivo):
- texto vazio ou longo demais (`texto_vazio`, `texto_longo`);
- caractere invisível, de controle, de direção (bidi) ou letra de outro alfabeto (`caractere_nao_permitido`);
- marcador que não existe ou quebrado (`marcador_desconhecido`, `marcador_malformado`);
- número, data ou quantidade fora dos marcadores, em algarismo de qualquer alfabeto ou por extenso, exceto
  anos citados no plano (`numero_fora_do_resultado`);
- link ou e-mail (`url_fora_do_resultado`);
- texto sobre as próprias instruções (`vazamento`) ou de acusação (`linguagem_de_acusacao`);
- UF fora do escopo da sessão (`uf_fora_do_escopo`);
- negar registros que o resultado tem (`contradiz_resultado`) ou não usar nenhum valor do resultado
  (`sem_valor_do_resultado`).
"""

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from app.llm import lexico
from app.llm.marcadores import Marcador
from app.llm.regras import normalizar, ufs_mencionadas

MARCADOR = re.compile(r"\{\{\s*(v\d+)\s*\}\}")
LIMITE_CARACTERES = 1200

_DIGITOS = re.compile(r"\d+(?:[.,/-]\d+)*")
_TLDS = "com|br|org|net|gov|edu|io|ly|me|app|info|biz|co|us|uk|xyz|site|online|dev|ai|tv|link|to|gl"
_URL = re.compile(
    rf"https?://|www\.|\b[\w-]+(?:\.[\w-]+)*\.(?:{_TLDS})\b|\b[\w.+-]+@[\w-]+",
    re.IGNORECASE,
)
_PERMITIDOS = frozenset("\n\tºª")  # quebras de linha e os indicadores ordinais de "nº", "1ª"
_CATEGORIAS_PROIBIDAS = frozenset({"Cc", "Cf", "Co", "Cs", "Cn", "Zl", "Zp", "Mn", "Mc", "Me"})


@dataclass(frozen=True)
class Verificacao:
    aprovado: bool
    texto_final: str
    motivos: tuple[str, ...]
    usados: tuple[str, ...]


@dataclass(frozen=True)
class Contexto:
    marcadores: Mapping[str, Marcador]
    ufs_autorizadas: frozenset[str]
    anos_permitidos: frozenset[str]
    essenciais: frozenset[str] | None
    resultado_vazio: bool
    limite_caracteres: int


@dataclass(frozen=True)
class TextoAnalisado:
    texto: str  # NFC, sem espaços nas pontas
    usados: tuple[str, ...]  # marcadores citados, na ordem
    resto: str  # o que o redator escreveu por conta própria (marcadores trocados por espaço)
    normalizado: str  # resto em minúsculas e sem acento, para o léxico


def analisar(texto: str) -> TextoAnalisado:
    nfc = unicodedata.normalize("NFC", texto).strip()
    resto = MARCADOR.sub(" ", nfc)
    return TextoAnalisado(nfc, tuple(dict.fromkeys(MARCADOR.findall(nfc))), resto, normalizar(resto))


# ------------------------------------------------------------------ regras
Regra = Callable[[TextoAnalisado, Contexto], str | None]


def _texto_vazio(t: TextoAnalisado, _c: Contexto) -> str | None:
    return "texto_vazio" if not t.texto else None


def _texto_longo(t: TextoAnalisado, c: Contexto) -> str | None:
    return "texto_longo" if len(t.texto) > c.limite_caracteres else None


def _caractere_nao_permitido(t: TextoAnalisado, _c: Contexto) -> str | None:
    for ch in t.texto:
        if ch in _PERMITIDOS:
            continue
        categoria = unicodedata.category(ch)
        if categoria in _CATEGORIAS_PROIBIDAS:
            return "caractere_nao_permitido"
        # Letra só do alfabeto latino: homóglifo (cirílico, grego) esconderia palavra proibida.
        if categoria.startswith("L") and not unicodedata.name(ch, "").startswith("LATIN"):
            return "caractere_nao_permitido"
    return None


def _marcador_desconhecido(t: TextoAnalisado, c: Contexto) -> str | None:
    return "marcador_desconhecido" if any(m not in c.marcadores for m in t.usados) else None


def _marcador_malformado(t: TextoAnalisado, _c: Contexto) -> str | None:
    return "marcador_malformado" if "{" in t.resto or "}" in t.resto else None


def _numero_fora_do_resultado(t: TextoAnalisado, c: Contexto) -> str | None:
    if any(n not in c.anos_permitidos for n in _DIGITOS.findall(t.resto)):
        return "numero_fora_do_resultado"
    # Algarismos que não são dígitos decimais: ², ½, Ⅻ, ①.
    if any(unicodedata.category(ch) in ("No", "Nl") for ch in t.resto):
        return "numero_fora_do_resultado"
    if lexico.RE_NUMERO_POR_EXTENSO.search(t.normalizado) or lexico.RE_DATA_POR_EXTENSO.search(t.normalizado):
        return "numero_fora_do_resultado"
    return None


def _url(t: TextoAnalisado, _c: Contexto) -> str | None:
    return "url_fora_do_resultado" if _URL.search(t.resto) else None


def _vazamento(t: TextoAnalisado, _c: Contexto) -> str | None:
    return "vazamento" if lexico.RE_VAZAMENTO.search(t.normalizado) else None


def _acusacao(t: TextoAnalisado, _c: Contexto) -> str | None:
    return "linguagem_de_acusacao" if lexico.RE_ACUSACAO.search(t.normalizado) else None


def _uf_fora_do_escopo(t: TextoAnalisado, c: Contexto) -> str | None:
    return "uf_fora_do_escopo" if ufs_mencionadas(t.resto) - c.ufs_autorizadas else None


def _contradiz_resultado(t: TextoAnalisado, c: Contexto) -> str | None:
    if c.resultado_vazio:
        return None
    return "contradiz_resultado" if lexico.RE_NEGA_REGISTROS.search(t.normalizado) else None


def _sem_valor_do_resultado(t: TextoAnalisado, c: Contexto) -> str | None:
    if c.essenciais is None or c.resultado_vazio or not c.essenciais:
        return None
    return None if c.essenciais.intersection(t.usados) else "sem_valor_do_resultado"


REGRAS: tuple[Regra, ...] = (
    _texto_vazio,
    _texto_longo,
    _caractere_nao_permitido,
    _marcador_desconhecido,
    _marcador_malformado,
    _numero_fora_do_resultado,
    _url,
    _vazamento,
    _acusacao,
    _uf_fora_do_escopo,
    _contradiz_resultado,
    _sem_valor_do_resultado,
)


# ------------------------------------------------------------------ preenchimento
_PREFIXO_MOEDA = re.compile(r"R\$\s*(?=\{\{\s*v\d+\s*\}\})")
_SUFIXO_PERCENTUAL = re.compile(r"(\{\{\s*(v\d+)\s*\}\})\s*%")


def preencher(texto: str, marcadores: Mapping[str, Marcador]) -> str:
    """Troca cada marcador pelo valor formatado. "R$ {{v}}" e "{{v}}%" não duplicam o símbolo."""

    def sem_prefixo(m: re.Match[str]) -> str:
        seguinte = MARCADOR.match(texto, m.end())
        marcador = marcadores.get(seguinte.group(1)) if seguinte else None
        return "" if marcador and marcador.tipo == "moeda" else m.group(0)

    texto = _PREFIXO_MOEDA.sub(sem_prefixo, texto)
    texto = _SUFIXO_PERCENTUAL.sub(
        lambda m: (
            m.group(1) if getattr(marcadores.get(m.group(2)), "tipo", None) == "percentual" else m.group(0)
        ),
        texto,
    )
    return MARCADOR.sub(lambda m: marcadores[m.group(1)].texto, texto)


# ------------------------------------------------------------------ entrada
def verificar(
    texto: str,
    marcadores: Mapping[str, Marcador],
    *,
    ufs_autorizadas: Iterable[str],
    anos_permitidos: Iterable[int] = (),
    essenciais: Iterable[str] | None = None,
    resultado_vazio: bool = False,
    limite_caracteres: int = LIMITE_CARACTERES,
) -> Verificacao:
    """`essenciais=None` desliga a regra `sem_valor_do_resultado` (quem chama sem o material da intent)."""
    contexto = Contexto(
        marcadores=marcadores,
        ufs_autorizadas=frozenset(ufs_autorizadas),
        anos_permitidos=frozenset(str(a) for a in anos_permitidos),
        essenciais=None if essenciais is None else frozenset(essenciais),
        resultado_vazio=resultado_vazio,
        limite_caracteres=limite_caracteres,
    )
    analisado = analisar(texto)
    motivos = tuple(m for regra in REGRAS if (m := regra(analisado, contexto)))
    if motivos:
        return Verificacao(False, "", motivos, analisado.usados)
    return Verificacao(True, preencher(analisado.texto, marcadores).strip(), (), analisado.usados)
