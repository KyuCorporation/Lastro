# ADR-002 — Catálogo de consultas em vez de NL-to-SQL livre

**Status:** aceita (06/11/2026)

**Contexto:** text-to-SQL em schemas reais tem acerto baixo (Spider 2.0, ICLR 2025: cerca de 21% para os melhores modelos, contra 91% no Spider 1.0) e SQL gerado por LLM é superfície de ataque.

**Decisão:** o planejador escolhe uma intent de um catálogo fechado e preenche parâmetros tipados (`contracts/plano_consulta.schema.json`). O SQL é fixo, parametrizado e versionado. Padrões Action-Selector e Plan-Then-Execute.

**Alternativas:** NL-to-SQL com validação de AST (fica como evolução: plano JSON mais rico compilado pelo backend); RAG puro (erra totais e agregações).

**Consequências:** cobertura limitada às intents; em troca, resultados auditáveis, injeção sem efeito sobre o que é consultado e testes determinísticos.
