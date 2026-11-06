"""Formatação dos valores que o código insere no texto (SPEC §8.3, passo 1). Só para a interface: na API e no
recibo os valores ficam crus (dinheiro como string decimal, datas em ISO 8601)."""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

TipoValor = Literal["moeda", "data", "inteiro", "percentual", "texto"]


def _milhar(inteiro: str) -> str:
    if inteiro.startswith("-"):
        return "-" + _milhar(inteiro[1:])
    grupos = []
    while len(inteiro) > 3:
        inteiro, grupo = inteiro[:-3], inteiro[-3:]
        grupos.insert(0, grupo)
    return ".".join([inteiro, *grupos])


def _decimal_br(valor: Decimal) -> str:
    q = valor.quantize(Decimal("0.01"), ROUND_HALF_UP)
    sinal = "-" if q < 0 else ""
    inteiro, centavos = f"{abs(q):.2f}".split(".")
    return f"{sinal}{_milhar(inteiro)},{centavos}"


def _data_br(valor: object) -> str:
    if isinstance(valor, str):  # ISO 8601 vindo de JSON
        try:
            valor = datetime.fromisoformat(valor)
        except ValueError:
            return valor
    d = valor.date() if isinstance(valor, datetime) else valor
    return d.strftime("%d/%m/%Y") if isinstance(d, date) else str(d)


def formatar_cnpj(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}" if len(cnpj) == 14 else cnpj


def formatar(valor: object, tipo: TipoValor) -> str:
    if valor is None:
        return "não informado"
    if tipo == "moeda":
        return f"R$ {_decimal_br(Decimal(str(valor)))}"
    if tipo == "percentual":
        return f"{_decimal_br(Decimal(str(valor)))}%"
    if tipo == "inteiro":
        return _milhar(str(int(valor)))
    if tipo == "data":
        return _data_br(valor)
    return str(valor)


def valor_cru(valor: object) -> str:
    """Valor para o recibo: decimal como string, data em ISO 8601."""
    if valor is None:
        return ""
    if isinstance(valor, date | datetime):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return format(valor, "f")
    return str(valor)
