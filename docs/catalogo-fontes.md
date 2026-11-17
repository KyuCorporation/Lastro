# Catálogo de fontes

Para cada fonte: URL oficial, forma de acesso (API ou arquivo), formato, autenticação, limites, paginação, cobertura temporal, frequência de atualização, identificador único, licença, termos de uso, **mapeamento campo a campo para o esquema** (`db/migrations/001_schema.sql`), problemas conhecidos e procedimento de download manual.

| fonte_id | URL | Acesso | Status | Observações |
|---|---|---|---|---|
| pe_portal | https://sistemas.tcepe.tc.br/DadosAbertos/ | API REST (TCE-PE) | conector conferido na API real e amostra real coletada em 15/11; falta a primeira carga completa | **Obrigatória (R1).** Só IP brasileiro. Estado (`Esfera=E`) e municípios (`Esfera=M`) |
| pncp | https://pncp.gov.br/api/consulta | API pública | conector pronto; amostra real coletada em 06/11 | OpenAPI em /api/consulta/v3/api-docs; 404 intermitente |
| ceis | https://portaldatransparencia.gov.br/download-de-dados/ceis/AAAAMMDD | arquivo (zip diário) | conector pronto; download respondeu em 06/11 | Firewall pode bloquear cliente HTTP |
| cnep | https://portaldatransparencia.gov.br/download-de-dados/cnep/AAAAMMDD | arquivo (zip diário) | conector pronto; download respondeu em 06/11 | Idem |
| receita_qsa | (preencher) | API por CNPJ | | Opcional; 1 req/s; só carteiras e sancionadas |
| demo_sintetico | — | seed | | Sintético, rotulado em toda a interface |

## Resumo por fonte

Consolida os detalhes abaixo e o código dos conectores. 

| | pe_portal (TCE-PE) | pncp | ceis / cnep |
|---|---|---|---|
| Formato | JSON em ISO-8859-1 | JSON | zip com CSV (`latin-1`, `;`) |
| Autenticação | nenhuma documentada | nenhuma | nenhuma |
| Paginação | não há: corta em 100 mil registros; a coleta é fatiada | `pagina` e `tamanhoPagina` (máx. 500) | arquivo inteiro |
| Recorte | contratos: ano × esfera; despesas: exercício × UG (estado) ou × município × mês (`TCEPE_*`) | janelas mensais de `PNCP_DATA_INICIAL` a `PNCP_DATA_FINAL`, filtro por `PNCP_UFS` | arquivo do dia, volta até `SANCOES_DIAS_RETROATIVOS` |
| Identificador único | `ctr:<CodigoContrato>`; `emp:` e `liq:` + UG, exercício e empenho | `numeroControlePNCP` | `CÓDIGO DA SANÇÃO` |
| Licença | dados abertos (LAI) | dados abertos (Lei 14.133/2021) | dados abertos (CGU) |
| Limites conhecidos | só IP brasileiro; 100 mil registros por resposta | 404 intermitente; ~6 min por mês de dados a 1 req/s | firewall pode bloquear cliente HTTP; dia sem arquivo responde 403 |
| Download manual | não implementado | — | zip em `data/raw/sancoes/` com `CEIS` ou `CNEP` no nome |
| Fixture | `amostra` + `exemplo_manual` | `amostra` + `exemplo_manual` | `amostra` (+ `ceis/exemplo_manual`) |

Em todas: 1 requisição por segundo, retry com backoff, cache em disco do dia (30 dias para exercício encerrado do TCE-PE), `User-Agent: lastro-hackathon`, resposta bruta em `data/raw/<fonte>/<data>/` e em `arquivos_brutos` (sha256), e pessoa física descartada e contada em `registros_descartados`. No `pe_portal` a resposta é saneada antes de ser gravada (detalhe abaixo).

## pe_portal — TCE-PE Dados Abertos (detalhe)

**Conferido na API real em 15/11/2026** (página de métodos em `https://sistemas.tcepe.tc.br/DadosAbertos/` e respostas reais). Sem autenticação. Só responde a IP brasileiro.

**Como a API se comporta:**

