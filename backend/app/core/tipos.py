"""Tipos de saída comuns da API (AGENTS.md §7: dinheiro como string decimal, nunca float)."""

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

CENTAVOS = Decimal("0.01")


def dinheiro_str(valor: Decimal) -> str:
    return format(valor.quantize(CENTAVOS), "f")


# Serializa como "1234.50" no JSON; no Python continua Decimal.
Dinheiro = Annotated[Decimal, PlainSerializer(dinheiro_str, return_type=str, when_used="json")]
