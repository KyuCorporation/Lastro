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
