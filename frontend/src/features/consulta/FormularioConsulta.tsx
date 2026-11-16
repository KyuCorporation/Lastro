import { useId, useState, type FormEvent } from "react";

import { LIMITE_PERGUNTA, type CarteiraListada } from "../../api/types";
import { NOME_FINALIDADE } from "../../lib/apresentacao";

interface Props {
  sugestoes: string[];
  enviando: boolean;
  aoEnviar(pergunta: string, carteiraId?: string): void;
  /** Carteiras do cliente: a escolhida vai como contexto (carteira_id) e fica registrada no recibo. */
  carteiras?: CarteiraListada[];
  carteiraInicial?: string;
  perguntaInicial?: string;
}

/** Cartão da pergunta (tela 01): campo em linguagem natural e o botão "Consultar". */
export function FormularioConsulta({
  sugestoes,
  enviando,
  aoEnviar,
  carteiras = [],
  carteiraInicial = "",
  perguntaInicial = "",
}: Props) {
  const [pergunta, setPergunta] = useState(perguntaInicial);
  const [carteira, setCarteira] = useState(carteiraInicial);
  const idCampo = useId();
  const idAjuda = useId();
  const idContexto = useId();
  const limpa = pergunta.trim();

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (limpa && !enviando) aoEnviar(limpa, carteira || undefined);
  }

  return (
    <form onSubmit={enviar} className="cartao p-5" aria-busy={enviando}>
      {carteiras.length > 0 && (
        <div className="mb-4 border-b border-kyu-linha pb-4">
          <label htmlFor={idContexto} className="block text-sm font-semibold text-kyu-suave">
            Contexto da consulta
          </label>
          <select
            id={idContexto}
            value={carteira}
            onChange={(e) => setCarteira(e.target.value)}
            className="foco mt-1 w-full rounded-md border border-kyu-borda bg-white px-3 py-2 text-kyu-texto md:w-auto md:min-w-80"
          >
            <option value="">Sem carteira</option>
            {carteiras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome} · {NOME_FINALIDADE[c.finalidade] ?? c.finalidade}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="flex-1">
          <label htmlFor={idCampo} className="block text-sm font-semibold text-kyu-suave">
            Pergunta em linguagem natural
          </label>
          <textarea
            id={idCampo}
            aria-describedby={idAjuda}
            value={pergunta}
            maxLength={LIMITE_PERGUNTA}
            rows={1}
            onChange={(e) => setPergunta(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) enviar(e);
            }}
            className="foco mt-1 w-full resize-none rounded-md border border-transparent bg-transparent py-1 text-lg text-kyu-texto [field-sizing:content] placeholder:text-kyu-suave hover:border-kyu-borda"
            placeholder="Ex.: Quais contratos do CNPJ 99.000.001/0001-01 vencem nos próximos 6 meses?"
          />
        </div>
        <button type="submit" disabled={!limpa || enviando} className="botao-primario md:min-w-44">
          {enviando ? "Consultando…" : "Consultar"}
        </button>
      </div>
      <div id={idAjuda} className="mt-2 flex flex-wrap justify-between gap-2 text-sm text-kyu-suave">
        <span>Ctrl+Enter envia. Informe o CNPJ do fornecedor. A resposta usa só as fontes que você pode ver.</span>
        <span>
          {pergunta.length}/{LIMITE_PERGUNTA}
        </span>
      </div>

      {sugestoes.length > 0 && (
        <fieldset className="mt-4 border-t border-kyu-linha pt-4">
          <legend className="sr-only">Perguntas sugeridas</legend>
          <p aria-hidden="true" className="text-sm font-semibold text-kyu-suave">
            Perguntas sugeridas
          </p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {sugestoes.map((s) => (
              <li key={s}>
                <button
                  type="button"
                  onClick={() => setPergunta(s)}
                  className="foco rounded-md border border-kyu-borda bg-kyu-creme px-3 py-1.5 text-left text-sm text-kyu-texto hover:border-kyu-laranja"
                >
                  {s}
                </button>
              </li>
            ))}
          </ul>
        </fieldset>
      )}
    </form>
  );
}
