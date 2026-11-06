/** Marca KYU: losango laranja com a lupa-alfinete. Decorativa quando acompanha o nome escrito. */
export function MarcaKyu({ tamanho = 32, titulo }: { tamanho?: number; titulo?: string }) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 64 64"
      role={titulo ? "img" : undefined}
      aria-hidden={titulo ? undefined : true}
      aria-label={titulo}
      focusable="false"
    >
      <rect x="10" y="10" width="44" height="44" rx="9" transform="rotate(45 32 32)" className="fill-kyu-marca" />
      <circle cx="32" cy="25" r="9" fill="none" strokeWidth="4.5" className="stroke-kyu-escuro" />
      <circle cx="32" cy="25" r="2.6" className="fill-kyu-escuro" />
      <path d="M32 34 V47" strokeWidth="4.5" strokeLinecap="round" className="stroke-kyu-escuro" />
    </svg>
  );
}

/** Marca + nome, como na lateral do design. */
export function LogoKyu({ claro = true }: { claro?: boolean }) {
  return (
    <span className="inline-flex items-center gap-3">
      <MarcaKyu tamanho={36} />
      <span className={`text-2xl font-extrabold tracking-wide ${claro ? "text-white" : "text-kyu-escuro"}`}>KYU</span>
    </span>
  );
}