- URL: `<base>/<Método>!json?<filtros>`. Resposta em **ISO-8859-1**, com envelope `{"resposta": {"status", "entidade", "tamanhoResultado", "limiteResultado", "conteudo": [...]}}`.
- **Não pagina.** Devolve tudo de uma vez e corta em silêncio em `limiteResultado` (100 mil registros). Filtro desconhecido é ignorado sem erro (`AnoReferencia` em `Contratos` devolvia os contratos de todos os anos, 71 MB).
- Colunas `char` vêm preenchidas com espaços. Valores em texto com ponto decimal (`"766482.72"`).
- **Dado pessoal:** em registro de pessoa física, `CPF_CNPJ` vem mascarado (`***.***.614-53`), mas `NumeroDocumentoAjustado` e `NumeroDocumento` trazem o **CPF inteiro**, e o nome vem em claro.

**Métodos usados:**

| Método | O que traz | Filtros usados | Campos usados |
|---|---|---|---|
| `Contratos` | contratos do estado e dos municípios | `AnoContrato`, `Esfera` (`Municipio` só na amostra) | `CodigoContrato`, `CodigoEfiscoUG` (estado), `CodigoUG`, `UnidadeGestora`, `CPF_CNPJ`, `TipoDocumento`, `RazaoSocial`, `Objeto`, `Valor`, `Vigencia` ("dd/mm/aaaa a dd/mm/aaaa"), `Esfera`, `Situacao` ("Regular", "Concluído", "Rescindido por Acordo Entre as Partes", "Suspenso por Decisão Administrativa"), `LinkArquivo` (página do documento no sistema do tribunal, `http://sistemas.tcepe.tc.br/...remessaTCEPE.html?...&idDocumento=N`) |
| `DespesasEstaduais` | um registro por empenho do estado | `ANOREFERENCIA`, `ID_UNIDADE_GESTORA` (e-Fisco) | `NUMEROEMPENHO`, `CPF_CNPJ`, `NOME_FORNECEDOR`, `VALOREMPENHADO`, `DATAEMPENHO`, `HISTORICO`, `NOMEUNIDADEGESTORA` |
| `DespesasMunicipais` | um registro por empenho municipal | `CODIGO_MUNICIPIO`, `ANOREFERENCIA`, `MESREFERENCIA` | os mesmos, mais `ID_EMPENHO` e `FORNECEDOR` |
| `EmpenhoLiquidacao` | liquidações e anulações (valor negativo). **Não traz o credor** | `ANOREFERENCIA`, `ESFERA`, `ID_UNIDADE_GESTORA` | `IDEMPENHO`, `NUMERO`, `TIPO`, `VALOR`, `DATA` |
| `UnidadesJurisdicionadasEstaduais` | lista das unidades gestoras do estado (134) | — | `ID_UNIDADEGESTORA` |
| `Municipios` | nome → código do município no TCE (`P062` = Garanhuns) | `UNIDADEFEDERATIVA=PE` | `MUNICIPIO`, `CODIGO` |

Existem e não são usados: `EmpenhoPagamento` (pagamentos, só municípios), `TermoAditivo`, `Sancoes`, `Fornecedores`, licitações e obras.

**Volume: como a coleta é fatiada.** Cada fatia é uma URL, com cache próprio em `data/raw/_cache/pe_portal/`:

| Conjunto | Fatia | Controle |
|---|---|---|
| Contratos | ano do contrato × esfera, de `TCEPE_CONTRATOS_ANO_INICIAL` até o último ano de `TCEPE_ANOS` (contrato antigo pode estar vigente) | estado: ~10 mil contratos por ano |
| Despesas do estado | exercício (`TCEPE_ANOS`) × unidade gestora (`TCEPE_UGS_ESTADUAIS`; vazio = as 134) | a liquidação só é pedida para UG que teve empenho de PJ |
| Despesas municipais | município de `TCEPE_MUNICIPIOS` × exercício × mês; liquidações por UG vista nas despesas | vazio = nenhum município (o estado inteiro não cabe a 1 req/s) |

- Fatia de **exercício encerrado** vale no cache por `TCEPE_CACHE_DIAS` (30); a do exercício corrente, só no dia. Reexecutar não volta à fonte para o que já foi coletado.
- Fatia que chega a `limiteResultado` **falha** (`RecorteTruncado`) em vez de gravar dado cortado. Como despesa estadual só filtra por UG e ano, uma UG com mais de 100 mil empenhos ou liquidações no ano não pode ser coletada inteira; ainda não foi medido se alguma chega a isso.
- Fatia vazia não vira arquivo no bronze.

