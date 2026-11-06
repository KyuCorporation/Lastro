-- 006_auditoria_seq_no_trigger.sql — ordem da trilha de auditoria com escrita simultânea.
-- Aprovada em 06/11/2026 (AGENTS.md §4). Só substitui a função do trigger criada em 001_schema.sql.
--
-- Problema: o seq (bigserial) era sorteado antes de o trigger pegar o lock do tenant. Com duas transações ao mesmo
-- tempo, a que pegou o seq maior podia encadear primeiro: a cadeia continuava válida, mas fora da ordem do seq, e
-- a verificação (que percorre por seq) acusaria adulteração falsa.
-- Correção: sortear o seq dentro do trigger, depois do lock. O nextval do default da coluna também roda e deixa um
-- buraco no seq, o que não afeta a cadeia. A API também pega o mesmo lock antes do insert (defesa dupla).
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
