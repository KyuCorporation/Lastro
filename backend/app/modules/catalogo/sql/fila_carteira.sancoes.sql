-- fila_carteira@v1 — sanções vigentes dos fornecedores da carteira (evidência do sinal sancao_direta), com proveniência
-- Sanção é nacional: sem filtro de UF. Mesma regra de vigência de sancoes_fornecedor@v2.
select s.id, s.fonte_id, s.id_origem, s.url_origem, s.coletado_em, s.hash_conteudo, s.arquivo_bruto_id,
       s.cnpj as fornecedor_cnpj, s.tipo, s.orgao_sancionador, s.uf_orgao, s.data_inicio, s.data_fim,
       count(*) over () as total_linhas
  from sancoes s
  join carteira_itens i on i.fornecedor_cnpj = s.cnpj and i.carteira_id = %(carteira_id)s
 where s.removida_em is null
   and coalesce(s.data_inicio, %(hoje)s) <= %(hoje)s
   and (s.data_fim is null or s.data_fim >= %(hoje)s)
 order by s.data_inicio desc nulls last, s.id
 limit %(limite)s
