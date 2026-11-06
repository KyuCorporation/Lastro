# Fontes e a última execução concluída de cada uma (uma ingestão em andamento não conta).
LISTAR_FONTES = """
select f.id, f.nome, f.tipo,
       e.id as execucao_id, e.status, e.finalizada_em, e.registros_novos
  from fontes f
  left join lateral (
        select x.id, x.status, x.finalizada_em, x.registros_novos
          from execucoes_ingestao x
         where x.fonte_id = f.id and x.status <> 'rodando'
         order by x.iniciada_em desc
         limit 1
  ) e on true
 order by f.id
"""