**LGPD: o que é gravado.** Toda resposta passa por `normalize.pe_portal.sanear` **antes** de ir para o cache e para o bronze:

- registro de pessoa física (CPF, CPF mascarado ou `TipoDocumento = CPF`) ou sem CNPJ válido vira só o marcador `{"_lastro_omitido": "<motivo>"}`. Nome, documento, objeto e valores não são gravados. O marcador mantém a contagem em `registros_descartados`;
- em registro de PJ, CPF formatado e sequência de 11 dígitos em nome, `Objeto` e `HISTORICO` são mascarados (razão social de MEI costuma trazer o CPF do titular);
- espaços de preenchimento saem; a resposta é regravada em UTF-8, com `saneamento_lgpd.registros_omitidos` no envelope.

Consequência: o arquivo do bronze e o `sha256` em `arquivos_brutos` são os da **resposta saneada**, não os bytes exatos que a fonte mandou. `url_origem` continua sendo a chamada exata, exceto no contrato com `LinkArquivo`. A fixture `amostra/` leva só PJ e só os campos usados, sem `HISTORICO`.

**Mapeamento:**

| Origem TCE-PE | Destino | Regra |
|---|---|---|
| `Contratos` | `contratos` | `id_origem` = `ctr:<CodigoContrato>`; `uf` = `PE`; `valor_global` = `Valor`; vigência extraída de `Vigencia`; `data_assinatura` nula (a API não informa; os sinais usam o início da vigência); `url_origem` = `LinkArquivo` quando é do host `sistemas.tcepe.tc.br`, senão a chamada exata da API |
| `Despesas*` (empenho) | `pagamentos` | `id_origem` = `emp:<UG>:<exercício>:<empenho>` (empenho = `ID_EMPENHO` nos municípios, `NUMEROEMPENHO` no estado); valor = `VALOREMPENHADO`; `descricao` começa com "empenho" |
| `EmpenhoLiquidacao` | `pagamentos` | `id_origem` = `liq:<UG>:<exercício>:<empenho>:<NUMERO>`; credor e órgão vêm do empenho de mesma chave; anulação entra com valor negativo e `descricao` "anulação de liquidação…"; liquidação sem empenho de PJ coletado é descartada (`fora_do_escopo`) |
| Unidade gestora | `orgaos` | `id` = `pe_portal:<código>`: e-Fisco com 6 dígitos no estado (as despesas vêm sem o zero à esquerda e são completadas), código do TCE nos municípios |
| Credor / contratada | `fornecedores` | CNPJ com dígito verificador válido; **pessoa física é descartada** e contada em `registros_descartados` |

**Regras:** 1 requisição por segundo, `User-Agent: lastro-hackathon`. A resposta saneada de cada fatia vai para `data/raw/pe_portal/<data>/` e para `arquivos_brutos` com sha256. A leitura de respostas salvas à mão (`data/raw/pe/`) ainda não existe no conector; se a API cair, vale o cache e a fixture.

**Pagamentos:** a leitura de dinheiro que saiu vem de empenho e liquidação. Os sinais por UF (`concentracao`, `penhasco`) usam a data da liquidação.

**Por que `EmpenhoPagamento` não é carregado** (avaliado em 15/11/2026 com a Prefeitura de Garanhuns, exercício de 2025: 48.731 pagamentos e 21.301 liquidações):

- **Somaria em dobro.** O catálogo e os sinais tratam como "pago" tudo o que não é empenho (`id_origem` sem `emp:`). Todo empenho com pagamento tinha liquidação, e o total pago foi 97,6% do liquidado. Gravar os dois dobraria o valor pago, a menos que as consultas do catálogo, os sinais e o gabarito mudassem.
- **Não há identificador do pagamento.** Os campos são empenho, tipo, data, valor e dados bancários (banco, agência, conta, cheque). Empenho + data + valor + tipo se repete; só os dados bancários distinguem os registros, e um `id_origem` feito deles não é estável.
- **Só existe para municípios.** "Pago" passaria a significar pagamento nos municípios e liquidação no estado.

Se o produto precisar da data efetiva de pagamento, a decisão é trocar a liquidação pelo pagamento nos municípios (e não somar os dois), com mudança no catálogo.

