# Catálogo de fontes

Para cada fonte: URL oficial, forma de acesso (API ou arquivo), formato, autenticação, limites, paginação, cobertura temporal, frequência de atualização, identificador único, licença, termos de uso, **mapeamento campo a campo para o esquema** (`db/migrations/001_schema.sql`), problemas conhecidos e procedimento de download manual.

| fonte_id | URL | Acesso | Status | Observações |
|---|---|---|---|---|
| pe_portal | https://sistemas.tcepe.tc.br/DadosAbertos/ | API REST (TCE-PE) | aberta no navegador pela equipe em 06/11; endpoints a confirmar | **Obrigatória (R1).** Só IP brasileiro. Estado (`Esfera=E`) e municípios (`Esfera=M`) |
| pncp | https://pncp.gov.br/api/consulta | API pública | testada em 05/11 | OpenAPI em /api/consulta/v3/api-docs; 404 intermitente |
| ceis | Portal da Transparência (dados abertos) | arquivo | | Firewall pode bloquear cliente HTTP |
| cnep | Portal da Transparência (dados abertos) | arquivo | | Idem |
| receita_qsa | (preencher) | API por CNPJ | | Opcional; 1 req/s; só carteiras e sancionadas |
| demo_sintetico | — | seed | | Sintético, rotulado em toda a interface |

## pe_portal — TCE-PE Dados Abertos (detalhe)

**O que se sabe** (documentação do cliente R `tceper`, que consome esta API; confirmar na documentação oficial):

- Cerca de 72 endpoints. Sem autenticação documentada. Restrita a IP brasileiro.
- Filtros comuns (nomes da API): `AnoReferencia`, `CodigoEfiscoUG`, `CodigoMunicipio`, `NumeroEmpenho`, `Esfera` (`E` estado, `M` município), `Natureza`, `CpfCnpj`, `Nome`.
- Conjuntos úteis ao Lastro: contratos (estaduais e municipais), itens e aditivos de contrato, empenhos, liquidações, pagamentos de empenho (**só municípios**), licitações e licitantes, convênios, obras e empresas contratadas, sanções, fornecedores, entidades e municípios.

**O que falta preencher** (olhar a documentação e uma resposta real): caminho exato de cada endpoint, formato (JSON ou XML), paginação, limites, cobertura temporal, campo identificador único, nomes dos campos.

**Mapeamento previsto (hipótese; ajustar com a amostra):**

| Origem TCE-PE | Destino | Regra |
|---|---|---|
| Contrato | `contratos` | `id_origem` = identificador do contrato; `uf` = `PE`; `url_origem` = chamada exata da API; `valor_global`, vigência e objeto dos campos equivalentes |
| Empenho | `pagamentos` | `id_origem` = `emp:<chave>`; `descricao` começa com "empenho" |
| Liquidação | `pagamentos` | `id_origem` = `liq:<chave>`; `data_pagamento` = data da liquidação; `descricao` começa com "liquidação" |
| Unidade gestora / município | `orgaos` | `id` = `pe_portal:<código>`; `esfera` = `estadual` ou `municipal` |
| Credor / contratada | `fornecedores` | CNPJ normalizado e com dígito verificador válido; **CPF (11 dígitos) é descartado** e contado em `registros_descartados` |
| Sanção (opcional) | `sancoes` | só se o CEIS/CNEP estiver bloqueado; `fonte_id` continua `pe_portal` |

**Regras:** 1 requisição por segundo, cache em disco, `User-Agent: lastro-hackathon`. A resposta bruta de cada chamada vai para `data/raw/pe_portal/<data>/` e para `arquivos_brutos` com sha256. Em caso de bloqueio ou queda: salvar as respostas à mão em `data/raw/pe/` e o conector lê delas.

**Pagamentos:** o estado não tem pagamento no endpoint de pagamentos; a leitura de dinheiro que saiu vem de empenho e liquidação. Os sinais por UF (`concentracao`, `penhasco`) usam a data da liquidação.

**Sem sobreposição:** PE vem só desta fonte. O PNCP carrega as outras UFs (AL na demo), salvo `PNCP_PE_FALLBACK=true`.
