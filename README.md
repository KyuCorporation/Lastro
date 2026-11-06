# Lastro — radar de risco de fornecedores, com recibo

Hack Garanhuns Tech 2026 · Desafio 1 · Equipe KYU.

Uma consultoria de gestão de terceiros sobe a carteira de fornecedores de um cliente. O Lastro cruza dados públicos (dados abertos do TCE-PE, PNCP, CEIS/CNEP), devolve uma fila priorizada por sinais de risco e responde perguntas em linguagem natural com um recibo verificável. O acesso por estado, perfil e contexto é aplicado pelo próprio banco (RLS).

- Produto e arquitetura: [`SPEC.md`](SPEC.md) · Tarefas: [`docs/backlog.md`](docs/backlog.md)
- Regras para agentes e humanos: [`AGENTS.md`](AGENTS.md)
- Contratos: [`contracts/`](contracts/) · Arquitetura, ADRs e fontes: [`docs/`](docs/) · Testes de ponta a ponta: [`docs/integracao.md`](docs/integracao.md)

## Rodar do zero

### 1. Pré-requisitos

- Docker com Compose v2 (`docker compose version`).
- `make`. No Windows, use o Git Bash com `make` instalado (por exemplo, `choco install make`). Sem `make`, rode os comandos `docker compose` equivalentes que estão no [`Makefile`](Makefile).
- Portas livres: `5432` (Postgres; dá para trocar com `DB_PORTA_HOST` no `.env`), `8000` (API) e `5173` (interface).

### 2. Configuração

```bash
git clone https://github.com/KyuCorporation/Sui-a-Pernambucana.git
cd Sui-a-Pernambucana
cp .env.example .env
```

