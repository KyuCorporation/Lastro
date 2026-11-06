# Lastro — radar de risco de fornecedores, com recibo

Hack Garanhuns Tech 2026 · Desafio 1 · Equipe KYU.

Uma consultoria de gestão de terceiros sobe a carteira de fornecedores de um cliente. O Lastro cruza dados públicos (dados abertos do TCE-PE, PNCP, CEIS/CNEP), devolve uma fila priorizada por sinais de risco e responde perguntas em linguagem natural com um recibo verificável. O acesso por estado, perfil e contexto é aplicado pelo próprio banco (RLS).

- Produto e arquitetura: [`SPEC.md`](SPEC.md)
- Regras para agentes e humanos: [`AGENTS.md`](AGENTS.md)
- Contratos: [`contracts/`](contracts/) · Arquitetura e ADRs: [`docs/`](docs/)

## Rodar do zero

Pré-requisitos: Docker com Compose e `make`.

```bash
cp .env.example .env            # preencha as senhas; LLM_PROVIDER=mock funciona sem chave
make up                         # sobe db (aplica migrations), api e web
make seed                       # usuários de demo e fornecedor sintético
make ingest-pe ingest-pncp ingest-sancoes sinais
```

- API: http://localhost:8000/docs · Interface: http://localhost:5173
- Usuários de demo (senha `demo123`, só desenvolvimento): ver SPEC §6.3.

## Testes e avaliação

```bash
make test           # matriz de acesso, pipeline e API
make eval           # gabarito de perguntas
make eval-ataques   # suíte de ataques
```

## Premissas, limitações e próximos passos

Ver [`docs/premissas-limitacoes.md`](docs/premissas-limitacoes.md).
