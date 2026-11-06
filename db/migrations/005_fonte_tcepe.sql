-- 005_fonte_tcepe.sql — a fonte estadual de PE passa a ser a API de dados abertos do TCE-PE.
-- O id 'pe_portal' é mantido para não quebrar referências; só mudam os metadados.
update fontes
   set nome = 'TCE-PE Dados Abertos',
       tipo = 'api',
       url_base = 'https://sistemas.tcepe.tc.br/DadosAbertos/',
       licenca = 'Dados abertos (LAI)',
       observacoes = 'API restrita a IP brasileiro. Contratos e empenhos/liquidações do estado e dos municípios de PE. Mapeamento em docs/catalogo-fontes.md'
 where id = 'pe_portal';
