# SPEC — Lastro: radar de risco de fornecedores, com recibo

> Hack Garanhuns Tech 2026 · Desafio 1 (Portal Inteligente de Transparência com IA) · Equipe KYU
> Versão 1.1 · 06/11/2026, 04h00 (fonte de PE passa a ser a API de dados abertos do TCE-PE) · Fonte da verdade do produto.

"Lastro" é o nome de trabalho. Pode ser trocado sem impacto no código.

---

## 1. O produto em uma frase

Uma consultoria de gestão de terceiros sobe a **carteira de fornecedores** de um cliente. O Lastro cruza dados públicos de transparência (dados abertos do Tribunal de Contas de PE, PNCP e listas de sanções), devolve uma **fila priorizada por sinais de risco** e responde perguntas em linguagem natural com um **recibo verificável**: cada número aponta para a linha e a fonte oficial de onde veio.

Toda consulta respeita **estado, perfil e contexto** (a carteira e a finalidade). Quem barra o acesso é o banco de dados, não o prompt.

## 2. Problema, persona e hipótese

- **Persona principal:** analista de risco de fornecedores de uma consultoria de gestão de terceiros. Ele homologa e monitora fornecedores dos clientes.
- **Personas secundárias:** auditor interno (confere consultas e recibos) e gestor de contrato (lê o dossiê de uma página).
- **Tarefa:** levantar o histórico de contratos e pagamentos públicos de um fornecedor e decidir se ele exige diligência reforçada.
- **Dor:** dados dispersos e em formatos diferentes, busca manual demorada, e resposta de IA sem fonte não serve para compliance.
- **Hipótese:** o analista leva mais de 30 min para levantar os pagamentos de um fornecedor.
- **Métrica de valor:** minutos por fornecedor, antes e depois; % de respostas com recibo íntegro; zero vazamento entre estados e tenants.

## 3. Escopo

### 3.1 Requisitos mínimos do desafio (obrigatórios)

| ID | Requisito do desafio | Como o Lastro cumpre | Evidência na demo |
|---|---|---|---|
| R1 | Captura de ao menos um portal estadual | Conector da **API de dados abertos do TCE-PE** (contratos e empenhos/liquidações do estado e dos municípios de PE), com cada resposta bruta e seu hash guardados. Fonte oficial do estado | Tela de fontes mostra a execução, a data de coleta e o hash |
| R2 | Normalização e catalogação | Esquema único (fornecedor, órgão, UF, contrato, pagamento) com proveniência por linha; catálogo de fontes e dicionário de dados | `docs/catalogo-fontes.md` e `docs/dicionario-dados.md`; tela de fontes |
| R3 | Controle de acesso por estado e perfil | Contexto de acesso por requisição, aplicado por **Row-Level Security** no Postgres | Mesma pergunta, dois usuários, respostas diferentes |
| R4 | LLM restrita aos dados autorizados | A LLM nunca toca o banco: escolhe uma consulta do catálogo; o backend executa sob RLS e entrega à LLM só o resultado autorizado | Pergunta pedindo outro estado é negada |
| R5 | Registro de consultas e fontes | Tabela `consultas`, recibo por resposta e trilha de auditoria encadeada por hash | Tela de auditoria e verificação do recibo |

A **citação de fonte** faz parte do escopo do MVP e é obrigatória.

### 3.2 Diferenciais

| ID | Diferencial | Como |
|---|---|---|
| D1 | RAG com citação de fonte | Recuperação estruturada (SQL do catálogo) mais busca textual no objeto dos contratos (full-text do Postgres). Citações vêm do backend, nunca do texto da LLM |
| D2 | Multi-tenant | Cada cliente da consultoria é um tenant. RLS isola carteiras, consultas, recibos, alertas e auditoria |
| D3 | Proteção contra ataques de prompt | Defesa por arquitetura (§8.5): planejador sem acesso a dado, redator em quarentena, números inseridos por código, verificador. Suíte de 50 ataques, incluindo injeção armazenada no dado |

### 3.3 Inovações

