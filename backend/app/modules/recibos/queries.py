# Recibos são imutáveis: lastro_app só tem select e insert (002_rls.sql). A RLS limita a leitura ao dono,
# ao auditor e ao admin do tenant; o insert, ao próprio usuário no próprio tenant.

INSERIR_RECIBO = """
insert into recibos (tenant_id, usuario_id, consulta_id, conteudo, hash, criado_em)
values (ctx_tenant(), ctx_usuario(), %(consulta_id)s, %(conteudo)s, %(hash)s, %(criado_em)s)
returning id
"""

BUSCAR_RECIBO = """
select id, conteudo, hash, criado_em
  from recibos
 where id = %(id)s
"""
