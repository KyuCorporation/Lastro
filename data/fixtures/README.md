# data/fixtures/ — amostras versionadas (até 200 linhas por fonte)

Cada conector grava aqui uma amostra real e pequena da sua fonte. Os testes e a demo offline usam só isto.
Não coloque dado pessoal: favorecido pessoa física é descartado na normalização.

## pe_portal (TCE-PE)

A API do TCE-PE só responde a IP brasileiro, então **agente de nuvem não gera esta fixture**. Quem tem rede brasileira roda:

```
python -m lastro_pipeline.cli ingest pe_portal --amostra 200
```

e comita `data/fixtures/pe_portal/`. Enquanto isso não acontece, o agente pode criar uma fixture mínima à mão em `data/fixtures/pe_portal/exemplo_manual/`, que deve ser substituída pela real assim que existir. A amostra deve incluir: contratos estaduais e municipais, ao menos um empenho com liquidação e um credor pessoa física (para testar o descarte).
