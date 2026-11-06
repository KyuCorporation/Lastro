"""Sessão com contexto de acesso (core/db.py). Requer o banco do Compose com os seeds de demo (make seed)."""

from app.core.db import sessao


def contar_contratos(conn) -> int:
    return conn.execute("select count(*) from contratos").fetchone()[0]


def test_sem_contexto_contratos_retorna_zero():
    with sessao(None) as conn:
        assert contar_contratos(conn) == 0


def test_com_contexto_ve_so_as_ufs_do_escopo(ctx_ana, ctx_bia):
    with sessao(ctx_ana) as conn:
        assert contar_contratos(conn) >= 1  # contrato sintético de PE do seed 020
        assert conn.execute("select count(*) from contratos where uf <> 'PE'").fetchone()[0] == 0
    with sessao(ctx_bia) as conn:
        assert conn.execute("select count(*) from contratos where uf = 'PE'").fetchone()[0] == 0


def test_contexto_nao_vaza_para_a_proxima_transacao(ctx_ana):
    with sessao(ctx_ana):
        pass
    with sessao(None) as conn:
        assert conn.execute("select current_setting('app.tenant_id', true)").fetchone()[0] in ("", None)
        assert contar_contratos(conn) == 0


def test_statement_timeout_local(ctx_ana):
    with sessao(ctx_ana) as conn:
        assert conn.execute("show statement_timeout").fetchone()[0] == "5s"
    with sessao(ctx_ana, timeout_ms=1200) as conn:
        assert conn.execute("show statement_timeout").fetchone()[0] == "1200ms"
