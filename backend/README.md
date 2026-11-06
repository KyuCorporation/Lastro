# backend/ — API

FastAPI conectada como `lastro_app` (sem BYPASSRLS). Toda rota autenticada usa a sessão de `core/db.py`, que abre transação e aplica `set_config('app.*', …, true)`.

```
app/
  main.py            # cria o app, inclui routers, CORS, handler de erro padrão (contracts/api.md)
  core/              # config.py, db.py (sessão com contexto), security.py (JWT, bcrypt), errors.py,
                     # relogio.py (hoje em PE, trocável nos testes), tipos.py (Dinheiro como string decimal)
  modules/
    auth/            # login e /me
    policy/          # contexto de acesso e permissão por perfil (SPEC §6.2)
    catalogo/        # SQL das intents (SPEC §7) + executor
    consulta/        # orquestra: planejador → validação → executor → redator → verificador → recibo → auditoria
    recibos/         # hash canônico e verificação
    auditoria/       # gravação e verificação da cadeia
    carteiras/       # POST/GET /carteiras e GET /carteiras/{id}/fila; prioridade.py (SPEC §9)
    fornecedores/    # GET /fornecedores/{cnpj}/dossie (404 se nada visível no escopo)
    sinais/          # leitura de sinais (cálculo fica na pipeline)
    alertas/         # alertas por evento (opcional)
    metricas/        # lê eval/reports
  llm/               # interface de provedor, gemini, mock, planejador, redator, verificador, prompts/
  tests/             # test_acesso.py (matriz do SPEC §6.4) e testes por módulo
```

Padrão por módulo: `router.py`, `service.py`, `queries.py`, `schemas.py`, `tests/`.

## Fila da carteira

Prioridade = soma dos pesos dos sinais visíveis (forte 10, atenção 3, info 1) × `max(1, log10(1 + valor exposto))`,
sendo o valor exposto o valor dos contratos vigentes nas UFs do usuário. O piso 1 é o único ajuste à fórmula do
SPEC §9: sem ele, um sancionado sem contrato vigente teria prioridade 0. A partir de R$ 9,00 de exposição a
fórmula é a do SPEC. Detalhes em `modules/carteiras/prioridade.py`.
