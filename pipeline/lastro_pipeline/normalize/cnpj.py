"""Documento de pessoa (CNPJ/CPF): limpeza, classificação e dígitos verificadores."""

import re
from typing import Literal

TipoDocumento = Literal["cnpj", "cpf", "invalido"]

_PESOS_CNPJ_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_CNPJ_2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def somente_digitos(valor: object) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _dv(digitos: str, pesos: tuple[int, ...]) -> str:
    resto = sum(int(d) * p for d, p in zip(digitos, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def cnpj_valido(cnpj: str) -> bool:
    if not re.fullmatch(r"[0-9]{14}", cnpj) or len(set(cnpj)) == 1:
        return False
    return cnpj[12] == _dv(cnpj[:12], _PESOS_CNPJ_1) and cnpj[13] == _dv(cnpj[:13], _PESOS_CNPJ_2)


def classificar(valor: object) -> tuple[TipoDocumento, str]:
    """Devolve o tipo do documento e os dígitos. CPF nunca é validado nem guardado: só reconhecido para descarte.

    Fontes às vezes perdem zeros à esquerda (CNPJ lido como número), por isso 12 e 13 dígitos são completados.
    """
    digitos = somente_digitos(valor)
    if len(digitos) == 11 or "*" in str(valor or ""):
        return "cpf", ""
    if 12 <= len(digitos) <= 14:
        digitos = digitos.zfill(14)
        return ("cnpj", digitos) if cnpj_valido(digitos) else ("invalido", "")
    return "invalido", ""


def com_dv(base12: str) -> str:
    """Completa os 12 primeiros dígitos com os dois verificadores. Usado para gerar dados sintéticos de teste."""
    d1 = _dv(base12, _PESOS_CNPJ_1)
    return base12 + d1 + _dv(base12 + d1, _PESOS_CNPJ_2)
