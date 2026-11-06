# frontend/ — interface

Vite + React 18 + TypeScript (`strict`), TanStack Query, React Router 6 e Tailwind. Visual e telas seguem o design
da KYU (marca, cores e as 5 telas numeradas).

## Telas

| Tela | Rota | Dados |
|---|---|---|
| Login | `/login` | `POST /auth/login`; seletor de usuários do seed com `VITE_DEMO_MODE=true` |
| 01 Consulta inteligente | `/` | `POST /consultas`; valor, resumo e "Integridade da consulta" lidos do recibo (`GET /recibos/{id}`). "Teste de segurança" manda o pedido de ataque para a API real e mostra o que ela decidiu |
| 02 Recibo de evidências | `/recibos/:id` | `GET /recibos/{id}`: valor, registros de origem com link, totais com a origem do cálculo, selo sha256 |
| 03 Controle de acesso | `/acesso` | Sessão de `GET /me`; matriz do SPEC §6.2 (só apresenta) |
| 04 Auditoria de consultas | `/auditoria` | `GET /consultas` (o que a RLS mostra), com filtros. Gestor não vê o item no menu: a API responderia 403 |
| 05 Fonte e catálogo | `/fontes` | Conteúdo de `docs/catalogo-fontes.md`, sem contagens (`GET /fontes` ainda não existe) |

Cores em `tailwind.config.js` (`kyu-*`), classes comuns em `src/index.css` (`cartao`, `botao-primario`, `foco`),
marca em `src/components/LogoKyu.tsx` e `public/favicon.svg`.

```
npm install
npm run dev        # http://localhost:5173 (ou make up)
npm test           # vitest + Testing Library, sem rede (ou make test-web)
npm run lint       # tsc --noEmit (app e e2e)
npm run e2e        # Playwright no navegador da máquina contra o sistema de pé (make demo)
E2E_CANAL=msedge npm run e2e          # sem Google Chrome, usa o Edge
npx tsx e2e/capturas.ts <pasta>       # capturas das 5 telas no tamanho dos mockups, para comparar com o design
```

## Variáveis (`VITE_*`, no Compose ou em `frontend/.env.local`)

| Variável | Padrão | Para quê |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Base da API |
| `VITE_DEMO_MODE` | `false` | Mostra o seletor rápido dos usuários do seed no login (o Compose lê `DEMO_MODE` do `.env`) |
| `VITE_CONSULTAS_SIMULADAS` | `false` | Responde `POST /consultas` com dados fictícios, só para desenvolver a tela sem backend. A tela avisa "resposta simulada". **Desligado na demo** |

## Estrutura

```
src/
  main.tsx              # monta sessão → http → api e a árvore de provedores
  App.tsx               # rotas; tela nova = uma <Route> dentro do Layout + uma página em pages/
  Provedores.tsx        # QueryClient + ApiProvider + AuthProvider (o mesmo nos testes)
  api/
    types.ts            # espelha contracts/api.md; mudou o contrato, muda só aqui
    http.ts             # fetch com token, erro do contrato → ErroApi, 401 com token → sessão perdida
    index.ts            # interface Api (auth, consultas, recibos) e criarApi(); telas só usam useApi()
    ApiProvider.tsx
    adaptadores/        # consultasSimuladas.ts (desenvolvimento sem backend)
  auth/                 # sessao.ts (token em sessionStorage), AuthProvider, RotaProtegida, permissoes (§6.2)
  config/               # ambiente.ts (VITE_*), demo.ts (usuários do seed)
  features/consulta/    # hook, formulário, sugestões, texto com destaques, citações, resultado, integridade, teste de segurança
  features/recibo/      # useRecibo (GET /recibos/{id}) e leitura.ts (valor principal, período, fontes)
  components/           # Moldura (lateral + topo), LogoKyu, Selo, TituloPagina, MensagemErro, SeloSintetico, Carregando
  lib/                  # destaques.ts, extenso.ts (leitor de tela), formato.ts, apresentacao.ts (rótulos de perfil, UF, status)
  pages/                # Login, Consulta, Recibo, Acesso, Auditoria, Fontes
  testes/               # montar.tsx (Api falsa + app em memória), fluxo.test.tsx, telas.test.tsx
```

Endpoint novo: tipo em `api/types.ts` → função em `api/index.ts` (campo novo em `Api`) → hook em
`features/<tela>/` → página. A tela nunca chama `fetch` direto, então os testes injetam uma `Api` falsa.

## Regras

- O escopo de acesso vem só do backend. `auth/permissoes.ts` só decide o que mostrar (ex.: gestor não vê o
  formulário de consulta); quem barra é a API.
- Números da resposta já chegam inseridos pelo backend. A tela só destaca: moeda e data são lidas por extenso no
  leitor de tela; `[n]` no texto leva à fonte `n` da lista de citações.
- Datas ISO da API viram dd/mm/aaaa na tela. Dado sintético sempre com selo.
- Acessibilidade AA, teclado (Ctrl+Enter envia a pergunta, foco vai para a resposta), rótulo em todo campo, nada
  só por cor. Texto de sinal: "sinal para investigar". Nunca "fraude", "irregular", "suspeito".
