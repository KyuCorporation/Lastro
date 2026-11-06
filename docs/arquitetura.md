# Arquitetura

> Completar a partir do código real.

## Como está (MVP)
Ver SPEC §4: diagrama de camadas, fluxo da consulta e stack. ADRs em `docs/adr/`.

## Para produção
- **Identidade:** OIDC (Keycloak ou o IdP do cliente), RBAC + ABAC com motor de políticas, RLS mantida como última barreira.
- **Ingestão:** conectores para os 27 portais estaduais e municipais; fila (Celery ou RQ) com retry e dead letter; object storage para arquivos brutos; agendamento incremental; contratos de fonte testados diariamente.
- **Dados:** camadas bronze, prata e ouro; versionamento de registros e detecção de mudança de schema; catálogo semântico.
- **IA:** plano JSON compilado pelo backend com validação de AST para perguntas fora do catálogo; busca híbrida (full-text + vetorial) para documentos de licitação; reranker; avaliação contínua com o gabarito.
- **Operação:** OpenTelemetry, Prometheus e Grafana; custo por consulta; SLOs (P95 < 10 s com LLM); backups com teste de restauração; RPO e RTO definidos.
- **Segurança:** OWASP ASVS 5.0 e OWASP Top 10 para LLM como checklists; pentest; rotação de segredos.
- **Escala do negócio:** dado público coletado uma vez e reaproveitado por todos os clientes (reuso), carteiras ilimitadas por tenant, API para agentes de terceiros.
