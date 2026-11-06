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
| `pe_portal` | só `exemplo_manual` | **Falta a amostra real** (abaixo) |

## pe_portal (TCE-PE): falta rodar em rede brasileira

A API do TCE-PE só responde a IP brasileiro, então **agente de nuvem não gera esta fixture**. Quem tem rede
brasileira roda:

```
python -m lastro_pipeline.cli ingest pe_portal --amostra 200
pytest -m rede tests/test_pe_portal.py
```

e comita `data/fixtures/pe_portal/amostra/`. Até lá vale o `exemplo_manual/`, escrito contra o formato
**hipotético** de `docs/catalogo-fontes.md`. Se o teste de rede falhar, ajuste `ENVELOPES`/`CONJUNTOS` em
`connectors/pe_portal.py` e as tuplas `CAMPOS_*` em `normalize/pe_portal.py`, e atualize o `exemplo_manual/`.
