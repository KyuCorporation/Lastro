import { useId } from "react";

import type { ConteudoRecibo } from "../../api/types";
import { valoresDaResposta } from "../recibo/leitura";

/** Cada valor da resposta ao lado do que ele significa, com o rótulo escrito pelo código (nunca pela IA). */
export function ValoresDaResposta({ conteudo }: { conteudo: ConteudoRecibo }) {
  const id = useId();
  const valores = valoresDaResposta(conteudo);
  if (valores.length === 0) return null;
  return (
    <section aria-labelledby={id} className="mt-5 rounded-lg border border-kyu-linha p-4">
      <h3 id={id} className="text-sm font-semibold text-kyu-suave">
        Valores usados na resposta
      </h3>
      <p className="mt-1 text-sm text-kyu-suave">
        Inseridos pelo sistema a partir dos registros. A IA não escreve números.
      </p>
      <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-[minmax(0,1fr)_max-content]">
        {valores.map((v) => (
          <div key={v.marcador} className="contents">
            <dt className="text-kyu-texto">{v.rotulo}</dt>
            <dd className="font-bold text-kyu-texto sm:text-right">{v.texto}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
