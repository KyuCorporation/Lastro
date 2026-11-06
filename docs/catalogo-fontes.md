# Catálogo de fontes

Para cada fonte: URL oficial, forma de acesso (API ou arquivo), formato, autenticação, limites, paginação, cobertura temporal, frequência de atualização, identificador único, licença, termos de uso, **mapeamento campo a campo para o esquema** (`db/migrations/001_schema.sql`), problemas conhecidos e procedimento de download manual.

| fonte_id | URL | Acesso | Status | Observações |
|---|---|---|---|---|
| pe_portal | https://sistemas.tcepe.tc.br/DadosAbertos/ | API REST (TCE-PE) | conector pronto contra formato hipotético; falta a amostra real | **Obrigatória (R1).** Só IP brasileiro. Estado (`Esfera=E`) e municípios (`Esfera=M`) |
| pncp | https://pncp.gov.br/api/consulta | API pública | conector pronto; amostra real coletada em 06/11 | OpenAPI em /api/consulta/v3/api-docs; 404 intermitente |
| ceis | https://portaldatransparencia.gov.br/download-de-dados/ceis/AAAAMMDD | arquivo (zip diário) | conector pronto; download respondeu em 06/11 | Firewall pode bloquear cliente HTTP |
| cnep | https://portaldatransparencia.gov.br/download-de-dados/cnep/AAAAMMDD | arquivo (zip diário) | conector pronto; download respondeu em 06/11 | Idem |
| receita_qsa | (preencher) | API por CNPJ | | Opcional; 1 req/s; só carteiras e sancionadas |
| demo_sintetico | — | seed | | Sintético, rotulado em toda a interface |

## pe_portal — TCE-PE Dados Abertos (detalhe)

**O que se sabe** (documentação do cliente R `tceper`, que consome esta API; confirmar na documentação oficial):

- Cerca de 72 endpoints. Sem autenticação documentada. Restrita a IP brasileiro.
- Filtros comuns (nomes da API): `AnoReferencia`, `CodigoEfiscoUG`, `CodigoMunicipio`, `NumeroEmpenho`, `Esfera` (`E` estado, `M` município), `Natureza`, `CpfCnpj`, `Nome`.
- Conjuntos úteis ao Lastro: contratos (estaduais e municipais), itens e aditivos de contrato, empenhos, liquidações, pagamentos de empenho (**só municípios**), licitações e licitantes, convênios, obras e empresas contratadas, sanções, fornecedores, entidades e municípios.

**O que falta preencher** (olhar a documentação e uma resposta real): caminho exato de cada endpoint, formato (JSON ou XML), paginação, limites, cobertura temporal, campo identificador único, nomes dos campos.

**Como o conector trata a incerteza:** os caminhos (`Contratos!json`, `Empenhos!json`, `Liquidacoes!json`) e o envelope (`resposta.conteudo`, `conteudo`, `dados`…) ficam em `pipeline/lastro_pipeline/connectors/pe_portal.py`; cada campo aceita nomes alternativos em `pipeline/lastro_pipeline/normalize/pe_portal.py`. Recorte: conjunto × ano (`TCEPE_ANOS`) × esfera (`TCEPE_ESFERAS`) × município (`TCEPE_MUNICIPIOS`, opcional). Se a resposta trouxer `totalPaginas`, as páginas seguintes são pedidas com `pagina`.

**Mapeamento previsto (hipótese; ajustar com a amostra):**

| Origem TCE-PE | Destino | Regra |
|---|---|---|
| Contrato | `contratos` | `id_origem` = `ctr:<IdContrato>` ou `ctr:<UG>:<ano>:<número>`; `uf` = `PE`; `url_origem` = chamada exata da API; `valor_global`, vigência e objeto dos campos equivalentes |
| Empenho | `pagamentos` | `id_origem` = `emp:<UG>:<ano>:<empenho>`; `descricao` começa com "empenho" |
| Liquidação | `pagamentos` | `id_origem` = `liq:<UG>:<ano>:<empenho>:<liquidação>`; `data_pagamento` = data da liquidação; `descricao` começa com "liquidação" |
| Unidade gestora / município | `orgaos` | `id` = `pe_portal:<código>`; `esfera` = `estadual` ou `municipal` |
| Credor / contratada | `fornecedores` | CNPJ normalizado e com dígito verificador válido; **CPF (11 dígitos) é descartado** e contado em `registros_descartados` |
| Sanção (opcional) | `sancoes` | só se o CEIS/CNEP estiver bloqueado; `fonte_id` continua `pe_portal` |

**Regras:** 1 requisição por segundo, cache em disco, `User-Agent: lastro-hackathon`. A resposta bruta de cada chamada vai para `data/raw/pe_portal/<data>/` e para `arquivos_brutos` com sha256. Em caso de bloqueio ou queda: salvar as respostas à mão em `data/raw/pe/` e o conector lê delas.

**Pagamentos:** o estado não tem pagamento no endpoint de pagamentos; a leitura de dinheiro que saiu vem de empenho e liquidação. Os sinais por UF (`concentracao`, `penhasco`) usam a data da liquidação.

**Sem sobreposição:** PE vem só desta fonte. O PNCP carrega as outras UFs (AL na demo), salvo `PNCP_PE_FALLBACK=true`.

## pncp — Portal Nacional de Contratações Públicas (detalhe)

Conferido na especificação OpenAPI (`/api/consulta/v3/api-docs`) e numa coleta real em 06/11/2026.

- **Rota:** `GET /v1/contratos?dataInicial=AAAAMMDD&dataFinal=AAAAMMDD&pagina=N&tamanhoPagina=M` (máx. 500). Sem autenticação.
- **Resposta:** `{data: [...], totalRegistros, totalPaginas, numeroPagina, paginasRestantes, empty}`; `204` quando não há contratos.
- **Sem filtro de UF na rota:** o conector divide o período em janelas mensais, pagina cada uma e filtra por `unidadeOrgao.ufSigla`. **PE nunca vem do PNCP**, salvo `PNCP_PE_FALLBACK=true` (mesmo que PE esteja em `PNCP_UFS`).
- **Volume:** outubro/2026 teve 174.972 contratos no país (350 páginas de 500). Nas 40 primeiras páginas, 74 de 20 mil eram de AL. A 1 req/s, um mês leva cerca de 6 minutos e o período padrão (jan/2025 a out/2026), algumas horas. Para a demo, encurte `PNCP_DATA_INICIAL`/`PNCP_DATA_FINAL`.

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
