# frontend/ — interface

Vite + React 18 + TypeScript (`strict`), TanStack Query, React Router 6 e Tailwind.

```
npm install
npm run dev        # http://localhost:5173 (ou make up)
npm test           # vitest + Testing Library, sem rede (ou make test-web)
npm run lint       # tsc --noEmit
```

## Variáveis (`VITE_*`, no Compose ou em `frontend/.env.local`)

| Variável | Padrão | Para quê |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Base da API |
| `VITE_DEMO_MODE` | `false` | Mostra o seletor rápido dos usuários do seed no login (o Compose lê `DEMO_MODE` do `.env`) |
| `VITE_CONSULTAS_SIMULADAS` | `false` | Responde `POST /consultas` com dados fictícios enquanto a T11 não existe. A tela sempre avisa "resposta simulada". **Desligar na demo** |

Sem a T11 e com `VITE_CONSULTAS_SIMULADAS=false`, a consulta mostra o erro real da API (501, "Consulta ainda não implementada.").

## Estrutura

```
src/
  main.tsx              # monta sessão → http → api e a árvore de provedores
  App.tsx               # rotas; tela nova = uma <Route> dentro do Layout + uma página em pages/
  Provedores.tsx        # QueryClient + ApiProvider + AuthProvider (o mesmo nos testes)
  api/
    types.ts            # espelha contracts/api.md; mudou o contrato, muda só aqui
    http.ts             # fetch com token, erro do contrato → ErroApi, 401 com token → sessão perdida
    index.ts            # interface Api (auth, consultas) e criarApi(); telas só usam useApi()
    ApiProvider.tsx
    adaptadores/        # consultasSimuladas.ts (provisório até a T11)
  auth/                 # sessao.ts (token em sessionStorage), AuthProvider, RotaProtegida, permissoes (§6.2)
  config/               # ambiente.ts (VITE_*), demo.ts (usuários do seed)
  features/consulta/    # hook, formulário, sugestões, texto com destaques, citações, resultado
  components/           # Cabecalho, MensagemErro, SeloSintetico, Carregando
  lib/                  # destaques.ts (valores e [n] no texto), extenso.ts (leitor de tela), formato.ts
  pages/                # LoginPage, ConsultaPage, ReciboPage (destino do "Ver recibo"; tela completa na T22)
  testes/               # montar.tsx (Api falsa + app em memória), fluxo.test.tsx
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
