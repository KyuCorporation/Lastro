-- sancoes_fornecedor@v1 — sanções CEIS/CNEP do CNPJ, vigentes e passadas. Sanção é nacional: sem filtro de UF.
select s.id, s.fonte_id, s.id_origem, s.url_origem, s.coletado_em, s.hash_conteudo, s.arquivo_bruto_id,
       s.tipo, s.orgao_sancionador, s.uf_orgao, s.data_inicio, s.data_fim, s.fundamentacao,
       (coalesce(s.data_inicio, %(hoje)s) <= %(hoje)s
        and (s.data_fim is null or s.data_fim >= %(hoje)s)) as vigente,
       count(*) over () as total_linhas
  from sancoes s
 where s.cnpj = %(cnpj)s
 order by vigente desc, s.data_inicio desc nulls last, s.id
 limit %(limite)s
