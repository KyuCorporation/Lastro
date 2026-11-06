# Lastro — radar de risco de fornecedores, com recibo

Hack Garanhuns Tech 2026 · Desafio 1 · Equipe KYU.

Uma consultoria de gestão de terceiros sobe a carteira de fornecedores de um cliente. O Lastro cruza dados públicos (dados abertos do TCE-PE, PNCP, CEIS/CNEP), devolve uma fila priorizada por sinais de risco e responde perguntas em linguagem natural com um recibo verificável. O acesso por estado, perfil e contexto é aplicado pelo próprio banco (RLS).

- Produto e arquitetura: [`SPEC.md`](SPEC.md) · Tarefas: [`docs/backlog.md`](docs/backlog.md)
- Regras para agentes e humanos: [`AGENTS.md`](AGENTS.md)
- Contratos: [`contracts/`](contracts/) · Arquitetura, ADRs e fontes: [`docs/`](docs/)

> **Rascunho (T14).** O passo a passo abaixo segue o que existe no código hoje. Falta validar em clone limpo, por uma pessoa de fora, com o sistema completo rodando. Itens marcados *(pendente)* dependem de tarefas ainda abertas.

## Rodar do zero

### 1. Pré-requisitos

- Docker com Compose v2 (`docker compose version`).
- `make`. No Windows, use o Git Bash e instale o `make` (por exemplo, `choco install make`), ou rode os comandos `docker compose` equivalentes que estão no [`Makefile`](Makefile).
- Portas livres: `5432` (Postgres), `8000` (API) e `5173` (interface).

### 2. Configuração

```bash
git clone https://github.com/KyuCorporation/Sui-a-Pernambucana.git
cd Sui-a-Pernambucana
cp .env.example .env
```

No `.env`, troque as senhas (`POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `INGEST_DB_PASSWORD`) e o `JWT_SECRET`. O resto já funciona como está:

- `LLM_PROVIDER=mock` roda sem chave e sem rede: o planejador usa regras e a resposta usa o texto pronto de cada consulta. Para usar o Gemini, `LLM_PROVIDER=gemini` e `GEMINI_API_KEY`.
- `DEMO_MODE=true` mostra o seletor rápido dos usuários de demonstração na tela de login.
- `CONSULTAS_SIMULADAS=false` deixa a tela de consulta chamar a API de verdade.

As senhas do banco são lidas **só na criação do volume**. Se mudar depois, rode `make reset-db`.

### 3. Subir

```bash
make up      # db (aplica db/migrations no primeiro start), api e web
make seed    # tenants, usuários de demonstração e o fornecedor sintético da cena do ataque
```

- Interface: http://localhost:5173
- API e documentação interativa: http://localhost:8000/docs · saúde: http://localhost:8000/health (`{"status":"ok","db":"ok","llm":"mock"}`)

### 4. Carregar dados

Sem rede, a partir das amostras versionadas em [`data/fixtures/`](data/fixtures/):

```bash
docker compose build pipeline   # a pipeline fica num profile à parte: o make up não a constrói
docker compose run --rm pipeline python -m lastro_pipeline.cli ingest todas --offline
```

Saída esperada (uma linha por fonte): `pe_portal: ok | lidos 7, novos 5, ...`, `pncp: ok | lidos 75, novos 74, ...`, `ceis: ok | lidos 102, novos 101, ...`, `cnep: ok | lidos 100, novos 100, ...`. Os descartados são pessoas físicas.

Com rede, das fontes reais (1 requisição por segundo, cache em disco):

```bash
make ingest-pncp       # contratos das UFs de PNCP_UFS (AL) no período do .env; encurte o período para a demo
make ingest-sancoes    # CEIS e CNEP (arquivo do dia)
make ingest-pe         # TCE-PE: só responde a IP brasileiro
```

Rodar a mesma ingestão de novo não duplica nada. Se uma fonte bloquear, siga o download manual em [`docs/catalogo-fontes.md`](docs/catalogo-fontes.md).

Sinais de risco (`make sinais`): *(pendente, T17)*.

### 5. Entrar

Usuários de demonstração (senha `demo123`, **só desenvolvimento**):

| E-mail | Cliente (tenant) | Perfil | UFs |
|---|---|---|---|
| ana@alfa.demo | Cliente Alfa | analista | PE |
| caio@alfa.demo | Cliente Alfa | auditor | PE |
| gil@alfa.demo | Cliente Alfa | gestor | PE |
| admin@alfa.demo | Cliente Alfa | admin | PE, AL |
| bia@beta.demo | Cliente Beta | analista | AL |

## O que já funciona

| Parte | Estado |
|---|---|
| Banco com RLS, migrations e seeds | pronto |
| Login, `/me`, permissão por perfil e auditoria das negações | pronto |
| Ingestão PNCP, CEIS, CNEP e TCE-PE (`pe_portal` ainda sem amostra real) | pronto |
| Planejador, catálogo das consultas N1, redator e verificador | pronto como biblioteca |
| Telas de login e consulta | pronto |
| `POST /consultas` de ponta a ponta, com recibo | *(pendente, T11)*: hoje responde 501 |
| Sinais, carteira, fila, dossiê, recibo verificável, auditoria encadeada na tela | *(pendente)* |

## Testes e avaliação

```bash
make test           # matriz de acesso, pipeline, API e interface (aplica os seeds antes)
make test-db        # só a matriz de acesso (RLS)
make lint
```

`make eval` e `make eval-ataques`: *(pendente, T20 e T21)*.

## Problemas comuns

- **Postgres sai com código 127 no primeiro start (Windows).** O script `db/migrations/000_roles.sh` foi baixado com CRLF. O `.gitattributes` força LF; se o clone for anterior a ele, apague `db/migrations/000_roles.sh`, rode `git checkout -- db/migrations/000_roles.sh` e depois `docker compose down -v && make up`.
- **`psql: ... C:/Program Files/Git/seeds/...` no Git Bash.** O Git Bash converte caminhos. Rode com `MSYS_NO_PATHCONV=1 make seed`.
- **A pipeline diz "ainda não implementado" para algo que já existe.** A imagem está velha: `docker compose build pipeline`.
- **Login falha depois de trocar senha no `.env`.** As senhas do banco só valem na criação do volume: `make reset-db`.
- **`make ingest-pe` falha.** A API do TCE-PE só responde a IP brasileiro. Use `ingest todas --offline` ou o download manual.

## Premissas, limitações e próximos passos

Ver [`docs/premissas-limitacoes.md`](docs/premissas-limitacoes.md).
