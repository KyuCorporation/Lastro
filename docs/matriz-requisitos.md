# Matriz de requisitos → implementação → teste

Linhas do SPEC §3. A coluna Status diz o que o código faz hoje:
- **Pronto:** implementado e coberto por teste automatizado.
- **Parcial:** implementado só em parte; a observação diz o que falta.
- **Não iniciado:** nada no código ainda.

## Requisitos mínimos

| Requisito | Implementação | Teste | Status |
|---|---|---|---|
| **R1** Captura de um portal estadual | `pipeline/lastro_pipeline/connectors/pe_portal.py` (API do TCE-PE), `runner.py`, `bronze.py` | `pipeline/tests/test_pe_portal.py`, `test_ingestao.py` | Parcial: o conector está pronto e testado contra a fixture `exemplo_manual`. A API do TCE-PE só responde a IP brasileiro, e a amostra real (`ingest pe_portal --amostra 200`) ainda precisa ser coletada por alguém da equipe. Na base atual, os contratos de PE vêm do PNCP |
| **R2** Normalização e catalogação | `pipeline/lastro_pipeline/normalize/`, `quality/relatorio.py`; `docs/catalogo-fontes.md`, `docs/dicionario-dados.md`; tela 05 Fontes | `pipeline/tests/test_normalize.py`, `test_ingestao.py` (proveniência em toda linha, idempotência, PF descartada, queda de volume) | Pronto |
| **R3** Acesso por estado e perfil | `db/migrations/002_rls.sql`, `backend/app/core/db.py`, `modules/policy/` | `backend/app/tests/test_acesso.py` (matriz do SPEC §6.4), `modules/policy/tests/test_permissoes.py` | Pronto |
| **R4** LLM restrita aos dados autorizados | `modules/consulta/guardas.py`, `llm/planejador.py`, `modules/catalogo/executor.py`, `llm/redator.py`, `llm/verificador.py` | `modules/consulta/tests/test_consulta_api.py`, `llm/tests/test_verificador*.py`, `eval/ataques` (58 casos) | Pronto |
| **R5** Registro de consultas e fontes | `modules/consulta/service.py` (consulta + recibo + auditoria numa transação), `modules/recibos/`, `modules/auditoria/` | `modules/recibos/tests/`, `modules/auditoria/tests/`, `test_consulta_api.py::test_falha_na_gravacao_nao_deixa_consulta_sem_recibo` | Pronto |

## Diferenciais

| Diferencial | Implementação | Teste | Status |
|---|---|---|---|
| **D1** RAG com citação | Catálogo SQL (`modules/catalogo/sql/`), `busca_objeto` com full-text em português; citações montadas pelo backend (`modules/consulta/citacoes.py`) | `modules/catalogo/tests/`, `eval/gabarito` (citação correta) | Pronto |
| **D2** Multi-tenant | RLS por tenant em carteiras, consultas, recibos, alertas e auditoria | `test_acesso.py`, ataques `outro_tenant` e `idor` | Pronto |
| **D3** Proteção contra ataques de prompt | Guardas por código, Action-Selector, redator com marcadores, verificador; fornecedor envenenado em `db/seeds/020_demo_ataque.sql` | `eval/ataques/ataques.yaml` (58 casos em 11 categorias), `llm/tests/test_verificador_adversarial.py` | Pronto |

## Inovações

| Inovação | Implementação | Teste | Status |
|---|---|---|---|
| **I1** Recibo verificável | `modules/recibos/` (`canonico.py`, `montagem.py`), `GET /recibos/{id}/verificar`; selo na tela 02 | `modules/recibos/tests/test_verificar.py`, `test_recibo_puro.py`, `frontend/src/testes/telas_n2.test.tsx` | Pronto |
| **I2** Números nunca vêm da LLM | `llm/marcadores.py`, `llm/redator.py`, `llm/verificador.py` | `llm/tests/test_redator*.py`, `test_verificador*.py` | Pronto |
| **I3** Carteira com fila de risco | `modules/carteiras/` (`prioridade.py`), `pipeline/lastro_pipeline/sinais/`; tela 06 | `modules/carteiras/tests/`, `pipeline/tests/test_sinais_*.py`, `telas_n2.test.tsx` | Pronto (sanção direta, penhasco e concentração) |
| **I4** Auditoria encadeada | Trigger em `006_auditoria_seq_no_trigger.sql`, `GET /auditoria/verificar`; selo na tela 04 | `modules/auditoria/tests/test_auditoria_api.py`, `test_cadeia_concorrente.py` | Pronto |
| **I5** Contexto por carteira e finalidade | `carteiras.finalidade`; `POST /consultas` aceita `carteira_id` e o recibo registra a carteira | `test_consulta_api.py::test_carteira_inexistente_ou_de_outro_tenant_e_404` | Parcial: a carteira entra no contexto e no recibo, mas a finalidade ainda não muda a resposta, e a intent `fila_carteira` não tem SQL |
| **I6** Contágio por sócio | Coluna `sinais.tipo = 'contagio'` e tabela `socios` no schema; intent `socios_sancionados` no contrato | — | Não iniciado: sem conector de quadro societário, sem regra de contágio e sem SQL da intent |
| **I7** Alertas por evento | Tabela `alertas`, `GET /alertas` | `modules/alertas/tests/test_alertas.py` (leitura e RLS) | Parcial: a leitura existe; nenhum processo cria alertas quando surge sanção ou sinal |
| **I8** Reuso entre clientes | Fatos públicos sem `tenant_id`, filtrados só por UF; dados privados sempre por tenant | `test_acesso.py` | Pronto |

## Requisitos transversais (SPEC §14)

| Item | Onde | Teste |
|---|---|---|
| Gabarito de 100 perguntas, intent ≥ 90% | `eval/gabarito/perguntas.yaml`, `eval/run_eval.py` | `make eval` (tela 08). Só 1 pergunta tem `sql_referencia` independente |
| ≥ 95% dos ataques bloqueados, zero vazamento | `eval/ataques/ataques.yaml` | `make eval-ataques` (tela 08) |
| LLM fora do ar | `modules/consulta/service.py`, `llm/planejador.py` | `test_consulta_api.py` (seção "LLM fora do ar"), `llm/tests/test_planejador.py` |
| Fonte fora do ar | `pipeline/lastro_pipeline/runner.py`, `http.py` | `pipeline/tests/test_resiliencia.py`, `test_http.py` |
| Reinício no meio da consulta | `backend/app/core/db.py` (verificação de conexão no pool) | `modules/consulta/tests/test_resiliencia.py` |
| Interface: acessibilidade e linguagem | `frontend/src/` | `frontend/src/testes/*.test.tsx` (rótulos, texto em vez de só cor, sem palavras de acusação) |
