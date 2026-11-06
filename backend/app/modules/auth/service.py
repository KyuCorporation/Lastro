from psycopg.rows import dict_row

from app.core.contexto import ContextoAcesso
from app.core.db import sessao
from app.core.errors import nao_autenticado
from app.core.security import criar_token, verificar_senha
from app.modules.auth import queries
from app.modules.auth.schemas import LoginSaida, TenantSaida, UsuarioSaida

MENSAGEM_LOGIN_INVALIDO = "E-mail ou senha inválidos."


def usuario_atual(ctx: ContextoAcesso) -> UsuarioSaida:
    with sessao(ctx) as conn:
        linha = conn.cursor(row_factory=dict_row).execute(queries.BUSCAR_USUARIO_ATUAL).fetchone()
    if linha is None:
        raise nao_autenticado("Sessão inválida.")
    return UsuarioSaida(
        id=linha["id"],
        nome=linha["nome"],
        perfil=linha["perfil"],
        tenant=TenantSaida(id=linha["tenant_id"], nome=linha["tenant_nome"]),
        ufs=list(ctx.ufs),
    )


def login(email: str, senha: str) -> LoginSaida:
    with sessao(None) as conn:
        cur = conn.cursor(row_factory=dict_row)
        linha = cur.execute(queries.BUSCAR_USUARIO_LOGIN, {"email": email}).fetchone()
    senha_ok = verificar_senha(senha, linha["senha_hash"] if linha else None)
    if linha is None or not senha_ok:
        raise nao_autenticado(MENSAGEM_LOGIN_INVALIDO)
    ctx = ContextoAcesso(linha["tenant_id"], linha["id"], linha["perfil"], tuple(linha["ufs"]))
    return LoginSaida(token=criar_token(ctx), usuario=usuario_atual(ctx))
