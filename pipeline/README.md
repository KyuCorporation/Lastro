# pipeline/ — ingestão, qualidade e sinais

Conecta como `lastro_ingest`. Roda por CLI (`python -m lastro_pipeline.cli ...`), sem fila.

## Uso

```
python -m lastro_pipeline.cli ingest pe_portal            # TCE-PE (só em rede brasileira)
python -m lastro_pipeline.cli ingest pncp                 # PNCP: UFs de PNCP_UFS no período do .env
python -m lastro_pipeline.cli ingest sancoes              # CEIS + CNEP (ou: ceis, cnep)
python -m lastro_pipeline.cli ingest todas --offline      # tudo a partir de data/fixtures, sem rede
python -m lastro_pipeline.cli ingest pncp --amostra 100   # grava data/fixtures/pncp/amostra/ (não grava no banco)
python -m lastro_pipeline.cli sinais                      # recalcula os sinais (ou --hoje AAAA-MM-DD)
```

Pelo Make: `make ingest-pe`, `make ingest-pncp`, `make ingest-sancoes`, `make sinais`, `make test-pipeline`.
Rodar duas vezes não muda contagens: a segunda execução sai com `novos 0, atualizados 0`.

## Estrutura

```
lastro_pipeline/
  cli.py            # typer: ingest <fonte> [--offline] [--amostra N], sinais
  config.py         # pydantic-settings (.env)
  modelos.py        # RespostaBruta, Orgao, Fornecedor, Contrato, Pagamento, Sancao, Descarte
  http.py           # cliente comum: N req/s, retry com backoff, cache em disco do dia, User-Agent lastro-hackathon
  bronze.py         # resposta bruta em data/raw/<fonte>/<data>/ e em arquivos_brutos (sha256 único por fonte)
  db.py             # SQL explícito: execucoes_ingestao e upsert por (fonte_id, id_origem) só se hash_conteudo mudou
  runner.py         # orquestra uma execução, igual para todas as fontes
  fixtures.py       # lê e grava data/fixtures/<fonte>/<conjunto>/ com manifest.json (url_origem, coletado_em)
  connectors/       # base.py (contrato), pe_portal.py, pncp.py, sancoes.py; __init__.py registra as fontes
  normalize/        # cnpj.py, valores.py e o mapeamento campo a campo de cada fonte
  quality/          # relatorio.py: completude, duplicidade, datas fora de faixa, queda de volume > 50%
  sinais/           # regras.py (regras v1, puras) e calculo.py (lê fatos, grava sinais)
tests/              # usam data/fixtures, nunca rede (exceto @pytest.mark.rede)
```

## Como uma execução funciona (`runner.py`)

1. Abre `execucoes_ingestao` (`rodando`) e grava os filtros em `parametros.filtros`.
2. Para cada resposta bruta: bronze → `interpretar` → `normalizar` → upsert de órgão, fornecedor e fato.
3. Fecha com `ok`, ou com `parcial` se o volume lido caiu mais de 50% em relação à última execução com os
   mesmos filtros. O relatório de qualidade vai para `parametros.qualidade`. Nada é apagado.
4. Em erro, os fatos não são gravados (transação única) e a execução fica `falhou`, com a mensagem em `erro`.

Pessoa física (CPF, `tipoPessoa = PF`, `TIPO DE PESSOA = F`) é descartada e contada em `registros_descartados`.

## Sinais (`make sinais`)

Regras v1 do SPEC §9 em `sinais/regras.py`. Cada sinal tem `explicacao` em uma frase e `evidencias`
(`[{tabela, id, url_origem}]`, até 50, as de maior valor). Linguagem: "sinal para investigar", nunca acusação.

| Sinal | Regra | UF | Gravidade |
|---|---|---|---|
| `sancao_direta` | CNPJ com sanção vigente no CEIS ou CNEP (começou e não terminou; sem data final = vigente) | nula (nacional) | forte |
| `penhasco` | ≥ 50% do valor dos contratos vigentes (`vigencia_fim >= hoje`) termina em até 180 dias | por UF | atenção |
| `concentracao` | Maior órgão responde por ≥ 70% do valor recebido nos últimos 24 meses | por UF | atenção |

- **Por UF:** penhasco e concentração usam só fatos da própria UF, para a RLS de `sinais` não vazar outra UF.
- **Recebido** = pagamentos e liquidações; empenho (`id_origem` `emp:`) não conta, como no catálogo. Se a UF não
  tem nenhum pagamento do fornecedor (o PNCP só traz contratos), usa o valor dos contratos assinados na janela, e a
  explicação diz isso. Órgão desconhecido entra no total, mas nunca como "o maior órgão".
- **Recálculo idempotente:** o mesmo (fornecedor, UF, tipo) atualiza a mesma linha (o `id` não muda); sinal que
  deixou de valer é apagado (se um alerta ainda apontar para ele, fica e o CLI avisa). Tudo numa transação com
  lock, e cada recálculo grava `sinais_recalculados` na trilha global de auditoria.

## Fonte nova

1. `connectors/<fonte>.py` com uma classe que segue `connectors/base.py` (`filtros`, `coletar`, `interpretar`,
   `normalizar`, `amostra`).
2. `normalize/<fonte>.py` com o mapeamento para os modelos de `modelos.py`.
3. Uma linha em `connectors/__init__.py` e a fixture em `data/fixtures/<fonte>/`.

Bronze, upsert, qualidade, retry, cache e limite de taxa já vêm prontos.

## Testes

`make test-pipeline` roda tudo no Compose. Os testes de banco (`tests/test_ingestao.py`) usam o Postgres real como
`lastro_ingest` dentro de uma transação desfeita no fim; sem `DATABASE_URL` eles são pulados com aviso.
Testes `@pytest.mark.rede` batem na fonte real e só rodam com `pytest -m rede` (o do TCE-PE, só em rede brasileira).
