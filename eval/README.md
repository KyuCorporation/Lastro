# eval/ — avaliação

- `gabarito/perguntas.yaml`: 100 perguntas. **O `sql_referencia` é escrito por outra pessoa ou outro agente que não o autor do catálogo.** Senão o teste vira circular.
- `ataques/ataques.yaml`: 50 ataques.
- `run_eval.py`: harness. Faz login como o usuário do caso, chama `POST /consultas`, compara intent, resultado (contra o SQL de referência executado sob o mesmo contexto), citações e comportamento. Escreve `reports/gabarito.json`, `reports/ataques.json` e um resumo em `reports/resumo.md`.
- Os números de `reports/` alimentam `GET /metricas`.

Métricas: acerto de intent, acerto de resultado, citação correta, abstenção correta, taxa de fallback; para ataques, % bloqueado e nº de vazamentos (meta: zero).
