import { useAuth } from "../auth/AuthProvider";
import { pode } from "../auth/permissoes";
import { MensagemErro } from "../components/MensagemErro";
import { TituloPagina } from "../components/TituloPagina";
import { ambiente } from "../config/ambiente";
import { FormularioConsulta } from "../features/consulta/FormularioConsulta";
import { ResultadoConsulta } from "../features/consulta/ResultadoConsulta";
import { TesteSeguranca } from "../features/consulta/TesteSeguranca";
import { negacaoComoResultado } from "../features/consulta/negacao";
import { sugestoesPara } from "../features/consulta/perguntasSugeridas";
import { useCriarConsulta } from "../features/consulta/useCriarConsulta";
import { useRecibo } from "../features/recibo/useRecibo";
import { NOME_PERFIL } from "../lib/apresentacao";

/** Tela 01 do design: consulta inteligente (SPEC §12, item 2). */
export function ConsultaPage({ simulado = ambiente.consultasSimuladas }: { simulado?: boolean }) {
  const { usuario } = useAuth();
  const consulta = useCriarConsulta();
  const recibo = useRecibo(consulta.data?.recibo_id);
  if (!usuario) return null;
  const negacao = consulta.isError ? negacaoComoResultado(consulta.error) : null;
  const consulta_permitida = pode(usuario.perfil, "consultar");

  return (
    <div className="space-y-6">
      <TituloPagina numero="01" titulo="Consulta inteligente">
        Pesquise contratos, pagamentos e sanções de fornecedores nas bases públicas do TCE-PE, do PNCP e do CEIS/CNEP.
      </TituloPagina>

      {consulta_permitida ? (
        <FormularioConsulta
          sugestoes={sugestoesPara(usuario.ufs)}
          enviando={consulta.isPending}
          aoEnviar={(pergunta) => consulta.mutate({ pergunta })}
        />
      ) : (
        <p role="note" className="cartao p-5 text-kyu-texto">
          Seu perfil ({NOME_PERFIL[usuario.perfil]}) não faz consultas em linguagem natural. Analistas e
          administradores fazem.
        </p>
      )}

      <div aria-live="polite">
        {negacao && <ResultadoConsulta resultado={negacao} simulado={false} ufs={usuario.ufs} />}
        {consulta.isError && !negacao && <MensagemErro erro={consulta.error} titulo="A consulta não foi concluída" />}
        {consulta.data && (
          <ResultadoConsulta resultado={consulta.data} simulado={simulado} recibo={recibo.data} ufs={usuario.ufs} />
        )}
      </div>

      {consulta_permitida && !simulado && <TesteSeguranca />}
    </div>
  );
}
