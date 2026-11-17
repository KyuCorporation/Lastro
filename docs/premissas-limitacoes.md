# Premissas, limitações, riscos e próximos passos

Situação do código em 08/11/2026.

## Premissas

- Dados públicos de contratações e sanções podem ser coletados e reprocessados para diligência, respeitando a LGPD: só pessoa jurídica, sem CPF, sócio pessoa física apenas mascarado.
- O PNCP continua respondendo pela API pública. A coleta real de 06/11 trouxe contratos de PE e AL.
- O CEIS e o CNEP continuam publicando o arquivo diário. Se o firewall bloquear o cliente HTTP, o zip baixado à mão entra pelo mesmo conector.
- A API de dados abertos do TCE-PE responde a IP brasileiro com o formato descrito em `docs/catalogo-fontes.md`, conferido na API real em 15/11/2026.
- O cliente-alvo (consultoria de risco de fornecedores) trabalha por carteira de CNPJs, com finalidade (homologação, monitoramento, renovação) e acesso por estado.

## Limitações conhecidas

**Dados**
- O conector do TCE-PE foi conferido na API real e tem amostra real (`data/fixtures/pe_portal/amostra`), mas a carga completa (`make ingest-pe`) ainda não foi feita. Despesa municipal só entra para os municípios de `TCEPE_MUNICIPIOS`. Uma unidade gestora estadual com mais de 100 mil empenhos ou liquidações no ano não pode ser coletada inteira (limite da API); ainda não foi medido se alguma chega a isso.
- A situação do contrato do TCE-PE (`Situacao`) só existe nas linhas coletadas depois da migration 009. A fixture `amostra/` foi gerada antes e não traz o campo: até `ingest pe_portal --amostra 200` em rede brasileira, a demo trata todos os contratos da amostra como regulares. Na coleta de 15/11/2026, 35 de 7.294 contratos com data final no futuro estavam concluídos, rescindidos ou suspensos (R$ 20,8 milhões).
- O link de cada contrato do TCE-PE (`LinkArquivo`) é `http`, não `https`, e não foi conferido se abre de fora do Brasil. A fixture `amostra/` foi gerada antes de o campo entrar e só passa a tê-lo depois de `ingest pe_portal --amostra 200` em rede brasileira; até lá, os contratos da amostra apontam para o recorte da API.
- No `pe_portal`, o bronze guarda a resposta já sem dado de pessoa física (LGPD). O `sha256` é o da resposta saneada, não o dos bytes que a fonte mandou.
- Não há conector de quadro societário. A tabela `socios` fica vazia, então o dossiê mostra "Nenhum sócio" e o sinal de contágio não existe.
- Sanção que sai do CEIS ou do CNEP só é marcada como retirada (`removida_em`) numa coleta online completa com status `ok`. A demo carrega fixtures offline, que são recortes, então nela nenhuma sanção aparece como retirada. Entre os arquivos do CEIS de 05/11 e 17/11/2026, 375 sanções de PJ saíram do cadastro, 56 delas ainda vigentes pela data.
- A ingestão roda por comando (`make ingest-*`, `make sinais`), sem agendamento. Os sinais refletem a última vez que alguém rodou `sinais`.
- "Hoje" é o dia em Pernambuco (UTC−3) na API e na pipeline. As views de `db/migrations/003_views.sql` usam `current_date` do banco, que roda em UTC; o catálogo não usa essas views.

**Consultas**
- O catálogo cobre 8 intents. `socios_sancionados` está no contrato do plano, mas vira abstenção ("ainda não está disponível").
- A finalidade da carteira (homologação, monitoramento, renovação) fica no recibo, mas ainda não muda a resposta de `fila_carteira`.
- Perguntas fora do catálogo não são respondidas. Isso é deliberado (ADR-002), mas limita o que a pessoa pode perguntar.
- A finalidade da carteira entra no recibo, mas não muda a resposta.
- A busca por objeto ignora acento dos dois lados (`busca_objeto@v2`) e roda sem índice, o que basta no volume da demo; o índice sem acento depende de migration (extensão `unaccent`). Sem acento, palavras diferentes podem cair no mesmo radical: "médica" e "medicamentos" viram "medic".
- No modo `mock` (sem LLM), o planejador é um roteador por regras e o texto vem de modelos fixos por intent. As respostas ficam corretas e citadas, porém mais engessadas.

**Plataforma**
- O alerta nasce quando alguém cria a carteira ou abre a fila depois de um novo cálculo de sinais, não no instante do cálculo: a pipeline não escreve em dados de tenant. O status do alerta só avança (aberto, visto, resolvido) e cada mudança entra na auditoria.
- O limite de 30 consultas por minuto fica na memória do processo da API.
- O JWT vale 480 minutos e não tem revogação no servidor.
- A auditoria registra o login que deu certo. Tentativa com senha errada não entra: a trilha é por tenant e, sem sessão, não há tenant.
- A tela do recibo procura a âncora na trilha entre as 500 respostas e as 500 abstenções mais recentes do tenant (teto de `GET /auditoria`). Recibo mais antigo aparece como "âncora não localizada", sem acusar alteração. Busca direta por recibo (`?recibo_id=`) depende de mudança de contrato.

**Avaliação**
- As 59 perguntas `responder` do gabarito têm `sql_referencia` escrita sem acesso ao SQL do catálogo (SPEC §14.1). As divergências que restam são de leitura (empenho citado à parte, prazo padrão de 180 dias, "dinheiro" como valor contratado) e estão em `docs/relatorio-avaliacao.md`.
- O gabarito só rodou sem LLM (`mock`). Com o Gemini, só a suíte de ataques rodou, em 16/11, antes do teto de tempo da consulta. A tela de métricas mostra os dois provedores lado a lado quando os dois relatórios existem (`make eval EVAL_LLM=gemini`).
- O cronômetro de diligência (T23) ainda não foi medido.

## Riscos

| Risco | Efeito | Mitigação no código |
|---|---|---|
| Formato do TCE-PE mudar | Conector quebra na coleta | Teste de contrato marcado `@pytest.mark.rede`; a falha fica registrada em `execucoes_ingestao` sem apagar dados |
| Contratos duplicados entre TCE-PE e PNCP | Valor de PE contado duas vezes | O PNCP só grava PE se `PNCP_PE_FALLBACK` estiver ligado (`test_pncp_nao_grava_pe_sem_fallback`) |
| Provedor de LLM fora do ar ou lento | Consulta demorada ou sem texto | Planejador por regras e modelo determinístico; uma chamada só ao provedor quando ele cai |
| Fonte bloqueando o acesso | Dados desatualizados | Sem contorno; download manual pelo mesmo conector |
| Texto malicioso dentro do dado público | Resposta manipulada | Marcadores, verificador e evento `ataque_detectado` (ver `modelo-ameacas.md`) |

## Próximos passos

1. Fazer a primeira carga completa do TCE-PE em rede brasileira (`make ingest-pe`) e medir o volume por unidade gestora.
2. Implementar o SQL de `socios_sancionados`, e o conector de quadro societário com o sinal de contágio.
3. Medir o cronômetro com 3 CNPJs e validar a hipótese com especialistas (T23).
4. Rodar `make eval EVAL_LLM=gemini` e `make eval-ataques EVAL_LLM=gemini` e publicar os números ao lado dos do modo `mock`.