| ID | Inovação |
|---|---|
| I1 | **Recibo verificável**: cada resposta tem um recibo com consulta, parâmetros, linhas, fontes, hashes e versão do modelo. Um endpoint recalcula o hash e diz se está íntegro |
| I2 | **Números nunca vêm da LLM**: o redator escreve com marcadores (`{{v1}}`); o código insere os valores; o verificador reprova qualquer número que não esteja no resultado |
| I3 | **Carteira com fila de risco**: o cliente sobe CNPJs e recebe uma fila priorizada por sinais explicáveis (sanção direta, penhasco de contratos, concentração em um órgão) |
| I4 | **Trilha de auditoria encadeada** (cada evento carrega o hash do anterior), à prova de adulteração silenciosa |
| I5 | **Contexto por carteira e finalidade**, além de estado e perfil: o enunciado pede "estado, perfil e contexto" |
| I6 | **Contágio por sócio**: sócio em comum com empresa sancionada (só como "atenção") |
| I7 | **Alertas por evento**: nova sanção ou sinal reabre o fornecedor na fila do tenant |
| I8 | **Reuso entre clientes**: dado público coletado uma vez serve a todos os tenants, sem compartilhar nada privado |

### 3.4 Fora de escopo

Perfil de cidadão; comparação entre estados como funcionalidade; reranker; embeddings e pgvector (a busca textual do Postgres basta; reavaliar só se sobrar tempo e houver GPU); Keycloak; Prometheus, Grafana e OpenTelemetry; Kubernetes; previsão por modelo treinado. O caminho para produção está em `docs/arquitetura.md`, seção "Para produção".

## 4. Arquitetura

### 4.1 Princípios inegociáveis

1. **A LLM não controla acesso.** O escopo vem da sessão autenticada e é aplicado por RLS. Nenhum texto de prompt amplia escopo.
2. **A LLM não toca o banco e não calcula.** Ela escolhe uma consulta do catálogo (planejador) e redige texto com marcadores (redator). Quem consulta e calcula é o código.
3. **Proveniência nasce no dado.** Toda linha pública tem `fonte_id`, `id_origem`, `url_origem`, `coletado_em`, `hash_conteudo` e `arquivo_bruto_id`. A citação é montada a partir disso.
4. **Sem evidência, sem resposta.** Resultado vazio ou fora do escopo gera abstenção explícita.
5. **Sinal não é acusação.** Só sanção direta é "forte". O resto é "atenção", com explicação e evidência.

### 4.2 Camadas e pastas

```
pipeline/   Ingestão (bronze → normalizado), qualidade, cálculo de sinais. Usa o papel lastro_ingest.
db/         Migrations (schema, RLS, views) e seeds de demonstração. Fonte da verdade do modelo de dados.
backend/    API FastAPI. Usa o papel lastro_app (sem BYPASSRLS).
  core/       config, conexão, sessão com contexto de acesso, segurança, logs
  modules/    auth, policy, catalogo, consulta, recibos, carteiras, fornecedores, sinais, alertas, auditoria, metricas
  llm/        interface de provedor (gemini, mock), prompts versionados
frontend/   React + Vite + TypeScript.
contracts/  Contratos congelados: recibo, plano de consulta, API.
eval/       Gabarito de perguntas, suíte de ataques, harness e relatórios.
docs/       Arquitetura, ADRs, catálogo de fontes, dicionário, matriz de requisitos, modelo de ameaças, premissas e limitações, avaliação.
data/       raw/ (fora do git) e fixtures/ (amostras pequenas versionadas para testes e demo offline).
```

### 4.3 Fluxo de uma consulta