**Sem sobreposição:** PE vem só desta fonte. O PNCP carrega as outras UFs (AL na demo), salvo `PNCP_PE_FALLBACK=true`.

## pncp — Portal Nacional de Contratações Públicas (detalhe)

Conferido na especificação OpenAPI (`/api/consulta/v3/api-docs`) e numa coleta real em 06/11/2026.

- **Rota:** `GET /v1/contratos?dataInicial=AAAAMMDD&dataFinal=AAAAMMDD&pagina=N&tamanhoPagina=M` (máx. 500). Sem autenticação.
- **Resposta:** `{data: [...], totalRegistros, totalPaginas, numeroPagina, paginasRestantes, empty}`; `204` quando não há contratos.
- **Sem filtro de UF na rota:** o conector divide o período em janelas mensais, pagina cada uma e filtra por `unidadeOrgao.ufSigla`. **PE nunca vem do PNCP**, salvo `PNCP_PE_FALLBACK=true` (mesmo que PE esteja em `PNCP_UFS`).
- **Volume:** outubro/2026 teve 174.972 contratos no país (350 páginas de 500). Nas 40 primeiras páginas, 74 de 20 mil eram de AL. A 1 req/s, um mês leva cerca de 6 minutos. O período padrão do `.env.example` é um mês (out/2026); período longo leva horas.

| Origem (RecuperarContratoDTO) | Destino | Regra |
|---|---|---|
| `numeroControlePNCP` | `contratos.id_origem` | identificador único nacional |
| `unidadeOrgao.ufSigla` | `contratos.uf` | filtro de UF |
| `orgaoEntidade.cnpj` + `unidadeOrgao.codigoUnidade` | `orgaos.id` = `pncp:<cnpj>:<unidade>` | `esferaId` F/E/M/D → federal/estadual/municipal/distrital |
| `niFornecedor`, `tipoPessoa`, `nomeRazaoSocialFornecedor` | `fornecedores` | `PF` ou CPF → descartado; estrangeiro sem CNPJ → descartado |
| `objetoContrato`, `valorGlobal` (ou `valorInicial`), `dataAssinatura`, `dataVigenciaInicio`, `dataVigenciaFim` | `contratos` | valores em decimal, nunca float |
| `orgaoEntidade.cnpj`, `anoContrato`, `sequencialContrato` | `contratos.url_origem` | `https://pncp.gov.br/app/contratos/<cnpj>/<ano>/<sequencial>` |

## ceis e cnep — sanções (detalhe)

Conferido nos arquivos reais de 05/11/2026 (CEIS: 23.759 linhas, 14.598 de PJ; CNEP: 1.854 linhas, 1.814 de PJ).

- **Download:** `https://portaldatransparencia.gov.br/download-de-dados/<ceis|cnep>/AAAAMMDD` redireciona para um zip em `dadosabertos-download.cgu.gov.br` com um CSV (`latin-1`, separador `;`).
- **Dia sem arquivo responde 403** (`AccessDenied` do armazenamento), não 404. O conector volta até `SANCOES_DIAS_RETROATIVOS` dias (padrão 7) e não guarda essa resposta em cache.
- **Download manual (firewall ou fonte fora):** baixar o zip no navegador e salvar em `data/raw/sancoes/` com `CEIS` ou `CNEP` no nome. O conector usa o mais recente. Não contornar bloqueio.
- `url_origem` = URL do arquivo baixado.

| Coluna do CSV | Destino | Regra |
|---|---|---|
| `CÓDIGO DA SANÇÃO` | `sancoes.id_origem` | |
| `TIPO DE PESSOA`, `CPF OU CNPJ DO SANCIONADO` | `sancoes.cnpj` | `F` ou CPF → descartado |
| `CATEGORIA DA SANÇÃO` | `sancoes.tipo` | |
| `ÓRGÃO SANCIONADOR`, `UF ÓRGÃO SANCIONADOR` | `orgao_sancionador`, `uf_orgao` | |
| `DATA INÍCIO SANÇÃO`, `DATA FINAL SANÇÃO` | `data_inicio`, `data_fim` | dd/mm/aaaa; data final pode vir vazia |
| `FUNDAMENTAÇÃO LEGAL` | `fundamentacao` | cortada em 2.000 caracteres |
