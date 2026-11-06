# pipeline/ — ingestão, qualidade e sinais

Conecta como `lastro_ingest`. Roda por CLI (`python -m lastro_pipeline.cli ...`), sem fila.

```
lastro_pipeline/
  cli.py            # typer: ingest <fonte>, sinais, qualidade
  config.py         # pydantic-settings (.env)
  db.py             # conexão, upsert por (fonte_id, id_origem), registro de execucoes_ingestao
  bronze.py         # salva arquivo/resposta em /data/raw/<fonte>/<data>/ e em arquivos_brutos (sha256)
  connectors/       # pe_portal.py (API do TCE-PE), pncp.py, sancoes.py, qsa.py (opcional)
  normalize/        # mapeamento campo a campo por fonte; cnpj.py (limpa e valida DV); descarta favorecido PF
  quality/          # completude, duplicidade, datas fora de faixa, queda de volume > 50% → execução 'parcial'
  sinais/           # sancao_direta.py, penhasco.py, concentracao.py, contagio.py (opcional); sempre por UF
tests/              # usam data/fixtures, nunca rede (exceto @pytest.mark.rede)
```

Regras: SPEC §5 e §10, AGENTS.md §3 e §10. Cada conector salva amostra em `data/fixtures/<fonte>/`.
Upsert: se `hash_conteudo` não mudou, não atualiza. Rodar duas vezes não muda contagens (critério de todos os conectores).
