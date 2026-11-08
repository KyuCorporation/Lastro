# ADR-003 — Números inseridos por código e recibo verificável

**Status:** aceita (06/11/2026)

**Contexto:** a dor é que "resposta de IA sem fonte não serve para compliance". LLMs erram e inventam números, e texto vindo das fontes pode conter injeção.

**Decisão:** o redator só escreve marcadores (`{{v1}}`); o código insere os valores do resultado; um verificador reprova qualquer número, CNPJ ou URL fora do resultado e cai num modelo determinístico. Cada resposta gera um recibo (`contracts/recibo.schema.json`) com plano, parâmetros, linhas, fontes e versões, cujo hash é verificável por endpoint. A auditoria é encadeada por hash.

**Alternativas:** citação gerada pela LLM (pode inventar fonte); só log textual (não detecta adulteração).

**Consequências:** respostas um pouco mais engessadas; em troca, nenhum número sem lastro e prova de integridade para auditoria.

**No código (08/11/2026):**
- Modelos determinísticos por intent em `backend/app/llm/marcadores.py`; redator em `llm/redator.py`; verificador em `llm/verificador.py`.
- Recibo montado em `modules/recibos/montagem.py`, com JSON canônico em `canonico.py`. O selo aparece na tela 02 a partir de `GET /recibos/{id}/verificar`.
- Auditoria encadeada pelo trigger de `db/migrations/006_auditoria_seq_no_trigger.sql`, verificada em `GET /auditoria/verificar`.
- Provas: `llm/tests/test_verificador*.py`, `modules/recibos/tests/test_verificar.py`, `modules/auditoria/tests/test_cadeia_concorrente.py`.
