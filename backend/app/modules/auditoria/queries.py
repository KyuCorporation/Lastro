# hash_anterior e hash são preenchidos pelo trigger auditoria_encadear (001_schema.sql).
INSERIR_EVENTO = """
insert into auditoria (tenant_id, usuario_id, evento, detalhes, hash_anterior, hash)
values (ctx_tenant(), ctx_usuario(), %(evento)s, %(detalhes)s, '', '')
"""
