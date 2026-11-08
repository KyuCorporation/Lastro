# Relatório de avaliação

Duas partes:
- **Resultados automáticos:** gerados pelo `eval/` e conferidos por qualquer pessoa com `make eval` e `make eval-ataques`.
- **Avaliação com pessoas (T23):** o cronômetro com 3 CNPJs e a validação da hipótese com 3 especialistas. Esta parte é feita pela equipe; o protocolo está abaixo, pronto para seguir, e os resultados entram nas tabelas marcadas "a preencher".

## 1. Resultados automáticos

Rodada de 08/11/2026 com `LLM_PROVIDER=mock`, sem LLM; o planejador é o roteador por regras. Com o Gemini, rodar de novo e registrar ao lado.

| Avaliação | Resultado | Meta (SPEC §14.6) |
|---|---|---|
| Gabarito: perguntas sem falha | 100 de 100 | — |
| Gabarito: acerto de intent | 100% (80 avaliadas) | ≥ 90% |
| Gabarito: citação correta | 100% (42 respostas) | — |
| Gabarito: resultado igual ao SQL de referência | 100% (só 1 pergunta tem SQL independente) | — |
| Ataques bloqueados | 58 de 58 (100%) | ≥ 95% |
| Vazamentos entre UFs ou tenants | 0 | zero |
| Matriz de acesso (`backend/app/tests/test_acesso.py`) | todos os casos do SPEC §6.4 passando | — |

A tela 08 Métricas mostra a rodada mais recente, lida de `eval/reports/`.

## 2. Cronômetro de diligência (T23)

**Pergunta:** quanto tempo um analista leva para levantar o histórico público de um fornecedor e decidir se ele exige diligência reforçada, com e sem o Lastro? A hipótese do SPEC §2 diz que, sem o Lastro, leva mais de 30 minutos.

### 2.1 Fornecedores

Os três são de Pernambuco, existem na base de 08/11/2026 e têm perfis diferentes:

| Código | CNPJ | Fornecedor | Por que foi escolhido |
|---|---|---|---|
| F1 | 08.778.201/0001-26 | DROGAFONTE LTDA | Sanções vigentes no CEIS e concentração em um órgão |
| F2 | 01.157.529/0001-86 | L E COMERCIO DE MATERIAIS DE INFORMATICA LTDA | Contrato vencendo em até 180 dias e concentração em um órgão |
| F3 | 32.137.518/0001-68 | ESTRELA COMUNICACAO GRAFICA EIRELI | 7 contratos vigentes, sem sinal e sem sanção (caso "limpo") |

Antes de começar, confira que os três continuam na base: abra o dossiê de cada um (`/fornecedores/<cnpj>`). Se algum tiver sumido depois de uma nova coleta, troque por outro com o mesmo perfil e registre a troca.

### 2.2 Tarefa (igual nas duas condições)

Para cada fornecedor, preencher as 5 respostas, cada uma com o link da fonte:

1. Quantos contratos vigentes ele tem em PE e qual o valor total?
2. Algum contrato termina nos próximos 180 dias? Qual valor?
3. Ele tem sanção vigente no CEIS ou no CNEP?
4. Qual órgão mais contrata com ele, e quanto isso representa do total?
5. Decisão: exige diligência reforçada? (sim/não, com uma frase de justificativa)

A tarefa termina quando as 5 respostas estão preenchidas com fonte. O limite é de 45 minutos por fornecedor; se estourar, registre "> 45" e o que faltou.

### 2.3 Condições

- **Com o Lastro:**
  - entrar como `ana@alfa.demo`;
  - usar a consulta (tela 01), o recibo (02) e o dossiê (07);
  - a fonte de cada resposta é o link do recibo ou do dossiê.
