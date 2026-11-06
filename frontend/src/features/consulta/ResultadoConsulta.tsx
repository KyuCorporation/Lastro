import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";

import type { ConsultaSaida, StatusConsulta } from "../../api/types";
import { SeloSintetico } from "../../components/SeloSintetico";
import { ListaCitacoes } from "./ListaCitacoes";
import { TextoResposta } from "./TextoResposta";

// Cada status tem título e cor próprios, mas o título sempre diz o estado em texto (nada só por cor).
const APRESENTACAO: Record<StatusConsulta, { titulo: string; classe: string }> = {
  respondida: { titulo: "Resposta", classe: "border-slate-300 bg-white" },
  abstencao: { titulo: "Sem registros nas fontes autorizadas", classe: "border-slate-400 bg-slate-50" },
  esclarecimento: { titulo: "Preciso de um detalhe", classe: "border-blue-700 bg-blue-50" },
  negada: { titulo: "Acesso negado", classe: "border-red-700 bg-red-50" },
  erro: { titulo: "Não foi possível responder", classe: "border-red-700 bg-red-50" },
};

interface Props {
  resultado: ConsultaSaida;
  simulado: boolean;
}

export function ResultadoConsulta({ resultado, simulado }: Props) {
  const titulo = useRef<HTMLHeadingElement>(null);
  const { titulo: textoTitulo, classe } = APRESENTACAO[resultado.status] ?? APRESENTACAO.erro;
  const idCitacao = (n: number) => `citacao-${resultado.consulta_id}-${n}`;

  // Leva o foco para a resposta: quem usa teclado ou leitor de tela chega direto nela.
  useEffect(() => titulo.current?.focus(), [resultado.consulta_id]);

  return (
    <section aria-labelledby="titulo-resultado" className={`rounded-lg border-2 p-5 ${classe}`}>
      <h2 id="titulo-resultado" ref={titulo} tabIndex={-1} className="mb-3 text-xl font-bold text-slate-900">
        {textoTitulo}
      </h2>
      {(resultado.sintetico || simulado) && (
        <div className="mb-3">
          <SeloSintetico simulado={simulado} />
        </div>
      )}
      <TextoResposta texto={resultado.resposta} idCitacao={idCitacao} />
      <ListaCitacoes citacoes={resultado.citacoes} idCitacao={idCitacao} />
      {resultado.recibo_id && (
        <p className="mt-6">
          <Link
            to={`/recibos/${resultado.recibo_id}`}
            className="inline-block rounded-md border-2 border-blue-800 px-4 py-2 font-semibold text-blue-900 hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
          >
            Ver recibo
          </Link>
        </p>
      )}
    </section>
  );
}