```mermaid
sequenceDiagram
  participant U as Analista (frontend)
  participant A as API (lastro_app)
  participant P as Planejador LLM
  participant DB as Postgres (RLS)
  participant R as Redator LLM (quarentena)
  participant V as Verificador (código)
  U->>A: POST /consultas {pergunta, carteira_id?}
  A->>A: autentica JWT, monta contexto (tenant, usuário, perfil, UFs)
  A->>DB: BEGIN; set_config(app.*) local à transação
  A->>P: pergunta + catálogo de consultas (sem nenhum dado do banco)
  P-->>A: plano JSON (contracts/plano_consulta.schema.json)
  A->>A: valida plano (Pydantic); UF pedida ∩ UFs autorizadas; parâmetros tipados
  alt fora de escopo ou UF não autorizada
    A->>DB: auditoria(evento=negado ou abstencao)
    A-->>U: resposta de abstenção ou negação, com motivo
  else plano válido
    A->>DB: executa SQL parametrizado do catálogo (RLS filtra)
    DB-->>A: linhas + metadados de proveniência
    A->>R: resultado estruturado; campos de texto marcados como dado não confiável
    R-->>A: texto com marcadores {{v1}}, {{v2}}
    A->>V: insere valores por código e confere números, citações e marcadores
    V-->>A: aprovado, ou reprovado (cai no modelo de resposta determinístico)
    A->>DB: grava consulta, recibo (hash) e auditoria (encadeada)
    A-->>U: resposta + citações + recibo_id
  end
```

### 4.4 Stack

| Camada | Escolha | Motivo |
|---|---|---|
| Banco | PostgreSQL 16 | RLS, views `security_invoker`, full-text em português, pgcrypto |
| Backend | Python 3.12, FastAPI, Pydantic v2, psycopg 3 (SQL explícito, sem ORM) | SQL parametrizado e visível facilita revisão e citação |
| Ingestão | Python 3.12, httpx, polars ou csv da stdlib | Simples e rápido |
| LLM | Interface própria com provedores `gemini` e `mock`; modelo por variável `LLM_MODEL` | Gemini como provedor principal; `mock` garante testes determinísticos e demo sem rede |
| Auth | JWT HS256 com usuários de seed | Sem provedor de identidade externo no MVP |
| Frontend | React 18, Vite, TypeScript, TanStack Query, Tailwind | Rápido de montar |
| Execução | Docker Compose (db, api, web) e `pipeline` via `docker compose run` | Reprodutível pelo README |

Não usar Redis ou fila. A ingestão roda por CLI, é idempotente e registra `execucoes_ingestao`.

## 5. Modelo de dados

A fonte da verdade é `db/migrations/`. Resumo:

- **Identidade e escopo:** `tenants`, `usuarios` (perfil), `escopos` (UFs por usuário).
- **Proveniência:** `fontes`, `execucoes_ingestao`, `arquivos_brutos` (sha256 único por fonte).
- **Fatos públicos:** `orgaos`, `fornecedores` (só CNPJ), `contratos` (com `objeto_tsv` para busca textual), `pagamentos`, `sancoes`, `socios` (sócio guardado como chave hash e exibição mascarada).
- **Derivados:** `sinais` (por fornecedor **e por UF**, para não vazar UF via sinal).
- **Do tenant:** `carteiras` (com `finalidade`), `carteira_itens`, `consultas`, `recibos`, `alertas`, `auditoria` (encadeada por hash).

Regras:
- **Somente pessoa jurídica.** Linhas com CPF como favorecido são descartadas na normalização e contadas no relatório de qualidade.
- **Idempotência:** chave única `(fonte_id, id_origem)`; reingestão faz upsert e só atualiza se `hash_conteudo` mudou.
- **Valores** em `numeric(18,2)`, datas em `date`, CNPJ com 14 dígitos sem máscara.

## 6. Controle de acesso

### 6.1 Contexto de acesso

A cada requisição autenticada, a API abre uma transação e executa `select set_config('app.tenant_id', $1, true)` (e o mesmo para `app.usuario_id`, `app.perfil`, `app.ufs`). As políticas de RLS leem esse contexto pelas funções `ctx_tenant()`, `ctx_usuario()`, `ctx_perfil()` e `ctx_ufs()`. Sem contexto, nada é visível.

O papel `lastro_app` não é dono das tabelas e não tem `BYPASSRLS`. Todas as tabelas com RLS usam `FORCE ROW LEVEL SECURITY`.

### 6.2 Matriz de perfis

| Ação | analista | gestor | auditor | admin |
|---|---|---|---|---|
| Fazer consulta em linguagem natural | sim | não | não | sim |
| Ver dossiê de fornecedor | sim | sim | sim | sim |
| Criar e editar carteira | sim | não | não | sim |
| Ver fila da carteira | sim | sim | sim | sim |
| Ver as próprias consultas e recibos | sim | — | — | sim |
| Ver consultas e recibos de todo o tenant | não | não | sim | sim |
| Ver auditoria do tenant | não | não | sim | sim |
| Ver sócios (mascarados) | sim | não | sim | sim |

