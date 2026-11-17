-- 008_sancoes_retiradas.sql — sanção que sai do CEIS ou do CNEP deixa de contar como vigente.
-- Aprovada em 17/11/2026 (AGENTS.md §4, plano P4.1). Só acrescenta colunas de controle a `sancoes`; grants e
-- policies continuam os de 002_rls.sql (o `lastro_ingest` já tem update em `sancoes`).
--
-- Problema: a pipeline só faz upsert. Sanção revogada ou anulada some do arquivo da CGU, mas a linha ficava no
-- banco com a data final no futuro e continuava "vigente": sinal forte e "sanção vigente" na resposta. Entre os
-- arquivos de 05/11 e 17/11/2026, 375 sanções de PJ sumiram do CEIS, 56 delas ainda vigentes pela data.
-- Correção: cada coleta completa (online, status ok) marca `vista_em` nas sanções do arquivo e `removida_em` nas que
-- não vieram. As colunas não fazem parte do `hash_conteudo`: são do Lastro, não da fonte.
alter table sancoes
  add column vista_em timestamptz,
  add column removida_em timestamptz;

update sancoes set vista_em = coletado_em where vista_em is null;

create index sancoes_ativas_idx on sancoes (cnpj) where removida_em is null;
