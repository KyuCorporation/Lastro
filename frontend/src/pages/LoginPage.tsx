import { useId, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { MensagemErro } from "../components/MensagemErro";
import { ambiente } from "../config/ambiente";
import { SENHA_SEED_DEMO, USUARIOS_DEMO } from "../config/demo";

interface EstadoNavegacao {
  de?: string;
  motivo?: "expirou" | "saiu";
}

const CLASSE_CAMPO =
  "mt-1 w-full rounded-md border border-slate-500 p-2 text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700";

export function LoginPage({ demo = ambiente.demo }: { demo?: boolean }) {
  const { estado, entrar } = useAuth();
  const navegar = useNavigate();
  const local = useLocation();
  const destino = (local.state as EstadoNavegacao | null)?.de ?? "/";
  const motivo = (local.state as EstadoNavegacao | null)?.motivo;
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);
  const idEmail = useId();
  const idSenha = useId();

  if (estado.status === "autenticado") return <Navigate to={destino} replace />;

  async function autenticar(credenciais: { email: string; senha: string }) {
    setEnviando(true);
    setErro(null);
    try {
      await entrar(credenciais);
      navegar(destino, { replace: true });
    } catch (e) {
      setErro(e);
    } finally {
      setEnviando(false);
    }
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    void autenticar({ email: email.trim(), senha });
  }

  return (
    <main className="mx-auto max-w-md px-4 py-10">
      <h1 className="text-2xl font-bold text-slate-900">Entrar no Lastro</h1>
      <p className="mt-1 text-slate-700">Radar de risco de fornecedores, com recibo.</p>

      {motivo === "expirou" && (
        <p role="status" className="mt-4 rounded-md border border-slate-400 bg-slate-50 p-3 text-slate-900">
          Sua sessão expirou. Entre novamente.
        </p>
      )}

      <form onSubmit={enviar} className="mt-6 space-y-4" aria-busy={enviando}>
        <div>
          <label htmlFor={idEmail} className="block font-semibold text-slate-900">
            E-mail
          </label>
          <input
            id={idEmail}
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={CLASSE_CAMPO}
          />
        </div>
        <div>
          <label htmlFor={idSenha} className="block font-semibold text-slate-900">
            Senha
          </label>
          <input
            id={idSenha}
            type="password"
            autoComplete="current-password"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            className={CLASSE_CAMPO}
          />
        </div>
        {erro !== null && <MensagemErro erro={erro} titulo="Não foi possível entrar" />}
        <button
          type="submit"
          disabled={enviando}
          className="w-full rounded-md bg-blue-800 px-4 py-2 font-semibold text-white hover:bg-blue-900 disabled:bg-slate-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
        >
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </form>

      {demo && (
        <section aria-labelledby="titulo-demo" className="mt-8 rounded-md border-2 border-dashed border-amber-700 p-4">
          <h2 id="titulo-demo" className="font-semibold text-slate-900">
            Usuários de demonstração
          </h2>
          <p className="text-sm text-slate-700">Modo demo: entra com o usuário do seed de desenvolvimento.</p>
          <ul className="mt-3 space-y-2">
            {USUARIOS_DEMO.map((u) => (
              <li key={u.email}>
                <button
                  type="button"
                  disabled={enviando}
                  onClick={() => void autenticar({ email: u.email, senha: SENHA_SEED_DEMO })}
                  className="w-full rounded-md border border-slate-400 px-3 py-2 text-left text-sm text-slate-900 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700"
                >
                  <strong>{u.nome}</strong> · {u.perfil} · {u.tenant} · UFs {u.ufs.join(", ")}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
