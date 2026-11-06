# Login acontece antes de existir contexto: usa a função SECURITY DEFINER de 004_auth_fontes.sql.
BUSCAR_USUARIO_LOGIN = """
select id, tenant_id, nome, perfil, senha_hash, ufs
  from auth_buscar_usuario(%(email)s)
"""

# Roda com o contexto do próprio usuário; a RLS limita usuarios e tenants ao tenant da sessão.
BUSCAR_USUARIO_ATUAL = """
select u.id, u.nome, u.perfil, t.id as tenant_id, t.nome as tenant_nome
  from usuarios u
  join tenants t on t.id = u.tenant_id
 where u.id = ctx_usuario() and u.ativo
"""
