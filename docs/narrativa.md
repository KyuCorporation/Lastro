# O Lastro em uma história

> Personagens e números desta história são fictícios. Ela descreve o produto como está desenhado no `SPEC.md`.

## O que é

Imagine um **cartório inteligente** que serve a quem precisa saber, rápido e com prova, com quem uma empresa faz negócio.

Marina trabalha numa consultoria de gestão de terceiros. Um cliente entrega a ela 40 fornecedores para checar. Antes, para cada um, ela abria quatro sites do governo, juntava contratos, pagamentos e sanções numa planilha e gastava meia hora. Agora ela cola a lista de CNPJs e, na manhã seguinte, encontra uma **fila**: no topo está a empresa que tem o contrato mais valioso acabando em 60 dias e depende de uma única prefeitura. Cada item da fila traz "sinal para investigar", nunca "fraude". A decisão continua sendo da Marina.

## Por quê

Os dados públicos existem, mas estão espalhados em prédios diferentes, cada um com seu jeito de arquivar. E uma IA que responde sem mostrar de onde tirou a informação não serve para compliance: ninguém assina embaixo de um "confia em mim". O desafio pede exatamente isto: reunir os dados, controlar quem vê o quê, e deixar a IA falar só do que o usuário pode ver, com o registro de tudo.

## Como funciona, no cartório

- **O malote.** Um estafeta (a pipeline) vai buscar cópias nos arquivos oficiais: o Tribunal de Contas de Pernambuco, o PNCP e as listas de sanções. Ele tira cópia autenticada (o hash) e etiqueta cada pasta com a origem e a data. Pessoa física é deixada de fora.
- **O arquivo com portas.** Tudo vai para um arquivo único. As portas se abrem pelo **crachá** de quem pergunta: estado, perfil e cliente. Quem tranca é o prédio (o banco de dados), não o atendente. Se o crachá é de Pernambuco, a pasta de Alagoas nem existe para aquela pessoa.
- **A recepcionista.** Marina pergunta em português. A recepcionista (a IA planejadora) só preenche uma **ficha de pedido** num formulário fixo, com os tipos de consulta que o cartório aceita. Ela nunca entra no arquivo.
- **O arquivista.** O código recebe a ficha, usa o crachá da Marina e traz só as pastas que ela pode ver.
- **O escrivão na sala fechada.** Outro redator (a IA de resposta) recebe cópias das pastas e escreve o texto **deixando lacunas** no lugar dos números (`{{v1}}`). Quem preenche as lacunas é o carimbo, ou seja, o código. A IA nunca inventa um valor. Se uma pasta tiver um bilhete dizendo "ignore as regras", o escrivão o trata como papel, não como ordem.
- **O conferente.** Antes de entregar, um conferente verifica se todo número do texto está nas pastas. Se não estiver, a resposta cai num texto padrão, sem IA.
- **O protocolo.** Cada resposta sai com um **recibo**: quais pastas foram usadas, de qual fonte, coletadas quando, e um selo. Qualquer pessoa pode recalcular o selo e saber se o recibo foi alterado.
- **O livro de registro.** Tudo fica anotado num livro de folhas costuradas: cada folha carrega o selo da anterior. Arrancar ou trocar uma página quebra a costura.