Em todos os casos, só nas **UFs do escopo do usuário** e só no **tenant dele**.

### 6.3 Usuários de demonstração (seed, senha `demo123`, só desenvolvimento)

| E-mail | Tenant | Perfil | UFs |
|---|---|---|---|
| ana@alfa.demo | Cliente Alfa | analista | PE |
| caio@alfa.demo | Cliente Alfa | auditor | PE |
| gil@alfa.demo | Cliente Alfa | gestor | PE |
| admin@alfa.demo | Cliente Alfa | admin | PE, AL |
| bia@beta.demo | Cliente Beta | analista | AL |

A segunda UF (AL) vem do PNCP. Se for carregada outra UF, ajustar o seed e esta tabela.

### 6.4 Casos obrigatórios da matriz de testes (`backend/app/tests/test_acesso.py`)

1. ana pergunta sobre PE → responde. ana pergunta sobre AL → negado, sem vazar contagem.
2. bia não vê carteira, consulta, recibo, alerta nem auditoria do Cliente Alfa, nem por ID direto (IDOR).
3. Sinal calculado com contratos de AL não aparece para ana (sinal é por UF).
4. Busca textual em `objeto` não retorna contrato fora das UFs do usuário.
5. gil (gestor) não consegue `POST /consultas` (403) e o evento vai para a auditoria.
6. Sem token: 401 em tudo, exceto `/auth/login` e `/health`.
7. Conexão como `lastro_app` sem `set_config`: `select count(*) from contratos` retorna 0.
8. `lastro_app` não consegue `UPDATE` nem `DELETE` em `auditoria` e `recibos`.

## 7. Catálogo de consultas (Action-Selector)

O planejador só pode escolher entre estas intenções. Cada uma tem SQL fixo e parametrizado em `backend/app/modules/catalogo/`. Toda consulta retorna, junto com os dados, as colunas de proveniência de cada linha usada.

| Intent | Parâmetros | O que retorna |
|---|---|---|
| `resumo_fornecedor` | cnpj, uf? | Nº de contratos, valor contratado, valor pago, por UF e órgão |
| `contratos_vigentes` | cnpj, uf? | Contratos com `vigencia_fim >= hoje` |
| `contratos_vencendo` | cnpj, dias (1–365, padrão 180), uf? | Contratos vigentes que terminam no prazo, com % do valor vigente |
| `pagamentos_periodo` | cnpj, data_inicio, data_fim, uf? | Pagamentos e total no período |
| `sancoes_fornecedor` | cnpj | Sanções CEIS/CNEP vigentes e passadas |
| `orgaos_fornecedor` | cnpj, uf? | Ranking de órgãos por valor e participação (concentração) |
| `busca_objeto` | termo (texto, até 80 caracteres), uf? | Contratos cujo objeto casa com o termo (full-text), top 20 |
| `fila_carteira` | carteira_id | Fornecedores da carteira ordenados por prioridade, com sinais |
| `socios_sancionados` | cnpj | Sócios em comum com empresas sancionadas |
| `fora_de_escopo` | motivo | Nada; gera abstenção |
| `esclarecer` | pergunta_de_volta | Nada; pede esclarecimento |

Regras do executor:
- `uf` do plano é **interseccionada** com `ctx_ufs()`. Se o plano pedir UF fora do escopo, a resposta é negação com motivo, e a auditoria registra `negado`.
- CNPJ validado (14 dígitos e dígitos verificadores). Datas validadas. Termo de busca passa por `plainto_tsquery('portuguese', $1)`.
- Timeout de 5 s por consulta (`SET LOCAL statement_timeout`). Limite de 200 linhas.

## 8. Camada de IA

### 8.1 Planejador

- Entrada: a pergunta do usuário, a data de hoje, as UFs do escopo e a descrição do catálogo (§7). **Nenhum dado do banco.**
- Saída: JSON validado por `contracts/plano_consulta.schema.json`. Saída inválida tenta uma vez e depois vira `esclarecer`.
- Prompt versionado em `backend/app/llm/prompts/planejador_v1.md`. A versão vai para o recibo.