No `.env`, troque as senhas (`POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `INGEST_DB_PASSWORD`) e o `JWT_SECRET`. O resto já funciona como está:

- `LLM_PROVIDER=mock` roda sem chave e sem rede: o planejador usa regras e a resposta usa o texto pronto de cada consulta. Para usar o Gemini: `LLM_PROVIDER=gemini` e `GEMINI_API_KEY`.
- `DEMO_MODE=true` mostra o seletor rápido dos usuários de demonstração na tela de login.
- `CONSULTAS_SIMULADAS=false` deixa a tela de consulta chamar a API de verdade. Mantenha `false`.

As senhas do banco são lidas **só na criação do volume**. Se mudar depois, rode `make reset-db`.

### 3. Subir com dados (um comando)

```bash
make demo
```

O `make demo` **apaga o banco** e recria tudo:
1. aplica as migrations;
2. carrega os seeds: usuários de demonstração e o fornecedor sintético da cena do ataque;
3. carrega as amostras de [`data/fixtures/`](data/fixtures/), sem rede;
4. sobe a API e a interface.

As etapas ainda não implementadas avisam e não interrompem a preparação.

Pronto quando aparecer `Pronto para a demo`:
- Interface: http://localhost:5173. Ela leva alguns segundos para responder depois que o container sobe.
- API: http://localhost:8000/docs (documentação interativa) e http://localhost:8000/health (`{"status":"ok","db":"ok","llm":"mock"}`).

### 3b. Passo a passo (o mesmo que o `make demo` faz)

```bash
make up               # db (aplica db/migrations no primeiro start), api e web
make seed             # tenants, usuários de demonstração e fornecedor sintético
make ingest-offline   # amostras de data/fixtures, sem rede
```

Saída esperada do `ingest-offline`, uma linha por fonte. Os descartados são pessoas físicas.

```
pe_portal: ok | lidos 7, novos 5, atualizados 0, descartados 2
pncp: ok | lidos 75, novos 74, atualizados 0, descartados 1
ceis: ok | lidos 102, novos 101, atualizados 0, descartados 1
cnep: ok | lidos 100, novos 100, atualizados 0, descartados 0
```

Rodar a mesma ingestão de novo não duplica nada: a segunda execução sai com `novos 0`.

### 4. Dados reais (opcional, com rede)

```bash
make ingest-pncp       # contratos das UFs de PNCP_UFS (AL), um mês por padrão (~6 min a 1 req/s)
make ingest-sancoes    # CEIS e CNEP (arquivo do dia)
make ingest-pe         # TCE-PE: só responde a IP brasileiro
```

Se uma fonte bloquear, siga o download manual em [`docs/catalogo-fontes.md`](docs/catalogo-fontes.md). Não tente contornar o bloqueio.

### 5. Entrar e perguntar

Usuários de demonstração (senha `demo123`, **só desenvolvimento**):

| E-mail | Cliente (tenant) | Perfil | UFs |
|---|---|---|---|
| ana@alfa.demo | Cliente Alfa | analista | PE |
| caio@alfa.demo | Cliente Alfa | auditor | PE |
| gil@alfa.demo | Cliente Alfa | gestor | PE |
| admin@alfa.demo | Cliente Alfa | admin | PE, AL |
| bia@beta.demo | Cliente Beta | analista | AL |

Com os dados do `make demo`, entre como **ana** e pergunte:

- "Faça um resumo do fornecedor 99.000.001/0001-01". Responde com valor, citação e recibo.
- "Quais contratos do CNPJ 99000001000101 vencem nos próximos 6 meses?"

Para ver o banco barrar o acesso, entre como **bia** (só AL) e faça a primeira pergunta com "em Pernambuco": a resposta é **Acesso negado**. Como **gil** (gestor), a consulta é negada por perfil. As duas negações vão para a auditoria.

## O que já funciona

| Parte | Estado |
|---|---|
| Banco com RLS, migrations e seeds; matriz de acesso do SPEC §6.4 (T13) | pronto |
| Login, `/me`, permissão por perfil, limite de 30 consultas por minuto | pronto |
| Ingestão PNCP, CEIS, CNEP e TCE-PE (`pe_portal` ainda sem amostra real) | pronto |
| `POST /consultas` de ponta a ponta: planejador, catálogo N1, redator e verificador, recibo com hash e auditoria (T08–T11) | pronto |
| `GET /consultas`, `GET /recibos/{id}` e `GET /recibos/{id}/verificar` (selo íntegro ou alterado, T15) | pronto |
| Telas de login e consulta, com citações e acesso negado (T12) | pronto |
| LLM fora do ar: resposta pelo texto pronto, sem travar a tela | pronto |
| Verificação da cadeia de auditoria (`/auditoria/verificar`, T16) | *pendente* |
| Sinais `sancao_direta`, `penhasco` e `concentracao` por UF (`make sinais`, T17) | pronto |
| Carteiras, fila priorizada por sinais e dossiê do fornecedor (`/carteiras`, `/fornecedores/{cnpj}/dossie`, T18) | pronto |
| Telas de recibo, carteira, dossiê, auditoria, fontes e métricas (T22, T26) | *pendente* |
| Gabarito e ataques (`make eval`, `make eval-ataques`, T20 e T21) | *pendente* |

## Testes

| Comando | O que prova | Precisa |
|---|---|---|
| `make test` | Matriz de acesso, pipeline, API e interface (aplica os seeds antes) | só o banco de pé |
| `make test-integracao` | API real por HTTP com os dados da pipeline, escopo por UF, injeção armazenada, consultas simultâneas | `make demo` antes |
| `make test-e2e` | Navegador real na interface: login, pergunta, citação, recibo, acesso negado, teclado | `make demo` e Google Chrome |
| `bash scripts/teste_resiliencia.sh` | API reiniciada, banco fora e de volta, fonte fora na ingestão | `make demo` antes |
| `make lint` | ruff no backend e na pipeline, `tsc` na interface | — |

Detalhes e defeitos já corrigidos na integração: [`docs/integracao.md`](docs/integracao.md).

## Problemas comuns

- **Porta 5432 ocupada** (outro Postgres na máquina): no `.env`, `DB_PORTA_HOST=55432`.
- **Postgres sai com código 127 no primeiro start (Windows).** O `db/migrations/000_roles.sh` está com CRLF. O `.gitattributes` força LF; se o clone for anterior a ele, apague o arquivo, rode `git checkout -- db/migrations/000_roles.sh` e depois `make reset-db`.
- **`psql: ... C:/Program Files/Git/seeds/...` no Git Bash.** O Git Bash converte caminhos. Rode com `MSYS_NO_PATHCONV=1 make seed`.
- **Login falha depois de trocar senha no `.env`.** As senhas do banco só valem na criação do volume: `make reset-db`.
- **Banco criado antes de 06/11/2026.** Falta a migration 006 (ordem da auditoria): `make reset-db`, ou veja [`db/README.md`](db/README.md).
- **A pipeline diz "ainda não implementado" para algo que já existe.** A imagem está velha (a pipeline fica num profile à parte e o `make up` não a reconstrói): `docker compose build pipeline`.
- **`make ingest-pe` falha.** A API do TCE-PE só responde a IP brasileiro. Use `make ingest-offline` ou o download manual.
- **Pergunta com acento chega quebrada pelo `curl` no Git Bash.** O terminal não manda UTF-8. Teste pela interface ou por http://localhost:8000/docs.

## Premissas, limitações e próximos passos

Ver [`docs/premissas-limitacoes.md`](docs/premissas-limitacoes.md).
