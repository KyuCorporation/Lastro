# backend/ — API

FastAPI conectada como `lastro_app` (sem BYPASSRLS). Toda rota autenticada usa a sessão de `core/db.py`, que abre transação e aplica `set_config('app.*', …, true)`.

```
app/
  main.py            # cria o app, inclui routers, CORS, handler de erro padrão (contracts/api.md)
  core/              # config.py, db.py (sessão com contexto), security.py (JWT, bcrypt), errors.py, logging.py
  modules/
    auth/            # login e /me
    policy/          # contexto de acesso e permissão por perfil (SPEC §6.2)
    catalogo/        # SQL das intents (SPEC §7) + executor
    consulta/        # orquestra: planejador → validação → executor → redator → verificador → recibo → auditoria
    recibos/         # hash canônico e verificação
    auditoria/       # gravação e verificação da cadeia
    carteiras/       # carteiras e fila
    fornecedores/    # dossiê
    sinais/          # leitura de sinais (cálculo fica na pipeline)
    alertas/         # alertas por evento (opcional)
    metricas/        # lê eval/reports
  llm/               # interface de provedor, gemini, mock, planejador, redator, verificador, prompts/
  tests/             # test_acesso.py (matriz do SPEC §6.4) e testes por módulo
```

Padrão por módulo: `router.py`, `service.py`, `queries.py`, `schemas.py`, `tests/`.
