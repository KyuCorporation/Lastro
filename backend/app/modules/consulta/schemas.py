from uuid import UUID

from pydantic import BaseModel, Field


class ConsultaEntrada(BaseModel):
    pergunta: str = Field(min_length=1, max_length=500)
    carteira_id: UUID | None = None
