# Alertas do tenant (RLS alertas_app: só o tenant da sessão). O sinal vem por left join com `sinais`, que tem RLS
# por UF. Quando o sinal já foi apagado pela pipeline (deixou de valer), vale a cópia guardada no alerta, com o
# mesmo filtro de UF da policy de `sinais`: alerta de um sinal de UF fora do escopo aparece sem o conteúdo do
# sinal (sinal nulo), nunca com ele.
LISTAR_ALERTAS = """
select a.id, a.carteira_id, a.fornecedor_cnpj as cnpj, a.status, a.criado_em,
       s.id as sinal_id,
       (s.id is not null
        or (a.sinal_tipo is not null and (a.sinal_uf is null or a.sinal_uf::text = any (ctx_ufs()))))
         as sinal_visivel,
       coalesce(s.tipo, a.sinal_tipo) as tipo,
       coalesce(s.gravidade, a.sinal_gravidade) as gravidade,
       coalesce(s.uf, a.sinal_uf)::text as uf,
       coalesce(s.explicacao, a.sinal_explicacao) as explicacao
  from alertas a
  left join sinais s on s.id = a.sinal_id
 where a.tenant_id = ctx_tenant()
   and (%(status)s::text is null or a.status = %(status)s)
 order by a.criado_em desc, a.id
 limit %(limite)s
"""

# Alerta por evento (SPEC §3.3 I7): cada sinal de fornecedor da carteira que ainda não gerou alerta nesta carteira
# vira um alerta aberto, com a cópia do que o sinal diz. A RLS de `sinais` limita aos sinais da UF de quem abre a
# fila. Roda na mesma transação da fila e da criação da carteira.
GERAR_ALERTAS_DA_CARTEIRA = """
insert into alertas (tenant_id, carteira_id, fornecedor_cnpj, sinal_id,
                     sinal_tipo, sinal_gravidade, sinal_uf, sinal_explicacao)
select ctx_tenant(), i.carteira_id, i.fornecedor_cnpj, s.id, s.tipo, s.gravidade, s.uf, s.explicacao
  from carteira_itens i
  join sinais s on s.fornecedor_cnpj = i.fornecedor_cnpj
 where i.carteira_id = %(carteira_id)s
on conflict (carteira_id, sinal_id) where sinal_id is not null do nothing
"""