### 8.2 Redator (quarentena)

- Entrada: a pergunta e o resultado estruturado. Campos de texto vindos de fonte externa (razão social, objeto, fundamentação) vão dentro de `<dado_nao_confiavel>…</dado_nao_confiavel>`, com a instrução de que são dados, nunca ordens.
- Saída: texto curto em português simples, com marcadores `{{v1}}` para todo número, valor ou data. O redator recebe a lista de marcadores disponíveis e o significado de cada um.
- O redator **não tem ferramentas** e não vê o contexto de acesso.

### 8.3 Verificador

1. Substitui os marcadores pelos valores formatados (R$ com duas casas, datas dd/mm/aaaa).
2. Reprova se sobrar marcador desconhecido, se aparecer número que não veio de marcador (exceto anos citados no plano), ou se aparecer CNPJ ou URL fora do resultado.
3. Reprova se o texto contiver padrões de vazamento: instruções do sistema, nomes de outros tenants, UFs fora do escopo.
4. Em reprovação, usa o **modelo determinístico** da intent (texto pronto com os valores) e marca `verificacao.status = "fallback"` no recibo.

### 8.4 Abstenção e esclarecimento

Resultado vazio → "Não encontrei registros de … nas fontes autorizadas para você (PE), coletadas em …". Nunca inventar. Pergunta ambígua → intent `esclarecer`.

### 8.5 Defesas contra injeção (mapeadas aos padrões de 2025)

| Padrão | Onde |
|---|---|
| Action-Selector | Planejador só escolhe intents do catálogo |
| Plan-Then-Execute | Escopo e plano fixados antes de qualquer dado externo entrar |
| Dual LLM / quarentena | Redator recebe dado não confiável e não tem ferramentas |
| Context-Minimization | Planejador nunca vê dado; redator vê só o resultado necessário |
| Controle no dado | RLS: mesmo que tudo falhe, o banco não entrega linha fora do escopo |

Injeção armazenada para a demo: `db/seeds/020_demo_ataque.sql` cria um fornecedor **fictício**, de fonte `demo_sintetico`, com instruções maliciosas na razão social e no objeto do contrato.

### 8.6 Configuração

`LLM_PROVIDER=gemini|mock`, `LLM_MODEL`, `GEMINI_API_KEY`. Temperatura 0 no planejador e baixa no redator. Timeout de 20 s; se a LLM cair, o planejador usa um roteador por regras (palavras-chave + CNPJ na pergunta) e o redator cai no modelo determinístico. **A demo precisa funcionar com a LLM fora do ar.**

## 9. Sinais de risco

Calculados pela pipeline (`pipeline/sinais/`) **por fornecedor e por UF**, versionados (`versao_regra`), sempre com `explicacao` em uma frase e `evidencias` (lista de `{tabela, id, url_origem}`).

| Sinal | Regra (v1) | Gravidade |
|---|---|---|
| `sancao_direta` | CNPJ em CEIS ou CNEP com sanção vigente | forte |
| `penhasco` | ≥ 50% do valor contratado vigente termina em até 180 dias | atenção |
| `concentracao` | Maior órgão responde por ≥ 70% do valor recebido nos últimos 24 meses | atenção |
| `contagio` | Sócio em comum com empresa com sanção vigente (opcional) | atenção |
| `liquidez` | Condicional: só se o dado de PE tiver liquidação e pagamento separados; regra a definir | atenção |

**Prioridade na fila:** `peso_gravidade × log10(1 + valor_exposto)`, com forte = 10, atenção = 3, info = 1. O valor exposto é o valor vigente do fornecedor nas UFs do usuário. A fila mostra a regra aplicada.

**Linguagem obrigatória na interface:** "sinal para investigar", nunca "fraude", "irregular" ou "suspeito".

## 10. Fontes e ingestão

