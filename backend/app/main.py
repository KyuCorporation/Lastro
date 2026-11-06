from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.db import fechar_pool
from app.core.errors import registrar_tratadores
from app.core.health import db_disponivel
from app.modules.alertas.router import router as alertas_router
from app.modules.auditoria.router import router as auditoria_router
from app.modules.auth.router import router as auth_router
from app.modules.carteiras.router import router as carteiras_router
from app.modules.consulta.router import router as consulta_router
from app.modules.fontes.router import router as fontes_router
from app.modules.fornecedores.router import router as fornecedores_router
from app.modules.metricas.router import router as metricas_router
from app.modules.recibos.router import router as recibos_router

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
registrar_tratadores(app)
app.include_router(auth_router)
app.include_router(consulta_router)
app.include_router(recibos_router)
app.include_router(fontes_router)
app.include_router(carteiras_router)
app.include_router(fornecedores_router)
app.include_router(auditoria_router)
app.include_router(alertas_router)
app.include_router(metricas_router)


class Saude(BaseModel):
    status: str
    db: str
    llm: str


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    """Quem abre a API no navegador cai na documentação interativa em vez de um 404."""
    return RedirectResponse("/docs")


@app.get("/health", response_model=Saude)
def health() -> Saude:
    db = "ok" if db_disponivel() else "indisponivel"
    return Saude(status="ok" if db == "ok" else "degradado", db=db, llm=settings.llm_provider)
