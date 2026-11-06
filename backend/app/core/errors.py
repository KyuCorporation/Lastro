"""Formato único de erro da API (contracts/api.md): {"erro": {"codigo", "mensagem", "request_id"}}."""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("lastro.api")


class ErroApi(Exception):
    def __init__(self, status: int, codigo: str, mensagem: str, headers: dict[str, str] | None = None):
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem
        self.headers = headers


def nao_autenticado(mensagem: str = "Autenticação necessária.") -> ErroApi:
    return ErroApi(401, "NAO_AUTENTICADO", mensagem, {"WWW-Authenticate": "Bearer"})


def _request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if rid is None:
        rid = request.state.request_id = str(uuid.uuid4())
    return rid


def _resposta(
    request: Request, status: int, codigo: str, mensagem: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    rid = _request_id(request)
    corpo = {"erro": {"codigo": codigo, "mensagem": mensagem, "request_id": rid}}
    return JSONResponse(corpo, status_code=status, headers={**(headers or {}), "X-Request-ID": rid})


_CODIGO_POR_STATUS = {401: "NAO_AUTENTICADO", 403: "PERFIL_SEM_PERMISSAO", 404: "NAO_ENCONTRADO"}


def registrar_tratadores(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = _request_id(request)
        resposta = await call_next(request)
        resposta.headers["X-Request-ID"] = rid
        return resposta

    @app.exception_handler(ErroApi)
    async def erro_api(request: Request, exc: ErroApi) -> JSONResponse:
        return _resposta(request, exc.status, exc.codigo, exc.mensagem, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def entrada_invalida(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _resposta(request, 422, "ENTRADA_INVALIDA", "Entrada inválida.")

    @app.exception_handler(StarletteHTTPException)
    async def http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        padrao = "ERRO_INTERNO" if exc.status_code >= 500 else "ENTRADA_INVALIDA"
        codigo = _CODIGO_POR_STATUS.get(exc.status_code, padrao)
        return _resposta(request, exc.status_code, codigo, str(exc.detail), getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def interno(request: Request, exc: Exception) -> JSONResponse:
        log.exception("erro não tratado (request_id=%s)", _request_id(request))
        return _resposta(request, 500, "ERRO_INTERNO", "Erro interno.")
