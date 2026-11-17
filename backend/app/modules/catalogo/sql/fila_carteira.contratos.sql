-- fila_carteira@v1 — contratos vigentes dos fornecedores da carteira (formam o valor exposto), com proveniência
select c.id, c.fonte_id, c.id_origem, c.url_origem, c.coletado_em, c.hash_conteudo, c.arquivo_bruto_id,
       c.fornecedor_cnpj, c.uf, c.orgao_id, o.nome as orgao_nome, c.objeto, c.valor_global,
       c.data_assinatura, c.vigencia_inicio, c.vigencia_fim,
       count(*) over () as total_linhas
  from contratos c
  join carteira_itens i on i.fornecedor_cnpj = c.fornecedor_cnpj and i.carteira_id = %(carteira_id)s
  left join orgaos o on o.id = c.orgao_id
 where c.uf::text = any (%(ufs)s::text[])
   and c.vigencia_fim >= %(hoje)s
   and coalesce(c.situacao, 'Regular') = 'Regular'
 order by c.valor_global desc nulls last, c.id
 limit %(limite)s
