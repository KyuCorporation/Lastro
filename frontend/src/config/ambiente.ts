// Configuração lida das variáveis VITE_* (definidas no Compose ou em frontend/.env.local).

function booleano(valor: string | undefined): boolean {
  return valor === "true" || valor === "1";
}

export interface Ambiente {
  /** Base da API (contracts/api.md). */
  apiUrl: string;
  /** Modo demo: mostra o seletor rápido dos usuários do seed na tela de login. */
  demo: boolean;
}

export const ambiente: Ambiente = {
  apiUrl: (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, ""),
  demo: booleano(import.meta.env.VITE_DEMO_MODE),
};

/** Flags do React Router 6 que adiantam o comportamento da v7 (mesmas no app e nos testes). */
export const FUTURO_ROUTER = { v7_startTransition: true, v7_relativeSplatPath: true } as const;
