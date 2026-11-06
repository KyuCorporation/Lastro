# AGENTS.md — como trabalhar neste repositório

Este arquivo vale para qualquer agente de código (Claude Code, Codex, Cursor) e para humanos. Leia inteiro antes da primeira alteração.

## 1. Antes de começar

1. Leia `SPEC.md` §1 e §4, e as seções que a sua alteração toca. Se o pedido citar uma tarefa por ID (`T05`…), leia a linha dela em `docs/backlog.md`.
2. Leia o `README.md` da pasta onde vai trabalhar. Ele diz o que a pasta faz.
3. Confira `contracts/` e `db/migrations/`. Eles são **contratos congelados** (seção 4).
4. Trabalhe em uma alteração por vez.

Se o pedido for ambíguo, escolha a leitura mais simples que o cumpra e siga. Não pare para perguntar o que dá para decidir sozinho.

## 2. Mapa do repositório

| Pasta | O que vive aqui |
|---|---|
| `pipeline/` | Conectores, normalização, qualidade, sinais. Papel de banco `lastro_ingest` |
| `db/` | Migrations e seeds |
| `backend/app/core`, `auth`, `policy`, `recibos`, `auditoria`, `carteiras`, `fornecedores`, `alertas`, `metricas`, `consulta` | API, contexto de acesso, recibos, auditoria |
| `backend/app/modules/catalogo`, `backend/app/llm/` | Consultas do catálogo, planejador, redator, verificador, prompts |
| `eval/` | Gabarito, ataques, harness, relatórios |
| `frontend/` | Interface |
| `docs/` | Arquitetura, ADRs, catálogo de fontes, dicionário, modelo de ameaças |
| `contracts/` | Recibo, plano de consulta, API |

## 3. Regras inegociáveis

1. **A LLM nunca acessa o banco.** Nada de tool calling com SQL, nada de SQL gerado por LLM. Só intents do catálogo (`SPEC.md` §7).
2. **A LLM nunca produz número, data, CNPJ ou URL que vá para o usuário.** Ela escreve marcadores `{{vN}}`; o código insere os valores; o verificador confere (`SPEC.md` §8.3).
3. **O escopo de acesso vem só da sessão autenticada.** Nunca de parâmetro da requisição, do plano da LLM ou do frontend. Toda consulta ao banco da API passa pela sessão com `set_config` (`backend/app/core/db.py`). Proibido usar o usuário `postgres` ou qualquer papel com `BYPASSRLS` na API.
4. **SQL sempre parametrizado.** Nunca f-string ou concatenação com valor vindo de fora.
5. **Proveniência obrigatória.** Toda linha pública gravada tem `fonte_id`, `id_origem`, `url_origem`, `coletado_em`, `hash_conteudo` e `arquivo_bruto_id`. Toda resposta cita linhas por esses campos.
6. **Só pessoa jurídica e só dado público ou sintético.** Descarte favorecido com CPF. Sócio pessoa física: só chave hash e exibição mascarada.
7. **Sinal não é acusação.** Na interface e nos textos: "sinal para investigar". Nunca "fraude", "irregular", "suspeito", "corrupção".
8. **Segredo nunca no código.** Use `backend/app/core/config.py` e `.env`. Não logue token, senha, chave ou prompt completo com dado de terceiros.
9. **A demo funciona sem LLM.** Todo caminho com LLM tem fallback (`LLM_PROVIDER=mock`, roteador por regras, modelo determinístico).

## 4. Contratos congelados

São contratos: `db/migrations/*`, `contracts/recibo.schema.json`, `contracts/plano_consulta.schema.json`, `contracts/api.md`.

- Agente **não altera** contrato sozinho. Se a alteração exigir, pare essa parte, descreva a "Mudança de contrato proposta: …" com o diff sugerido, e siga com o restante.
- Nova migration, quando aprovada por um humano, entra como arquivo novo (`006_…sql`; a 005 já é a fonte do TCE-PE). Nunca editar migration já aplicada.

## 5. Fluxo de trabalho do agente

1. Crie uma branch com nome descritivo, por exemplo `sinais-penhasco`.
2. Escreva primeiro o teste do comportamento esperado (ou complete o que já existir).
3. Implemente o mínimo para o teste passar. Sem funcionalidade extra fora do pedido.
4. Rode `make lint` e `make test` (ou o alvo específico da pasta). Tudo verde.
5. Commits pequenos, com mensagem descritiva, por exemplo `calcula sinal de penhasco por UF`.
6. Agente não faz merge na `main`.

