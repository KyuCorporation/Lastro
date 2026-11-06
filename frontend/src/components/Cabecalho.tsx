import { useAuth } from "../auth/AuthProvider";

const NOME_PERFIL = { analista: "Analista", gestor: "Gestor", auditor: "Auditor", admin: "Administrador" } as const;

export function Cabecalho() {
  const { usuario, sair } = useAuth();
  return (
    <header className="border-b border-slate-300 bg-white">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <p className="text-lg font-bold text-slate-900">
          Lastro <span className="font-normal text-slate-600">· radar de fornecedores, com recibo</span>
        </p>
        {usuario && (
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-800">
            <span>
              {usuario.nome} · {NOME_PERFIL[usuario.perfil]} · {usuario.tenant.nome}
            </span>
            <span aria-label={`Estados autorizados: ${usuario.ufs.join(", ")}`}>
              UFs: <strong>{usuario.ufs.join(", ")}</strong>
            </span>
            <button
              type="button"
              onClick={sair}
              className="rounded-md border border-slate-500 px-3 py-1 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700"
            >
              Sair
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
