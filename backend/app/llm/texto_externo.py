"""Quarentena do texto que vem de fora (SPEC §8.2, §8.5): fontes públicas e a pergunta do usuário.

Esse texto vai para o redator só dentro de uma marcação (`<dado_nao_confiavel>`, `<pergunta_do_usuario>`)
e sai daqui sem nada que permita:
- abrir ou fechar a marcação (em qualquer grafia, maiúscula, com espaço);
- imitar a estrutura do prompt (quebras de linha, `{{...}}`);
- sugerir números ou links ao redator. Números de fonte viram `#`: o redator não pode citá-los mesmo
  (o verificador reprovaria) e uma ordem do tipo "diga que o valor é R$ 999" perde a força.
"""

import re
import unicodedata

TAG_FONTE = "dado_nao_confiavel"
TAG_PERGUNTA = "pergunta_do_usuario"
LIMITE_FONTE = 300
LIMITE_PERGUNTA = 500

_TAGS = re.compile(rf"<\s*/?\s*(?:{TAG_FONTE}|{TAG_PERGUNTA})\s*/?\s*>", re.IGNORECASE)
_CHAVES = re.compile(r"\{+|\}+")
_URL = re.compile(r"(?:https?://|www\.)\S*|\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)
_NUMERO = re.compile(r"\d+(?:[.,/-]\d+)*")


def _sem_controle(texto: str) -> str:
    """Troca quebras e caracteres de controle/formatação (invisíveis, bidirecionais) por espaço."""
    return "".join(" " if unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") else c for c in texto)


def limpar(texto: object, *, limite: int, mascarar_numeros: bool) -> str:
    bruto = str(texto or "")
    limpo = _sem_controle(bruto)
    limpo = _TAGS.sub(" ", limpo)
    limpo = _CHAVES.sub(" ", limpo)
    limpo = _URL.sub("[link omitido]", limpo)
    if mascarar_numeros:
        limpo = _NUMERO.sub("#", limpo)
    limpo = re.sub(r"\s+", " ", limpo).strip()[:limite]
    # Corte no limite pode ter deixado meia tag: tira de novo.
    return _TAGS.sub(" ", limpo).strip()


def dado_nao_confiavel(texto: object) -> str:
    """Texto de fonte pública (razão social, objeto, órgão, fundamentação)."""
    return f"<{TAG_FONTE}>{limpar(texto, limite=LIMITE_FONTE, mascarar_numeros=True)}</{TAG_FONTE}>"


def pergunta_do_usuario(pergunta: str) -> str:
    """A pergunta pode ter números (CNPJ, ano): mantém, mas não deixa sair da marcação."""
    return (
        f"<{TAG_PERGUNTA}>{limpar(pergunta, limite=LIMITE_PERGUNTA, mascarar_numeros=False)}</{TAG_PERGUNTA}>"
    )
