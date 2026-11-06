# Integração: subir tudo e testar de ponta a ponta

## Subir o sistema com dados

```
cp .env.example .env      # troque as senhas
make demo                 # banco limpo + seeds + ingestão offline de data/fixtures + API e web de pé
```

Web em http://localhost:5173 (seletor de usuários de demo com `DEMO_MODE=true`), API em http://localhost:8000.
Etapas ainda não implementadas (sinais, eval) avisam e não interrompem a preparação.

## Camadas de teste

| Comando | O que prova | Precisa do sistema de pé |
|---|---|---|
| `make test` | Unidade e integração por módulo: acesso (§6.4), pipeline, API (TestClient + Postgres), frontend (Vitest) | Só o banco |
| `make test-integracao` | API real por HTTP com os dados que vieram da pipeline: TCE-PE, PNCP (AL), CEIS; escopo por UF; injeção armazenada; 24 consultas simultâneas com a trilha de auditoria íntegra | Sim (`make demo`) |
| `make test-e2e` | Navegador real (Chrome da máquina, via Playwright) na interface: login, pergunta, resposta com citação e recibo, acesso negado, teclado, perfis | Sim, e Google Chrome instalado |
| `bash scripts/teste_resiliencia.sh` | API reiniciada no meio da sessão; banco fora e de volta (503 e recuperação sozinha); fonte fora na ingestão (execução `falhou`, nada apagado) | Sim |

## Defeitos encontrados e corrigidos

### Valor pago somava empenho e liquidação (T05/T08) — corrigido

Empenho e liquidação vão para `pagamentos` (SPEC §10, regra 6) e o resumo somava os dois: Garanhuns (empenho de
R$ 40.000 e duas liquidações de R$ 20.000 dele) aparecia como pago R$ 80.000. Decisão de produto (06/11/2026):
**pago = o que saiu (liquidação, pagamento); o empenhado aparece à parte**. O empenho é reconhecido pelo
`id_origem` com prefixo `emp:` (gravado pelo conector do TCE-PE). `resumo_fornecedor` e `pagamentos_periodo`
passaram para a v2 (o recibo registra a versão) e devolvem `n_empenhos` e `valor_empenhado`; o texto diz
"Foram registrados 2 pagamento(s), num total de R$ 40.000,00. Há ainda R$ 40.000,00 empenhado(s) em 1 empenho(s)…".
Fonte sem empenho (PNCP, CEIS) não muda.

### Trilha de auditoria fora de ordem com escrita simultânea — corrigido no banco e na API

O `seq` da auditoria era sorteado antes de o trigger pegar o lock do tenant: com duas transações ao mesmo tempo,
a cadeia ficava fora da ordem do `seq`, e a verificação (T16) acusaria adulteração falsa. Duas correções:
`db/migrations/006_auditoria_seq_no_trigger.sql` (aprovada em 06/11/2026) sorteia o `seq` dentro do trigger,
depois do lock; e a API pega o mesmo lock antes do insert. `test_cadeia_concorrente.py` falha sem as duas e
passa com qualquer uma delas. Banco criado antes da 006: `make reset-db` (ou ver `db/README.md`).

### LLM fora do ar travava a tela por até 40 s — corrigido

`LLM_TIMEOUT_SECONDS` era ignorado (20 s fixos), e com o provedor fora o planejador esperava o timeout e o
redator esperava outro. Agora o tempo vem do `.env` e, se o planejador já caiu nas regras por indisponibilidade,
o redator vai direto ao modelo determinístico: uma chamada só. O recibo registra `fallback` com
`provedor_indisponivel`.

### Outros corrigidos nesta integração

- Healthcheck do Postgres aprovava o servidor temporário do init (só socket): agora é por TCP, e `make reset-db`
  espera o banco de verdade (`up --wait`) em vez de `sleep 5`.
- `scripts/demo_reset.sh` estava sem permissão de execução no git e abortava em `sinais` (T17): agora roda por
  `make demo` e avisa o que falta.
- Banco fora do ar respondia 500: agora 503 `FONTE_INDISPONIVEL` (contracts/api.md).
- Negação de escopo (403 `ESCOPO_NEGADO`) aparecia na tela como erro genérico: agora no painel "Acesso negado".
- 429 do limite de consultas agora traz `Retry-After` (segundos até abrir vaga) e a mensagem diz quanto esperar.
- Porta do banco no host configurável (`DB_PORTA_HOST`, padrão 5432): quem já tem Postgres na máquina troca no `.env`.
- Período padrão do PNCP no `.env.example` encurtado para um mês (o país inteiro leva ~6 min por mês a 1 req/s).

## O que ainda depende de pessoas

- **Amostra real do TCE-PE** (R1): rodar em rede brasileira `python -m lastro_pipeline.cli ingest pe_portal --amostra 200`
  e `pytest -m rede tests/test_pe_portal.py`; o conector foi escrito contra formato hipotético.
- **Gemini real**: nenhum teste chama o provedor de verdade. Com `LLM_PROVIDER=gemini` e a chave, fazer umas 20
  perguntas e conferir no recibo quantas saem `aprovado` e quantas `fallback`, e o tempo de cada uma.
