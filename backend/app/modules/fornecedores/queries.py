# Dossiê do fornecedor. Contratos, pagamentos e sinais chegam filtrados pela RLS às UFs do usuário; o filtro
# explícito por ctx_ufs() é defesa em profundidade. Identidade, órgãos e sanções são públicos para quem está
# autenticado (002_rls.sql). Toda linha leva a proveniência: fonte_id, id_origem, url_origem, coletado_em.

FORNECEDOR = """
select cnpj, razao_social, uf_sede
  from fornecedores
 where cnpj = %(cnpj)s
"""

# Empenho (id_origem 'emp:', TCE-PE) não é pagamento: "pago" soma o que saiu; o empenhado vem à parte,
# como no catálogo (resumo_fornecedor@v2).
RESUMO_POR_UF = """
with c as (
  select uf, count(*)::int as n_contratos, sum(valor_global) as valor_contratado,
         sum(valor_global) filter (where vigencia_fim >= %(hoje)s) as valor_vigente
    from contratos
   where fornecedor_cnpj = %(cnpj)s and uf::text = any (ctx_ufs())
   group by uf
),
p as (
  select uf,
         (count(*) filter (where id_origem not like 'emp:%%'))::int as n_pagamentos,
         sum(valor) filter (where id_origem not like 'emp:%%')      as valor_pago,
         sum(valor) filter (where id_origem like 'emp:%%')          as valor_empenhado
    from pagamentos
   where fornecedor_cnpj = %(cnpj)s and uf::text = any (ctx_ufs())
   group by uf
)
select coalesce(c.uf, p.uf)::text           as uf,
       coalesce(c.n_contratos, 0)           as n_contratos,
       coalesce(c.valor_contratado, 0)      as valor_contratado,
       coalesce(c.valor_vigente, 0)         as valor_vigente,
       coalesce(p.n_pagamentos, 0)          as n_pagamentos,
       coalesce(p.valor_pago, 0)            as valor_pago,
       coalesce(p.valor_empenhado, 0)       as valor_empenhado
  from c
  full join p on p.uf = c.uf
 order by 1
"""

CONTRATOS_VIGENTES = """
select c.id, c.fonte_id, c.id_origem, c.url_origem, c.coletado_em, c.uf::text as uf, c.orgao_id,
       o.nome as orgao_nome, c.objeto, c.valor_global, c.data_assinatura, c.vigencia_inicio, c.vigencia_fim
  from contratos c
  left join orgaos o on o.id = c.orgao_id
 where c.fornecedor_cnpj = %(cnpj)s
   and c.uf::text = any (ctx_ufs())
   and c.vigencia_fim >= %(hoje)s
 order by c.vigencia_fim, c.id
 limit %(limite)s
"""

SANCOES = """
select id, fonte_id, id_origem, url_origem, coletado_em, tipo, orgao_sancionador, uf_orgao::text as uf_orgao,
       data_inicio, data_fim, fundamentacao
  from sancoes
 where cnpj = %(cnpj)s
 order by data_inicio desc nulls last, id
 limit %(limite)s
"""

SINAIS = """
select id, tipo, gravidade, uf::text as uf, valor, explicacao, evidencias, versao_regra, calculado_em
  from sinais
 where fornecedor_cnpj = %(cnpj)s
   and (uf is null or uf::text = any (ctx_ufs()))
 order by case gravidade when 'forte' then 0 when 'atencao' then 1 else 2 end, tipo, uf nulls first
"""

# A RLS de socios já esconde a tabela do gestor; o serviço nem consulta para quem não pode (SPEC §6.2).
SOCIOS = """
select socio_tipo, socio_exibicao, fonte_id, coletado_em
  from socios
 where cnpj = %(cnpj)s
 order by socio_tipo, socio_exibicao
 limit %(limite)s
"""

FONTES = """
select id, nome, tipo
  from fontes
 where id = any (%(ids)s)
"""
