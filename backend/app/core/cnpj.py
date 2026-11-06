"""Validação de CNPJ (14 dígitos e dígitos verificadores)."""

import re

_PESOS_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_2 = (6, *_PESOS_1)


def _digito(numeros: str, pesos: tuple[int, ...]) -> str:
    resto = sum(int(n) * p for n, p in zip(numeros, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def normalizar_cnpj(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def cnpj_valido(cnpj: str) -> bool:
    if not re.fullmatch(r"\d{14}", cnpj) or len(set(cnpj)) == 1:
        return False
    d1 = _digito(cnpj[:12], _PESOS_1)
    d2 = _digito(cnpj[:12] + d1, _PESOS_2)
    return cnpj[12:] == d1 + d2
