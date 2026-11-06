# Alertas do tenant (RLS alertas_app: só o tenant da sessão). O sinal vem por left join com `sinais`, que tem RLS
# por UF: alerta de um sinal de UF fora do escopo aparece sem o conteúdo do sinal (sinal nulo), nunca com ele.
LISTAR_ALERTAS = """
select a.id, a.carteira_id, a.fornecedor_cnpj as cnpj, a.status, a.criado_em,
       s.id as sinal_id, s.tipo, s.gravidade, s.uf::text as uf, s.explicacao
  from alertas a
  left join sinais s on s.id = a.sinal_id
 where a.tenant_id = ctx_tenant()
   and (%(status)s::text is null or a.status = %(status)s)
 order by a.criado_em desc, a.id
 limit %(limite)s
"""
