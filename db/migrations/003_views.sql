-- 003_views.sql — views de apoio. Sempre security_invoker = true para respeitar a RLS de quem consulta.

create view v_contratos_vigentes with (security_invoker = true) as
select c.*
  from contratos c
 where c.vigencia_fim >= current_date;

create view v_resumo_fornecedor with (security_invoker = true) as
select c.fornecedor_cnpj,
       c.uf,
       count(*)                                   as n_contratos,
       sum(c.valor_global)                        as valor_contratado,
       sum(c.valor_global) filter (where c.vigencia_fim >= current_date) as valor_vigente,
       min(c.data_assinatura)                     as primeira_assinatura,
       max(c.vigencia_fim)                        as ultima_vigencia
  from contratos c
 group by c.fornecedor_cnpj, c.uf;

create view v_pagamentos_fornecedor with (security_invoker = true) as
select p.fornecedor_cnpj,
       p.uf,
       count(*)       as n_pagamentos,
       sum(p.valor)   as valor_pago,
       max(p.data_pagamento) as ultimo_pagamento
  from pagamentos p
 group by p.fornecedor_cnpj, p.uf;

grant select on v_contratos_vigentes, v_resumo_fornecedor, v_pagamentos_fornecedor to lastro_app;
