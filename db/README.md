# db/ — contrato do modelo de dados

- `migrations/` roda no init do container (ordem alfabética): papéis, schema, RLS, views, login e fontes.
  **Nunca edite uma migration aplicada.** Mudança aprovada vira arquivo novo (`006_...sql`; a 005 já existe).
- `seeds/` roda com `make seed`: usuários de demo e fornecedor sintético com injeção (cena do ataque).

Testado em 06/11 às 03h num Postgres 16: migrations e seeds aplicam limpas; RLS conferida para os casos 1, 3, 4, 7 e 8 do SPEC §6.4, auditoria encadeada, bloqueio de gestor criando carteira e isolamento de carteiras entre tenants.
Detalhes do contexto de acesso: SPEC §6 e ADR-001.
