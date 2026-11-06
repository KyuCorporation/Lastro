# O trigger auditoria_encadear (001_schema.sql) pega um advisory lock por tenant e lê o último hash. Mas o seq
# (bigserial) é sorteado antes do trigger: com duas transações ao mesmo tempo, a que pegou o seq maior pode
# encadear primeiro, e a ordem do seq deixa de ser a ordem da cadeia (a verificação acusaria quebra falsa).
# Pegar o MESMO lock antes do insert faz o nextval acontecer já com o lock: seq e cadeia na mesma ordem.
# A chave tem de ser idêntica à do trigger (new.tenant_id = ctx_tenant() no insert abaixo).
TRAVAR_CADEIA = "select pg_advisory_xact_lock(hashtext(coalesce(ctx_tenant()::text, 'global')))"

# hash_anterior e hash são preenchidos pelo trigger auditoria_encadear (001_schema.sql).
INSERIR_EVENTO = """
insert into auditoria (tenant_id, usuario_id, evento, detalhes, hash_anterior, hash)
values (ctx_tenant(), ctx_usuario(), %(evento)s, %(detalhes)s, '', '')
"""

# Leitura da trilha: a RLS (auditoria_app_select) já limita ao tenant da sessão e a auditor e admin.
LISTAR_EVENTOS = """
select seq, usuario_id, evento, detalhes, criado_em, hash
  from auditoria
 where tenant_id = ctx_tenant()
   and (%(evento)s::text is null or evento = %(evento)s)
 order by seq desc
 limit %(limite)s
"""

# Verificação da cadeia do tenant (T16), recalculada no banco com a MESMA fórmula do trigger auditoria_encadear
# (001_schema.sql / 006): hash = sha256(hash_anterior | tenant | usuario | evento | detalhes | epoch). Fazer no
# Postgres garante o mesmo texto de jsonb e de epoch que o trigger usou. Um elo quebra quando o hash gravado não
# confere com o conteúdo, ou quando hash_anterior não é o hash do evento anterior (evento apagado ou inserido).
VERIFICAR_CADEIA = """
with trilha as (
  select seq, hash_anterior, hash,
         coalesce(lag(hash) over (order by seq), repeat('0', 64)) as hash_esperado_anterior,
         encode(digest(
           hash_anterior || '|' || coalesce(tenant_id::text, '') || '|' || coalesce(usuario_id::text, '') || '|' ||
           evento || '|' || coalesce(detalhes::text, '') || '|' || extract(epoch from criado_em)::text,
           'sha256'), 'hex') as hash_recalculado
    from auditoria
   where tenant_id = ctx_tenant()
)
select count(*)::int as n_eventos,
       min(seq) filter (where hash_anterior <> hash_esperado_anterior or hash <> hash_recalculado)
         as primeiro_seq_quebrado
  from trilha
"""
