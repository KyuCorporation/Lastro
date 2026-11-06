import type { ReactNode } from "react";

import type { Tom } from "../lib/apresentacao";

const CLASSES: Record<Tom, string> = {
  verde: "bg-kyu-verde-fundo text-kyu-verde",
  vermelho: "bg-kyu-vermelho-fundo text-kyu-vermelho",
  ambar: "bg-kyu-ambar-fundo text-kyu-ambar",
  neutro: "bg-kyu-cabecalho text-kyu-suave",
};

/** Etiqueta de estado (verde, vermelho, âmbar). O texto diz o estado; a cor só reforça. */
export function Selo({ tom, children }: { tom: Tom; children: ReactNode }) {
  return (
    <span className={`inline-block rounded-md px-3 py-1 text-sm font-semibold ${CLASSES[tom]}`}>{children}</span>
  );
}

/** Ponto colorido + texto, como na coluna "Resultado" da auditoria. */
export function Indicador({ tom, children }: { tom: Tom; children: ReactNode }) {
  const cor = { verde: "bg-kyu-verde", vermelho: "bg-kyu-vermelho", ambar: "bg-kyu-ambar", neutro: "bg-kyu-suave" }[
    tom
  ];
  const texto = { verde: "text-kyu-verde", vermelho: "text-kyu-vermelho", ambar: "text-kyu-ambar", neutro: "" }[tom];
  return (
    <span className={`inline-flex items-center gap-2 font-semibold ${texto}`}>
      <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${cor}`} />
      {children}
    </span>
  );
}
