import { useId, useState, type FormEvent } from "react";

import { LIMITE_PERGUNTA } from "../../api/types";

interface Props {
  sugestoes: string[];
  enviando: boolean;
  aoEnviar(pergunta: string): void;
}

export function FormularioConsulta({ sugestoes, enviando, aoEnviar }: Props) {
  const [pergunta, setPergunta] = useState("");
  const idCampo = useId();
  const idAjuda = useId();
  const limpa = pergunta.trim();

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (limpa && !enviando) aoEnviar(limpa);
  }

  return (
    <form onSubmit={enviar} className="space-y-3" aria-busy={enviando}>
      <label htmlFor={idCampo} className="block text-base font-semibold text-slate-900">
        Sua pergunta
      </label>
      <textarea
        id={idCampo}
        aria-describedby={idAjuda}
        value={pergunta}
        maxLength={LIMITE_PERGUNTA}
        rows={3}
        onChange={(e) => setPergunta(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) enviar(e);
        }}
        className="w-full rounded-md border border-slate-500 p-3 text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700"
        placeholder="Ex.: Quais contratos do CNPJ 99.999.999/0001-91 vencem nos próximos 6 meses?"
      />
      <div id={idAjuda} className="flex justify-between text-sm text-slate-700">
        <span>Ctrl+Enter envia. Responde só com dados das fontes que você pode ver.</span>
        <span>
          {pergunta.length}/{LIMITE_PERGUNTA}
        </span>
      </div>
      <button
        type="submit"
        disabled={!limpa || enviando}
        className="rounded-md bg-blue-800 px-4 py-2 font-semibold text-white hover:bg-blue-900 disabled:cursor-not-allowed disabled:bg-slate-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
      >
        {enviando ? "Consultando…" : "Perguntar"}
      </button>

      <fieldset className="pt-2">
        <legend className="text-sm font-semibold text-slate-800">Perguntas sugeridas</legend>
        <ul className="mt-2 flex flex-col gap-2">
          {sugestoes.map((s) => (
            <li key={s}>
              <button
                type="button"
                onClick={() => setPergunta(s)}
                className="w-full rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-left text-sm text-slate-900 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700"
              >
                {s}
              </button>
            </li>
          ))}
        </ul>
      </fieldset>
    </form>
  );
}
