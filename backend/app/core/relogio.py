"""Relógio da API. "Hoje" é o dia em Pernambuco, não o do servidor (o container roda em UTC).

As rotas recebem a data pela dependência `Hoje`, que os testes trocam por uma data fixa com
`app.dependency_overrides[hoje] = lambda: date(...)`.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends

FUSO_RECIFE = timezone(timedelta(hours=-3))  # Pernambuco não tem horário de verão


def hoje_recife() -> date:
    return datetime.now(FUSO_RECIFE).date()


def hoje() -> date:
    return hoje_recife()


Hoje = Annotated[date, Depends(hoje)]
