-- pagamentos_periodo@v2 — pagamentos ao fornecedor no período, com total
-- v2: empenho (id_origem 'emp:', TCE-PE) não é pagamento. As linhas continuam todas (são fonte), mas o total
--     pago soma só o que saiu; o empenhado vem à parte.
select p.id, p.fonte_id, p.id_origem, p.url_origem, p.coletado_em, p.hash_conteudo, p.arquivo_bruto_id,
       p.uf, p.orgao_id, o.nome as orgao_nome, p.contrato_id, p.data_pagamento, p.valor, p.descricao,
       count(*) over ()                                                      as total_linhas,
       count(*) filter (where p.id_origem not like 'emp:%%') over ()         as total_pagos,
       sum(p.valor) filter (where p.id_origem not like 'emp:%%') over ()     as valor_total,
       count(*) filter (where p.id_origem like 'emp:%%') over ()             as total_empenhos,
       sum(p.valor) filter (where p.id_origem like 'emp:%%') over ()         as valor_empenhado_total
  from pagamentos p
  left join orgaos o on o.id = p.orgao_id
 where p.fornecedor_cnpj = %(cnpj)s
   and p.uf::text = any (%(ufs)s::text[])
   and p.data_pagamento between %(data_inicio)s and %(data_fim)s
 order by p.data_pagamento, p.id
 limit %(limite)s
