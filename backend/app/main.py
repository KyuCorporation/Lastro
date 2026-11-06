from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.health import db_disponivel

settings = get_settings()

app = FastAPI(title="Lastro API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Saude(BaseModel):
    status: str
    db: str
    llm: str


@app.get("/health", response_model=Saude)
def health() -> Saude:
    db = "ok" if db_disponivel(settings.database_url) else "indisponivel"
    return Saude(status="ok" if db == "ok" else "degradado", db=db, llm=settings.llm_provider)