| Fonte | `fonte_id` | Acesso | Observações |
|---|---|---|---|
| Dados abertos do TCE-PE | `pe_portal` (id mantido; nome exibido: "TCE-PE Dados Abertos") | API REST em `https://sistemas.tcepe.tc.br/DadosAbertos/`, sem autenticação documentada | **Obrigatória (R1).** Só responde a **IP brasileiro**: a ingestão real roda na máquina da equipe, nunca em agente de nuvem (que usa fixtures). Cobre estado (`Esfera=E`) e municípios (`Esfera=M`), com filtros como `AnoReferencia`, `CodigoMunicipio` e `CpfCnpj`. Se a API cair ou bloquear, salvar respostas manualmente em `data/raw/pe/` e o conector lê delas (mesmo hash, mesma proveniência). **Pagamentos só existem para municípios**; para o estado, usar empenho e liquidação. Detalhes e mapeamento em `docs/catalogo-fontes.md` |
| PNCP | `pncp` | API REST pública, sem autenticação | **Sem sobreposição com o TCE-PE:** PE vem só do `pe_portal`; o PNCP carrega as outras UFs (AL na demo). Se o `pe_portal` falhar, `PNCP_PE_FALLBACK=true` carrega PE pelo PNCP. Ler a especificação OpenAPI em `https://pncp.gov.br/api/consulta/v3/api-docs` antes de codificar. Rotas podem dar 404 intermitente: retry com backoff e cache em disco |
| CEIS e CNEP | `ceis`, `cnep` | Download de dados abertos do Portal da Transparência (ou API com chave) | O portal tem firewall que bloqueia clientes HTTP. Fallback: download manual para `data/raw/sancoes/` |
| Quadro societário | `receita_qsa` | Consulta por CNPJ (por exemplo, Minha Receita) | Opcional. Consultar **apenas** fornecedores das carteiras e empresas sancionadas das UFs carregadas. Até 1 requisição por segundo, com cache |
| Sintético de demo | `demo_sintetico` | Seed | Rotulado como sintético em todas as telas |

Regras da pipeline:
1. **Bronze:** todo arquivo ou resposta vai para `data/raw/<fonte>/<data>/` e para `arquivos_brutos` com sha256. Mesmo hash não reprocessa.
2. **Normalização:** mapeamento campo a campo documentado em `docs/catalogo-fontes.md`. Descartar favorecido pessoa física. Normalizar CNPJ, datas e valores.
3. **Qualidade:** completude, duplicidade, datas fora de faixa e queda de volume maior que 50% em relação à execução anterior (marca a execução como `parcial` e não apaga nada).
4. **Execuções** sempre registradas em `execucoes_ingestao`, com contagens e erro.
5. **Fixtures:** cada conector salva uma amostra pequena em `data/fixtures/<fonte>/`, usada nos testes e na demo offline. Para o `pe_portal`, quem tem IP brasileiro roda `ingest pe_portal --amostra 200` e comita o resultado; os agentes de nuvem só consomem a fixture.
6. **Mapeamento do TCE-PE (hipótese até a amostra real; ajustar com ela):** contrato → `contratos`; empenho/liquidação → `pagamentos` (`id_origem` prefixado `emp:` ou `liq:`, tipo no campo `descricao`); unidade gestora ou município → `orgaos` (`esfera` estadual ou municipal); `CpfCnpj` com 11 dígitos → descartado e contado em `registros_descartados`. `uf` é sempre `PE`. Contratos de municípios do agreste (Garanhuns incluído) servem de caso local na demo.

## 11. API

Contrato congelado em `contracts/api.md`. Resumo:

`POST /auth/login` · `GET /me` · `GET /health` · `GET /fontes` · `GET /fontes/execucoes` · `POST /carteiras` · `GET /carteiras` · `GET /carteiras/{id}/fila` · `GET /fornecedores/{cnpj}/dossie` · `POST /consultas` · `GET /consultas` · `GET /recibos/{id}` · `GET /recibos/{id}/verificar` · `GET /alertas` · `GET /auditoria` · `GET /auditoria/verificar` · `GET /metricas`

Erros sempre no formato `{"erro": {"codigo": "...", "mensagem": "...", "request_id": "..."}}`.

## 12. Frontend

Telas, em ordem de prioridade:

