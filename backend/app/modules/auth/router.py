from fastapi import APIRouter

from app.modules.auth import service
from app.modules.auth.dependencias import Contexto
from app.modules.auth.schemas import LoginEntrada, LoginSaida, UsuarioSaida

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginSaida)
def login(entrada: LoginEntrada) -> LoginSaida:
    return service.login(entrada.email, entrada.senha)


@router.get("/me", response_model=UsuarioSaida)
def me(ctx: Contexto) -> UsuarioSaida:
    return service.usuario_atual(ctx)
