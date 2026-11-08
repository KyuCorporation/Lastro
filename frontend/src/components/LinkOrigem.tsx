import type { ReactNode } from "react";

import { urlSegura } from "../lib/formato";

/** Link para o registro na fonte oficial. Sem URL pública (ou fora de http/https), mostra só o texto. */
export function LinkOrigem({ url, children }: { url: string | null | undefined; children: ReactNode }) {
  const segura = urlSegura(url);
  if (!segura) {
    return (
      <span className="text-kyu-suave">
        {children} · sem link público
      </span>
    );
  }
  return (
    <a href={segura} target="_blank" rel="noopener noreferrer" className="foco font-semibold text-kyu-laranja underline">
      {children}
      <span className="sr-only"> (abre a fonte oficial em nova aba)</span>
    </a>
  );
}
