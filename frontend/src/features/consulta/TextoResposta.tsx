import { Fragment, useMemo } from "react";

import { dividirEmTrechos } from "../../lib/destaques";

/** Texto da resposta com valores destacados e lidos por extenso no leitor de tela. */
export function TextoResposta({ texto }: { texto: string }) {
  const trechos = useMemo(() => dividirEmTrechos(texto), [texto]);
  return (
    <p className="text-xl font-semibold leading-relaxed text-kyu-texto">
      {trechos.map((t, i) => {
        switch (t.tipo) {
          case "moeda":
          case "data":
            return (
              <mark key={i} className="bg-transparent font-bold text-kyu-texto">
                <span aria-hidden="true">{t.texto}</span>
                <span className="sr-only">{t.falado}</span>
              </mark>
            );
          case "numero":
            return (
              <mark key={i} className="bg-transparent font-bold text-kyu-texto">
                {t.texto}
              </mark>
            );
          default:
            return <Fragment key={i}>{t.texto}</Fragment>;
        }
      })}
    </p>
  );
}
