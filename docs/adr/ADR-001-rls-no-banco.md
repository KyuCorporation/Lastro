# ADR-001 — Controle de acesso aplicado pelo banco (RLS)

**Status:** aceita (06/11/2026)

**Contexto:** o desafio exige controle de acesso por estado e perfil e uma LLM restrita aos dados autorizados. Filtro só na aplicação depende de cada consulta lembrar o `where`, e um erro vaza dado.

**Decisão:** a API conecta como `lastro_app`, sem BYPASSRLS. Cada requisição abre transação e define `app.tenant_id`, `app.usuario_id`, `app.perfil` e `app.ufs` com `set_config(..., true)`. Políticas de RLS com `FORCE ROW LEVEL SECURITY` filtram fatos públicos por UF e dados do tenant por tenant e perfil. Views com `security_invoker`.

**Alternativas:** filtro na aplicação (frágil); um banco por tenant (caro e não resolve UF); Keycloak com ABAC (horas de configuração sem mudar a demonstração).

**Consequências:** isolamento demonstrável ("quem negou foi o banco"); consultas sem contexto retornam zero linhas; o cálculo de sinais precisa ser por UF para não vazar informação de outro estado.

**No código (08/11/2026):**
- Políticas e privilégios em `db/migrations/002_rls.sql`; papéis em `000_roles.sh`.
- Contexto aplicado em `backend/app/core/db.py` (`sessao()`), com `statement_timeout` de 5 s.
- Sinais calculados por UF em `pipeline/lastro_pipeline/sinais/calculo.py`.
- Provas: `backend/app/tests/test_acesso.py` (matriz do SPEC §6.4), `test_db.py` (sem contexto, zero linhas) e os ataques `outra_uf`, `outro_tenant` e `idor`.
