"""Senha (bcrypt) e token (JWT HS256). O token carrega o contexto de acesso assinado pelo servidor."""

from datetime import UTC, datetime, timedelta
from typing import get_args
from uuid import UUID

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.contexto import ContextoAcesso, Perfil

ALGORITMO = "HS256"
_PERFIS = set(get_args(Perfil))

# Hash fixo para comparar quando o e-mail não existe: o tempo de resposta não revela se o usuário existe.
# Mesmo custo do gen_salt('bf') usado nos seeds.
_HASH_FICTICIO = bcrypt.hashpw(b"senha-ficticia", bcrypt.gensalt(rounds=6))


class TokenInvalido(Exception):
    pass


def verificar_senha(senha: str, senha_hash: str | None) -> bool:
    alvo = senha_hash.encode() if senha_hash else _HASH_FICTICIO
    try:
        ok = bcrypt.checkpw(senha.encode(), alvo)
    except ValueError:
        return False
    return ok and senha_hash is not None


def criar_token(ctx: ContextoAcesso, agora: datetime | None = None) -> str:
    s = get_settings()
    agora = agora or datetime.now(UTC)
    claims = {
        "sub": str(ctx.usuario_id),
        "tid": str(ctx.tenant_id),
        "perfil": ctx.perfil,
        "ufs": list(ctx.ufs),
        "iat": agora,
        "exp": agora + timedelta(minutes=s.jwt_exp_minutes),
    }
    return jwt.encode(claims, s.jwt_secret, algorithm=ALGORITMO)


def ler_token(token: str) -> ContextoAcesso:
    try:
        c = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[ALGORITMO],
            options={"require": ["sub", "tid", "perfil", "ufs", "exp"]},
        )
        if c["perfil"] not in _PERFIS or not isinstance(c["ufs"], list):
            raise TokenInvalido
        ufs = tuple(str(uf) for uf in c["ufs"])
        return ContextoAcesso(UUID(c["tid"]), UUID(c["sub"]), c["perfil"], ufs)
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise TokenInvalido from exc
