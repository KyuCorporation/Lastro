"""Verificador (SPEC §8.3): confere o texto do redator antes de qualquer valor chegar ao usuário.

Reprova se o redator escreveu número, CNPJ, data ou URL por conta própria (fora dos marcadores), se usou
marcador que não existe, se o texto vaza instruções, cita UF fora do escopo ou usa linguagem de acusação.
Aprovado, troca cada marcador pelo valor formatado que veio do resultado.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.llm.marcadores import Marcador
from app.llm.regras import normalizar, ufs_mencionadas

MARCADOR = re.compile(r"\{\{\s*(v\d+)\s*\}\}")
NUMERO = re.compile(r"\d+(?:[.,/-]\d+)*")
URL = re.compile(r"https?://|www\.|\b[\w-]+\.(?:com|br|org|net|gov|io)\b", re.IGNORECASE)
VAZAMENTO = re.compile(
    r"instruc(?:ao|oes) (?:do sistema|anteriores|que recebi)|\bprompt\b"
    r"|minhas regras|regras (?:acima|do sistema)"
    r"|dado_nao_confiavel|modelo de linguagem|\bsou uma ia\b"
)
ACUSACAO = re.compile(r"\bfraud|\birregular|\bsuspeit|\bcorrup")


@dataclass(frozen=True)
class Verificacao:
    aprovado: bool
    texto_final: str
    motivos: tuple[str, ...]
    usados: tuple[str, ...]


def preencher(texto: str, marcadores: dict[str, Marcador]) -> str:
    return MARCADOR.sub(lambda m: marcadores[m.group(1)].texto, texto)


def verificar(
    texto: str,
    marcadores: dict[str, Marcador],
    *,
    ufs_autorizadas: Iterable[str],
    anos_permitidos: Iterable[int] = (),
) -> Verificacao:
    motivos: list[str] = []
    usados = tuple(dict.fromkeys(MARCADOR.findall(texto)))

    if not texto.strip():
        motivos.append("texto_vazio")
    if any(mid not in marcadores for mid in usados):
        motivos.append("marcador_desconhecido")

    resto = MARCADOR.sub(" ", texto)  # o que o redator escreveu por conta própria
    if "{{" in resto or "}}" in resto:
        motivos.append("marcador_malformado")
    anos = {str(a) for a in anos_permitidos}
    if any(n not in anos for n in NUMERO.findall(resto)):
        motivos.append("numero_fora_do_resultado")
    if URL.search(resto):
        motivos.append("url_fora_do_resultado")
    normalizado = normalizar(resto)
    if VAZAMENTO.search(normalizado):
        motivos.append("vazamento")
    if ACUSACAO.search(normalizado):
        motivos.append("linguagem_de_acusacao")
    if ufs_mencionadas(resto) - set(ufs_autorizadas):
        motivos.append("uf_fora_do_escopo")

    if motivos:
        return Verificacao(False, "", tuple(motivos), usados)
    return Verificacao(True, preencher(texto, marcadores).strip(), (), usados)
