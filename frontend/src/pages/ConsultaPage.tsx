import { useAuth } from "../auth/AuthProvider";
import { pode } from "../auth/permissoes";
import { MensagemErro } from "../components/MensagemErro";
import { ambiente } from "../config/ambiente";
import { FormularioConsulta } from "../features/consulta/FormularioConsulta";
import { ResultadoConsulta } from "../features/consulta/ResultadoConsulta";
import { negacaoComoResultado } from "../features/consulta/negacao";
import { sugestoesPara } from "../features/consulta/perguntasSugeridas";
import { useCriarConsulta } from "../features/consulta/useCriarConsulta";

/** Tela central da demo (SPEC §12, item 2). */
export function ConsultaPage({ simulado = ambiente.consultasSimuladas }: { simulado?: boolean }) {
  const { usuario } = useAuth();
  const consulta = useCriarConsulta();
  if (!usuario) return null;
  const negacao = consulta.isError ? negacaoComoResultado(consulta.error) : null;

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Consulta</h1>
        <p className="text-slate-700">
          Pergunte em português sobre contratos, pagamentos e sanções de um fornecedor. Cada número vem de uma fonte
          oficial citada, e a consulta fica registrada.
        </p>
      </div>

      {pode(usuario.perfil, "consultar") ? (
        <FormularioConsulta
          sugestoes={sugestoesPara(usuario.ufs)}
          enviando={consulta.isPending}
          aoEnviar={(pergunta) => consulta.mutate({ pergunta })}
        />
      ) : (
        <p role="note" className="rounded-md border border-slate-400 bg-slate-50 p-4 text-slate-900">
          Seu perfil ({usuario.perfil}) não faz consultas em linguagem natural. Analistas e administradores fazem.
        </p>
      )}

      <div aria-live="polite">
        {negacao && <ResultadoConsulta resultado={negacao} simulado={false} />}
        {consulta.isError && !negacao && (
          <MensagemErro erro={consulta.error} titulo="A consulta não foi concluída" />
        )}
        {consulta.data && <ResultadoConsulta resultado={consulta.data} simulado={simulado} />}
      </div>
    </main>
  );
}
