from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.db import fechar_pool
from app.core.health import db_disponivel

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    fechar_pool()


app = FastAPI(title="Lastro API", version="0.1.0", lifespan=lifespan)
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
    db = "ok" if db_disponivel() else "indisponivel"
    return Saude(status="ok" if db == "ok" else "degradado", db=db, llm=settings.llm_provider)
