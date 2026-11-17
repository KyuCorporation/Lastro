import type { ReactNode } from "react";

import { urlSegura } from "../lib/formato";

/**
 * Link para o registro na fonte oficial. Só abre http/https (`url_origem` vem de fonte externa). Sem URL pública,
 * mostra `semLink` ou, por padrão, o próprio texto seguido de "sem link público".
 */
export function LinkOrigem({
  url,
  children,
  semLink,
}: {
  url: string | null | undefined;
  children: ReactNode;
  semLink?: ReactNode;
}) {
  const segura = urlSegura(url);
  if (!segura) {
    return <span className="text-kyu-suave">{semLink ?? <>{children} · sem link público</>}</span>;
  }
  return (
    <a href={segura} target="_blank" rel="noopener noreferrer" className="foco font-semibold text-kyu-laranja underline">
      {children}
      <span className="sr-only"> (abre a fonte oficial em nova aba)</span>
    </a>
  );
}
