# Premissas, limitações, riscos e próximos passos

Situação do código em 08/11/2026.

## Premissas

- Dados públicos de contratações e sanções podem ser coletados e reprocessados para diligência, respeitando a LGPD: só pessoa jurídica, sem CPF, sócio pessoa física apenas mascarado.
- O PNCP continua respondendo pela API pública. A coleta real de 06/11 trouxe contratos de PE e AL.
- O CEIS e o CNEP continuam publicando o arquivo diário. Se o firewall bloquear o cliente HTTP, o zip baixado à mão entra pelo mesmo conector.
- A API de dados abertos do TCE-PE responde a IP brasileiro com o formato descrito em `docs/catalogo-fontes.md`. Esse formato ainda precisa ser confirmado com uma amostra real.
- O cliente-alvo (consultoria de risco de fornecedores) trabalha por carteira de CNPJs, com finalidade (homologação, monitoramento, renovação) e acesso por estado.

## Limitações conhecidas

**Dados**
- O conector do TCE-PE foi testado só com uma fixture feita à mão (`exemplo_manual`). Na base atual, os contratos de PE vêm do PNCP, e empenhos e liquidações de PE ainda não foram carregados de verdade. Falta rodar `ingest pe_portal --amostra 200` numa rede brasileira.
- Não há conector de quadro societário. A tabela `socios` fica vazia, então o dossiê mostra "Nenhum sócio" e o sinal de contágio não existe.
- A ingestão roda por comando (`make ingest-*`, `make sinais`), sem agendamento. Os sinais refletem a última vez que alguém rodou `sinais`.

**Consultas**
- O catálogo cobre 7 intents. `fila_carteira` e `socios_sancionados` estão no contrato do plano, mas viram abstenção ("ainda não está disponível").
- Perguntas fora do catálogo não são respondidas. Isso é deliberado (ADR-002), mas limita o que a pessoa pode perguntar.
- A finalidade da carteira entra no recibo, mas não muda a resposta.
- No modo `mock` (sem LLM), o planejador é um roteador por regras e o texto vem de modelos fixos por intent. As respostas ficam corretas e citadas, porém mais engessadas.

**Plataforma**
- Nenhum processo cria alertas: `GET /alertas` existe, mas a tabela só recebe linhas nos testes.
- O limite de 30 consultas por minuto fica na memória do processo da API.
- O JWT vale 480 minutos e não tem revogação no servidor.
- A auditoria não registra o login (o schema prevê o evento `login`).

**Avaliação**
- Das 100 perguntas do gabarito, só a G001 tem `sql_referencia` escrita por alguém fora do catálogo (SPEC §14.1). As outras conferem intent, comportamento e citação, mas não o valor contra uma consulta independente.
- Os números do gabarito e dos ataques na tela de métricas foram gerados com `LLM_PROVIDER=mock`. Com o Gemini, é preciso rodar `make eval` de novo.
- O cronômetro de diligência (T23) ainda não foi medido.

## Riscos

| Risco | Efeito | Mitigação no código |
|---|---|---|
| Formato real do TCE-PE diferente do documentado | Conector quebra na primeira coleta real | Teste de contrato marcado `@pytest.mark.rede`; a falha fica registrada em `execucoes_ingestao` sem apagar dados |
| Contratos duplicados entre TCE-PE e PNCP | Valor de PE contado duas vezes | O PNCP só grava PE se `PNCP_PE_FALLBACK` estiver ligado (`test_pncp_nao_grava_pe_sem_fallback`) |
| Provedor de LLM fora do ar ou lento | Consulta demorada ou sem texto | Planejador por regras e modelo determinístico; uma chamada só ao provedor quando ele cai |
| Fonte bloqueando o acesso | Dados desatualizados | Sem contorno; download manual pelo mesmo conector |
| Texto malicioso dentro do dado público | Resposta manipulada | Marcadores, verificador e evento `ataque_detectado` (ver `modelo-ameacas.md`) |

## Próximos passos

1. Coletar a amostra real do TCE-PE em rede brasileira, ajustar o conector se o formato diferir e trocar a fixture `exemplo_manual` pela `amostra`.
2. Fazer alguém de fora do catálogo escrever `sql_referencia` para o gabarito, para a métrica de resultado medir de verdade.
3. Implementar o SQL de `fila_carteira` e `socios_sancionados`, e o conector de quadro societário com o sinal de contágio.
4. Criar alertas quando uma nova sanção ou sinal atingir fornecedor de carteira.
5. Medir o cronômetro com 3 CNPJs e validar a hipótese com especialistas (T23).
6. Rodar `make eval` e `make eval-ataques` com o Gemini e publicar os números ao lado dos do modo `mock`.
