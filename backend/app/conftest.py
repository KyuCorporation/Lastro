import os
from uuid import UUID

import pytest

from app.core.contexto import ContextoAcesso

# A configuração é lida na importação de app.main; garante valores padrão fora do container.
os.environ.setdefault("DATABASE_URL", "postgresql://lastro_app:x@localhost:5432/lastro")
os.environ.setdefault("JWT_SECRET", "segredo-so-para-teste-local-com-tamanho-suficiente")

# Usuários de db/seeds/010_demo_usuarios.sql
TENANT_ALFA = UUID("00000000-0000-0000-0000-00000000a1fa")
TENANT_BETA = UUID("00000000-0000-0000-0000-00000000be7a")


@pytest.fixture
def ctx_ana() -> ContextoAcesso:
    return ContextoAcesso(TENANT_ALFA, UUID("00000000-0000-0000-0000-0000000000a1"), "analista", ("PE",))


@pytest.fixture
def ctx_caio() -> ContextoAcesso:
    return ContextoAcesso(TENANT_ALFA, UUID("00000000-0000-0000-0000-0000000000a2"), "auditor", ("PE",))


@pytest.fixture
def ctx_bia() -> ContextoAcesso:
    return ContextoAcesso(TENANT_BETA, UUID("00000000-0000-0000-0000-0000000000b1"), "analista", ("AL",))
