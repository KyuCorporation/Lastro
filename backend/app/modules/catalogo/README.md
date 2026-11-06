# catalogo/ — consultas parametrizadas

Uma intent = um arquivo `sql/<intent>.sql` + uma entrada em `registry.py` com:
- `id` e `versao` (vai para o recibo como `intent@versao`);
- descrição curta para o prompt do planejador;
- modelo Pydantic dos parâmetros;
- quais colunas viram marcadores para o redator e de que tipo (moeda, data, inteiro, percentual);
- modelo de resposta determinístico (fallback do verificador).

Toda consulta retorna as colunas de proveniência (`id`, `fonte_id`, `id_origem`, `url_origem`, `coletado_em`, `hash_conteudo`) das linhas usadas.
A UF efetiva é `parametros.uf ∩ ctx_ufs()`; se a interseção for vazia e o plano pediu UF, o executor levanta `ESCOPO_NEGADO`.
Nada de SQL dinâmico além de parâmetros. `statement_timeout` de 5 s e limite de 200 linhas.