## 6. Definição de pronto

- Comportamento coberto por teste automatizado.
- `make lint` e `make test` verdes.
- Sem segredo, sem dado real sensível, sem `print` de depuração.
- Funciona com `LLM_PROVIDER=mock`.
- `README.md` da pasta atualizado se o jeito de usar mudou.

## 7. Convenções

- **Idioma:** domínio em português, como no banco (`fornecedor`, `contrato`, `carteira`, `sinal`, `recibo`). Termos técnicos genéricos em inglês quando forem padrão (`client`, `router`, `schema`). Mensagens ao usuário e documentação em português do Brasil.
- **Python 3.12:** tipagem em tudo, Pydantic v2 para entrada e saída, `ruff` e `ruff format`, `pytest`. Acesso a banco com `psycopg` 3 e SQL explícito em arquivos `.sql` ou constantes nomeadas. Sem ORM.
- **Estrutura de módulo no backend:** `router.py` (rotas), `service.py` (regra), `queries.py` ou `sql/` (SQL), `schemas.py` (Pydantic), `tests/`.
- **TypeScript:** `strict`, componentes funcionais, TanStack Query para chamadas, tipos da API em `frontend/src/api/types.ts` espelhando `contracts/api.md`.
- **SQL:** palavras-chave em minúsculas, nomes em `snake_case`, views com `security_invoker = true`.
- **Datas** em ISO 8601 na API; dd/mm/aaaa só na interface. **Dinheiro** como string decimal na API (`"1234.56"`), nunca float.

## 8. Comandos

```
make up              # sobe db, api e web
make down
make reset-db        # recria o banco com migrations e seeds de demo
make seed            # aplica db/seeds
make ingest-pe       # pipeline: API do TCE-PE (só roda em rede brasileira, na máquina da equipe)
make ingest-pncp     # pipeline: PNCP (UFs e período em .env)
make ingest-sancoes  # pipeline: CEIS e CNEP
make sinais          # recalcula sinais
make test            # tudo
make test-db         # matriz de acesso e RLS
make test-pipeline
make test-api
make eval            # gabarito
make eval-ataques    # suíte de ataques
make lint
```

## 9. Dados

- `data/raw/` fica fora do git. `data/fixtures/` é versionado e pequeno (até 200 linhas por fonte).
- Testes usam **fixtures**, nunca rede. Conectores de rede têm um teste de contrato marcado `@pytest.mark.rede`, que não roda por padrão.
- Requisições a fontes externas: no máximo 1 por segundo, retry com backoff exponencial, cache em disco, cabeçalho `User-Agent: lastro-hackathon` (sem e-mail pessoal).
- **A API do TCE-PE só responde a IP brasileiro.** Agente rodando em nuvem não consegue chamá-la e **não deve tentar contornar** (proxy, VPN, mirror). Desenvolva e teste o conector `pe_portal` só com `data/fixtures/pe_portal/`. Se a fixture ainda não existir, escreva o conector contra o formato descrito em `docs/catalogo-fontes.md`, crie uma fixture mínima à mão marcada como `exemplo_manual` e registre que falta rodar `ingest pe_portal --amostra 200` em rede brasileira. Quem roda a ingestão real é um humano.
- Se uma fonte bloquear, **não tente contornar** firewall ou bloqueio. Registre a falha e use o download manual descrito em `docs/catalogo-fontes.md`.

## 10. Não faça

- Não adicione serviço novo ao Compose (Redis, MinIO, Keycloak, Grafana) sem decisão humana registrada.
- Não troque a stack, o framework de frontend ou o banco.
- Não crie embeddings, vetores ou reranker (fora de escopo, `SPEC.md` §3.4).
- Não escreva "melhorias" fora do pedido. Se vir um problema, comunique ao final.
- Não apague testes para fazê-los passar. Não marque teste como `skip` sem explicar.
- Não gere documentação sobre o que ainda não existe no código.

## 11. Quando travar

- Erro de rede ou fonte fora: use a fixture e registre.
- Teste de outra área quebrando: não conserte; anote e avise.
- Mais de 30 minutos sem progresso na mesma falha: pare, escreva o diagnóstico e devolva a alteração.
