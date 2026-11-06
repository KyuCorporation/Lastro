from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.contexto import ContextoAcesso
from app.core.errors import nao_autenticado
from app.core.security import TokenInvalido, ler_token

_bearer = HTTPBearer(auto_error=False)


def contexto_atual(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> ContextoAcesso:
    """Único lugar de onde a API tira o contexto de acesso: o token assinado da sessão."""
    if credenciais is None:
        raise nao_autenticado()
    try:
        return ler_token(credenciais.credentials)
    except TokenInvalido:
        raise nao_autenticado("Token inválido ou expirado.") from None


Contexto = Annotated[ContextoAcesso, Depends(contexto_atual)]
