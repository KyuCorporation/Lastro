"""Conversões tolerantes de campos de origem (texto, data, dinheiro, chaves alternativas)."""

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

_FORMATOS_DATA = ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%d-%m-%Y")


def campo(registro: Mapping[str, Any], *chaves: str) -> Any:
    """Primeiro valor não vazio entre chaves alternativas (`"a.b"` navega em objetos aninhados)."""
    for chave in chaves:
        valor: Any = registro
        for parte in chave.split("."):
            valor = valor.get(parte) if isinstance(valor, Mapping) else None
        if valor not in (None, "", [], {}):
            return valor
    return None


def texto(valor: Any, limite: int | None = None) -> str | None:
    if valor is None:
        return None
    limpo = re.sub(r"\s+", " ", str(valor)).strip()
    if not limpo:
        return None
    return limpo[:limite] if limite else limpo


def data(valor: Any) -> date | None:
    """Aceita ISO (com ou sem hora), dd/mm/aaaa e aaaammdd. Valor ilegível vira None (contado na qualidade)."""
    if valor is None or isinstance(valor, date):
        return valor if not isinstance(valor, datetime) else valor.date()
    bruto = str(valor).strip()
    if not bruto:
        return None
    bruto = bruto.split("T")[0].split(" ")[0]
    for formato in _FORMATOS_DATA:
        try:
            return datetime.strptime(bruto, formato).date()
        except ValueError:
            continue
    return None


def dinheiro(valor: Any) -> Decimal | None:
    """Número da fonte em Decimal com 2 casas. Aceita 1234.5, '1.234,56' e '1234,56'. Nunca passa por float."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, Decimal)):
        numero = Decimal(valor)
    else:
        bruto = str(valor).strip().replace("R$", "").replace(" ", "")
        if not bruto:
            return None
        if "," in bruto:
            bruto = bruto.replace(".", "").replace(",", ".")
        try:
            numero = Decimal(bruto)
        except InvalidOperation:
            return None
    return numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def uf(valor: Any) -> str | None:
    sigla = texto(valor)
    return sigla.upper() if sigla and len(sigla) == 2 else None


def lista_de_registros(dados: Any, chaves: Sequence[str]) -> list[dict[str, Any]]:
    """Extrai a lista de registros de um envelope JSON (lista pura ou dentro de uma das chaves)."""
    if isinstance(dados, list):
        return [r for r in dados if isinstance(r, dict)]
    if isinstance(dados, Mapping):
        for chave in chaves:
            interno = campo(dados, chave)
            if isinstance(interno, list):
                return [r for r in interno if isinstance(r, dict)]
    return []
