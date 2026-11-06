// Guarda do token. sessionStorage: some ao fechar a aba e não é compartilhado entre abas.
// O escopo de acesso nunca vem daqui: quem decide é o backend, pela sessão (AGENTS.md §3.3).

const CHAVE = "lastro.token";

export interface ArmazenamentoToken {
  ler(): string | null;
  gravar(token: string): void;
  apagar(): void;
}

export function armazenamentoSessao(storage: Storage | undefined = globalThis.sessionStorage): ArmazenamentoToken {
  let emMemoria: string | null = null;
  return {
    ler() {
      try {
        return storage?.getItem(CHAVE) ?? emMemoria;
      } catch {
        return emMemoria;
      }
    },
    gravar(token) {
      emMemoria = token;
      try {
        storage?.setItem(CHAVE, token);
      } catch {
        // navegação privada ou storage bloqueado: fica só em memória
      }
    },
    apagar() {
      emMemoria = null;
      try {
        storage?.removeItem(CHAVE);
      } catch {
        // idem
      }
    },
  };
}

/** Ponte entre o cliente HTTP (que vê o 401) e o AuthProvider (que faz logout). */
export interface Sessao {
  token: ArmazenamentoToken;
  aoPerder(ouvinte: () => void): () => void;
  perder(): void;
}

export function criarSessao(token: ArmazenamentoToken = armazenamentoSessao()): Sessao {
  const ouvintes = new Set<() => void>();
  return {
    token,
    aoPerder(ouvinte) {
      ouvintes.add(ouvinte);
      return () => {
        ouvintes.delete(ouvinte);
      };
    },
    perder() {
      token.apagar();
      ouvintes.forEach((ouvinte) => ouvinte());
    },
  };
}