- **Sem o Lastro:**
  - só o navegador, sem assistente de IA;
  - fontes: [PNCP](https://pncp.gov.br), [Portal da Transparência](https://portaldatransparencia.gov.br) (busca de sanções do CEIS e do CNEP) e o portal do TCE-PE;
  - a fonte de cada resposta é o link da página onde o dado foi achado.

### 2.4 Ordem e participantes

- **Ideal: 2 participantes em ordem cruzada.**
  - P1 faz F1 e F2 sem o Lastro e F3 com o Lastro.
  - P2 faz o contrário.
  - Assim ninguém resolve o mesmo fornecedor duas vezes.
- **Mínimo: 1 participante, cada fornecedor primeiro com o Lastro e depois sem.**
  - Esse desenho é conservador. Na rodada manual o participante já conhece as respostas e termina mais rápido, então o tempo sem o Lastro sai menor do que seria na prática.
  - Se o Lastro ainda ganhar assim, o resultado é sólido. Registre que foi esse o desenho.
- **Perfil do participante:**
  - de preferência alguém que faz diligência de fornecedores e não participou do desenvolvimento;
  - se for da equipe, registre isso, porque quem construiu o Lastro usa a ferramenta mais rápido que um usuário novo.

### 2.5 Como medir

- Cronômetro do celular, iniciado ao abrir a primeira página e parado com a quinta resposta preenchida.
- Tempo em minutos, com uma casa decimal.
- **Conferência:** depois de tudo, compare cada resposta com o recibo do Lastro. Divergência não conta automaticamente como erro do participante: abra a fonte e registre quem estava certo e por quê.
  - Um caso esperado é contrato de PE que existe no PNCP e não no TCE-PE, ou o contrário.

### 2.6 Registro (a preencher)

| Participante | Fornecedor | Condição | Minutos | Respostas corretas (de 5) | Observações |
|---|---|---|---|---|---|
| | F1 | com | | | |
| | F1 | sem | | | |
| | F2 | com | | | |
| | F2 | sem | | | |
| | F3 | com | | | |
| | F3 | sem | | | |

**Resumo (a preencher):**
- mediana com o Lastro: __ min;
- mediana sem o Lastro: __ min;
- redução: __%;
- hipótese de mais de 30 min sem o Lastro: confirmada / refutada.

### 2.7 Levar o resultado para a tela de métricas

Grave `eval/reports/cronometro.json`, que fica fora do git como os outros relatórios. A API passa a mostrar os campos na tela 08, no bloco "Cronômetro de diligência":

```json
{
  "gerado_em": "2026-11-15T10:00:00-03:00",
  "modo": "cronometro",
  "provedor_llm": "gemini",
  "n_casos": 3,
  "metricas": {
    "mediana_sem_o_lastro_(min)": 0,
    "mediana_com_o_lastro_(min)": 0,
    "reducao_(%)": 0,
    "corretas_sem_o_lastro": "0 de 15",
    "corretas_com_o_lastro": "0 de 15",
    "participantes": "1, da equipe, ordem com → sem"
  }
}
```

A tela troca `_` por espaço e põe a primeira letra em maiúscula: `mediana_sem_o_lastro_(min)` aparece como "Mediana sem o lastro (min)".

## 3. Validação da hipótese com 3 especialistas (T23)

**Quem:** três pessoas que fazem ou contratam diligência de fornecedores (consultoria de gestão de terceiros, compliance, compras). Registre cargo e tipo de organização, não o nome, salvo se a pessoa autorizar.

**Formato:** conversa de 30 minutos, com demonstração de 10 minutos no meio.

**Roteiro:**

1. **Como você faz hoje** (antes de mostrar o Lastro):
   - Quando precisa levantar o histórico público de um fornecedor, por onde começa?
   - Quanto tempo leva, em média, por fornecedor? (anote o número que a pessoa disser antes de ouvir a hipótese)
   - O que mais toma tempo? O que já deu errado por falta de informação?
   - Você usaria uma resposta de IA num parecer de compliance? O que precisaria ter?
2. **Demonstração** (3 passos, com F1):
   - pergunta na consulta, depois o recibo com o selo de integridade;
   - carteira com F1, F2 e F3, depois a fila e o dossiê de F1;
   - pergunta pedindo dados de Alagoas, negada, depois o evento na auditoria (entrar como `caio@alfa.demo`, que é auditor).
3. **Depois de ver:**
   - O recibo serviria como evidência num parecer? O que falta nele?
   - Os sinais (sanção, vencimentos concentrados, concentração em um órgão) são os que você olha? Qual falta?
   - De 1 a 5, quanto isso reduziria o seu tempo por fornecedor? Por quê?
   - O que impediria você de usar no dia a dia?

### Registro (a preencher)

| Especialista | Cargo / organização | Tempo atual por fornecedor | Recibo serve como evidência? | Sinal que falta | Redução (1 a 5) | Principal objeção |
|---|---|---|---|---|---|---|
| E1 | | | | | | |
| E2 | | | | | | |
| E3 | | | | | | |

**Conclusão (a preencher):** a hipótese do SPEC §2 se confirma? O que muda no produto a partir das conversas?
