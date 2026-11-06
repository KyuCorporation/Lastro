"""Tipos de saída comuns da API (AGENTS.md §7: dinheiro como string decimal, nunca float)."""

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, PlainSerializer

CENTAVOS = Decimal("0.01")


def dinheiro_str(valor: Decimal) -> str:
    return format(valor.quantize(CENTAVOS), "f")


# Serializa como "1234.50" no JSON; no Python continua Decimal.
Dinheiro = Annotated[Decimal, PlainSerializer(dinheiro_str, return_type=str, when_used="json")]


def _sem_nulo(texto: str) -> str:
    """O Postgres não guarda NUL em `text`: sem esta checagem a gravação falha e a API responderia 500."""
    if "\x00" in texto:
        raise ValueError("texto com caractere nulo")
    return texto


# Todo texto de entrada que pode chegar ao banco. Byte nulo vira 422 ENTRADA_INVALIDA na borda.
TextoSemNulo = Annotated[str, AfterValidator(_sem_nulo)]
