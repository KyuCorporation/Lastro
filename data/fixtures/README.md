# data/fixtures/ — amostras versionadas (até 200 linhas por fonte)

Os testes e a demo offline (`ingest todas --offline`) usam só isto. Cada fonte tem um ou mais conjuntos,
cada um com os arquivos brutos e um `manifest.json` (URL de origem e hora da coleta de cada arquivo):

- `amostra/`: dado **real** recortado, gerado por `python -m lastro_pipeline.cli ingest <fonte> --amostra N`.
  Só pessoa jurídica e só os campos usados: CPF, subcontratado e texto livre não entram.
- `exemplo_manual/`: dado **sintético** escrito à mão para casos de borda (credor pessoa física, sanção sem data
  final). CNPJs da faixa `99.000.00x/0001-xx`, nomes marcados "(SINTÉTICO)".

| Fonte | Conjuntos | Observação |
|---|---|---|
| `pncp` | `amostra` (contratos reais de AL de out/2026 e alguns de PE), `exemplo_manual` (PF) | As linhas de PE estão lá de propósito: o teste prova que não entram sem `PNCP_PE_FALLBACK` |
| `ceis`, `cnep` | `amostra` (100 sanções reais de PJ, arquivo de 05/11/2026), `ceis/exemplo_manual` | |
| `pe_portal` | `amostra` (198 linhas reais de PJ, coletadas em 15/11/2026: contratos de 2026 do estado e de Garanhuns, empenhos e liquidações de uma UG estadual e da Prefeitura de Garanhuns), `exemplo_manual` (PF) | Em cada conjunto o empenho vem antes das liquidações dele |

## pe_portal (TCE-PE): só em rede brasileira

A API do TCE-PE só responde a IP brasileiro, então **agente de nuvem não gera esta fixture**. Para refazer a
amostra (9 requisições, cerca de 30 segundos), quem tem rede brasileira roda:

```
python -m lastro_pipeline.cli ingest pe_portal --amostra 200
pytest -m rede tests/test_pe_portal.py
```

A amostra leva só pessoa jurídica e só os campos usados (sem `HISTORICO`), e uma liquidação só entra se o empenho
dela entrou. Fora do Compose, aponte `DATA_DIR` para a pasta `data/` do repositório. O `exemplo_manual/` segue o
formato real e cobre a pessoa física como a API manda e como fica depois do saneamento
(`docs/catalogo-fontes.md`).
