import { useAuth } from "../auth/AuthProvider";
import { pode } from "../auth/permissoes";
import { Selo } from "../components/Selo";
import { TituloPagina } from "../components/TituloPagina";
import { NOME_PERFIL, nomesUfs } from "../lib/apresentacao";

// Espelha o SPEC §6.2. Só apresenta: quem decide é o backend (403 auditado) e a RLS no banco.
const MATRIZ = [
  { perfil: "Analista de risco", consulta: "Consultar dados autorizados", auditoria: "Próprias consultas" },
  { perfil: "Gestor de contrato", consulta: "Não faz consultas; vê dossiê e fila", auditoria: "Sem acesso" },
  { perfil: "Auditor", consulta: "Não faz consultas; confere recibos", auditoria: "Consultas e auditoria do cliente" },
  { perfil: "Administrador", consulta: "Consultar dados autorizados", auditoria: "Consultas e auditoria do cliente" },
];

/** Tela 03 do design: controle de acesso por perfil. */
export function AcessoPage() {
  const { usuario } = useAuth();
  if (!usuario) return null;
  const consulta = pode(usuario.perfil, "consultar");
  const ufs = usuario.ufs.map((uf) => uf).join(", ");

  return (
    <div className="space-y-6">
      <TituloPagina numero="03" titulo="Controle de acesso por perfil">
        A autorização é validada no servidor antes que a consulta alcance a IA.
      </TituloPagina>

      <div className="grid gap-5 lg:grid-cols-2">
        <section aria-labelledby="titulo-sessao" className="cartao p-6">
          <h2 id="titulo-sessao" className="text-xl font-bold text-kyu-texto">
            Sessão atual
          </h2>
          <p className="mt-3">
            <Selo tom="verde">Acesso ativo</Selo>
          </p>
          <p className="mt-4 text-2xl font-bold text-kyu-texto">{NOME_PERFIL[usuario.perfil]}</p>
          <p className="mt-3 text-lg text-kyu-texto">
            Estado{usuario.ufs.length > 1 ? "s" : ""} autorizado{usuario.ufs.length > 1 ? "s" : ""}:{" "}
            {nomesUfs(usuario.ufs)} ({ufs})
          </p>
          <p className="mt-4 text-kyu-suave">
            {consulta
              ? "Pode consultar registros públicos dentro do escopo."
              : "Vê os dados do escopo, mas não faz consultas em linguagem natural."}{" "}
            Cliente: {usuario.tenant.nome}.
          </p>
        </section>

        <section aria-labelledby="titulo-fora" className="cartao p-6">
          <h2 id="titulo-fora" className="text-xl font-bold text-kyu-texto">
            Tentativa fora do escopo
          </h2>
          <p className="mt-3">
            <Selo tom="vermelho">Acesso negado</Selo>
          </p>
          <p className="mt-4 text-2xl font-bold text-kyu-texto">Consulta para outro estado</p>
          <p className="mt-3 text-lg text-kyu-texto">O perfil atual não possui autorização para esse escopo.</p>
          <p className="mt-4 text-kyu-suave">
            A busca é interrompida antes da recuperação de dados. A negação não diz quantos registros existem fora do
            escopo e fica registrada na auditoria.
          </p>
        </section>
      </div>

      <section aria-labelledby="titulo-matriz" className="cartao p-6">
        <h2 id="titulo-matriz" className="text-xl font-bold text-kyu-texto">
          Matriz de permissões
        </h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[40rem] border-collapse text-left">
            <caption className="sr-only">O que cada perfil pode fazer</caption>
            <thead className="tabela-cabecalho">
              <tr>
                <th scope="col" className="rounded-l-md px-4 py-3">Perfil</th>
                <th scope="col" className="px-4 py-3">Escopo estadual</th>
                <th scope="col" className="px-4 py-3">Consulta</th>
                <th scope="col" className="rounded-r-md px-4 py-3">Auditoria</th>
              </tr>
            </thead>
            <tbody>
              {MATRIZ.map((linha) => {
                const atual = linha.perfil === NOME_PERFIL[usuario.perfil];
                return (
                  <tr key={linha.perfil} className={`border-b border-kyu-linha ${atual ? "bg-kyu-creme" : ""}`}>
                    <th scope="row" className="px-4 py-5 font-bold">
                      {linha.perfil}
                      {atual && <span className="ml-2 text-sm font-semibold text-kyu-verde">(você)</span>}
                    </th>
                    <td className="px-4 py-5">Só os estados do próprio usuário</td>
                    <td className="px-4 py-5">{linha.consulta}</td>
                    <td className="px-4 py-5">{linha.auditoria}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-6 font-semibold text-kyu-vermelho">
          A interface apenas apresenta permissões; a regra efetiva é aplicada e testada no backend.
        </p>
      </section>
    </div>
  );
}
