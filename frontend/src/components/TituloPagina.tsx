import type { ReactNode } from "react";

/** Título das telas, com a frase que explica para que a tela serve. */
export function TituloPagina({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <div className="mb-6">
      <h1 className="text-3xl font-bold text-kyu-texto sm:text-4xl">
        {titulo}
      </h1>
      {children && <p className="mt-3 text-lg text-kyu-suave">{children}</p>}
    </div>
  );
}
