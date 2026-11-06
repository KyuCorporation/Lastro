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

## Defeitos encontrados na integração

### Valor pago soma empenho e liquidação (T05/T08) — aberto

Empenho e liquidação vão para `pagamentos` (SPEC §10, regra 6) e o `resumo_fornecedor` soma os dois. Com as
fixtures do TCE-PE, Garanhuns tem empenho de R$ 40.000 e duas liquidações de R$ 20.000 desse empenho: o pago é
R$ 40.000, e a resposta diz R$ 80.000. Precisa de decisão de produto (somar só liquidação? separar empenhado e
pago?). O teste `test_valor_pago_nao_soma_empenho_com_liquidacao` está marcado `xfail` estrito: quando corrigirem,
ele passa e acusa, para tirar a marca.

### Trilha de auditoria fora de ordem com escrita simultânea — contornado na API

O `seq` da auditoria é sorteado antes de o trigger `auditoria_encadear` pegar o lock. Com duas transações ao mesmo
tempo, a que pegou o `seq` maior pode encadear primeiro: a cadeia continua válida, mas fora da ordem do `seq`, e a
verificação da T16 (percorrendo por `seq`) acusaria adulteração falsa. A API agora pega o mesmo lock antes do
insert (`modules/auditoria/queries.py`, `TRAVAR_CADEIA`); o teste `test_cadeia_concorrente.py` falha sem isso e
passa com isso. Quem gravar auditoria fora da API (pipeline) continua exposto: a correção definitiva é no banco.

**Mudança de contrato proposta** (AGENTS.md §4; precisa de aprovação humana; arquivo novo `006_…`): sortear o
`seq` dentro do trigger, depois do lock.

```sql
-- 006_auditoria_seq_no_trigger.sql
create or replace function auditoria_encadear() returns trigger
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  anterior char(64);
begin
  perform pg_advisory_xact_lock(hashtext(coalesce(new.tenant_id::text, 'global')));
  new.seq := nextval('auditoria_seq_seq');  -- depois do lock: ordem do seq = ordem da cadeia
  select a.hash into anterior
    from auditoria a
   where a.tenant_id is not distinct from new.tenant_id
   order by a.seq desc
   limit 1;
  new.criado_em := coalesce(new.criado_em, now());
  new.hash_anterior := coalesce(anterior, repeat('0', 64));
  new.hash := encode(digest(
      new.hash_anterior || '|' ||
      coalesce(new.tenant_id::text, '') || '|' ||
      coalesce(new.usuario_id::text, '') || '|' ||
      new.evento || '|' ||
      coalesce(new.detalhes::text, '') || '|' ||
      extract(epoch from new.criado_em)::text,
    'sha256'), 'hex');
  return new;
end $$;
```

O `nextval` do default da coluna também roda (deixa um buraco no `seq`), o que não afeta a cadeia.

### Corrigidos nesta integração

- Healthcheck do Postgres aprovava o servidor temporário do init (só socket): agora é por TCP, e `make reset-db`
  espera o banco de verdade (`up --wait`) em vez de `sleep 5`.
- `scripts/demo_reset.sh` estava sem permissão de execução no git e abortava em `sinais` (T17): agora roda por
  `make demo` e avisa o que falta.
- Banco fora do ar respondia 500: agora 503 `FONTE_INDISPONIVEL` (contracts/api.md).
- Negação de escopo (403 `ESCOPO_NEGADO`) aparecia na tela como erro genérico: agora no painel "Acesso negado".