1. **Login** com seletor rápido dos usuários de demo (só em modo demo).
2. **Consulta**: campo de pergunta, perguntas sugeridas, resposta com números destacados, lista de citações clicáveis e botão "ver recibo". **É a tela central da demo.**
3. **Recibo**: plano, parâmetros, linhas usadas, fontes com data de coleta, hash e selo "íntegro" ou "alterado" vindo de `/recibos/{id}/verificar`.
4. **Carteira e fila**: upload ou colagem de CNPJs, fila priorizada, sinais com explicação.
5. **Dossiê do fornecedor**: uma página com resumo, contratos vigentes, vencimentos, sanções e sinais, cada item com fonte.
6. **Auditoria** (auditor e admin): eventos, filtros e selo da cadeia íntegra.
7. **Fontes**: execuções, contagens, hash e data de coleta.
8. **Métricas**: resultados do `eval/`.

Requisitos: contraste AA, navegação por teclado, rótulos em campos, valores por extenso em leitor de tela, nada dependente só de cor. Banner fixo em dados sintéticos.

## 13. Segurança e LGPD

- Segredos só em `.env` (fora do git). `.env.example` versionado.
- Só dados públicos ou sintéticos. Nenhum dado real sensível.
- Sócio pessoa física: guardar só a chave hash e a exibição mascarada (`J*** S*** (CPF ***.456.789-**)`).
- Logs sem token, senha, chave de API ou prompt completo com dado de terceiros.
- CORS restrito à origem do frontend. Rate limit simples por usuário em `/consultas` (30 por minuto).
- Modelo de ameaças em `docs/modelo-ameacas.md` (OWASP Top 10 para LLM como referência).

## 14. Avaliação e testes

### 14.1 Gabarito (`eval/gabarito/perguntas.yaml`)

100 perguntas com `id`, `pergunta`, `usuario`, `intent_esperada`, `comportamento` (`responder`, `abster`, `esclarecer`, `negar`) e **`sql_referencia` escrito à parte**, por outra pessoa ou outro agente que não o autor do catálogo. O harness executa o SQL de referência e compara com o resultado do sistema.

Métricas: acerto de intent, acerto de resultado, citação correta, abstenção correta e taxa de fallback do verificador.

### 14.2 Ataques (`eval/ataques/ataques.yaml`)

50 casos: injeção direta, injeção armazenada (fornecedor envenenado), pedido de outra UF, pedido de outro tenant, IDOR, tentativa de extrair o prompt, SQL no parâmetro, CNPJ inválido, pergunta enorme. Métrica: % bloqueado e nº de vazamentos (meta: **zero vazamento**).

### 14.3 Matriz de acesso

Os 8 casos do §6.4, em pytest, rodando contra o banco real em container.

### 14.4 Pipeline

Idempotência (rodar duas vezes não muda contagens), contrato de cada fonte com a fixture, descarte de pessoa física, queda de volume.

### 14.5 Resiliência

LLM fora do ar (demo continua), fonte fora do ar (ingestão marca falha e não apaga dados), reinício da API no meio da consulta.

### 14.6 Metas

Zero vazamento entre UFs e tenants; ≥ 90% de acerto de intent; 100% das respostas com recibo íntegro; ≥ 95% dos ataques bloqueados; P95 da consulta abaixo de 10 s com LLM e abaixo de 2 s sem.

## 15. Premissas e riscos

**Premissas:** a API do PNCP segue respondendo (testada em 05/11); a API de dados abertos do TCE-PE responde (aberta no navegador pela equipe em 06/11; os nomes dos endpoints e campos ainda dependem da amostra); o portal do Governo de PE não oferece download, por isso não é a fonte; dados públicos podem ser reprocessados para fins de diligência, respeitando a LGPD.

**Riscos:** API do TCE-PE restrita a IP brasileiro (mitigação: ingestão só na máquina da equipe, fixtures para os agentes, respostas salvas à mão como plano B); duplicidade de contratos entre TCE-PE e PNCP (mitigação: PE só pelo TCE-PE); firewall do Portal da Transparência bloqueando CEIS/CNEP (mitigação: download manual); limite da API de quadro societário (mitigação: escopo restrito e cache); LLM fora do ar na demo (mitigação: mock e fallback determinístico).
