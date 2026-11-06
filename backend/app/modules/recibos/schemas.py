from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ReciboSaida(BaseModel):
    id: UUID
    conteudo: dict[str, Any]  # contracts/recibo.schema.json
    hash: str
    criado_em: datetime
