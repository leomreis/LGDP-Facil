import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getPublicPolicyDocument, tipoFromSlug } from '../api/publicPolicies';
import { ApiError } from '../api/client';
import type { PolicyDocumentType, PublicPolicyDocument } from '../types/api';

const TITULO: Record<PolicyDocumentType, string> = {
  privacy_policy: 'Política de Privacidade',
  terms_of_use: 'Termos de Uso',
  cookie_notice: 'Aviso de Cookies',
};

/** Página aberta a qualquer visitante — fora do AuthProvider/AppShell, sem
 * navegação do app: quem chega aqui é cliente da PME, não usuário nosso. */
export function PublicPolicyPage() {
  const { companyId, slug } = useParams<{ companyId: string; slug: string }>();
  const tipo = tipoFromSlug(slug);
  const [documento, setDocumento] = useState<PublicPolicyDocument | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId || !tipo) return;
    getPublicPolicyDocument(companyId, tipo)
      .then((doc) => {
        setDocumento(doc);
        document.title = `${TITULO[doc.tipo]} · ${doc.company_name}`;
      })
      .catch((e) =>
        setErro(
          e instanceof ApiError && (e.status === 404 || e.status === 422)
            ? 'Documento não encontrado.'
            : 'Não foi possível carregar o documento agora.',
        ),
      );
  }, [companyId, tipo]);

  const mensagem = !tipo ? 'Documento não encontrado.' : erro;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      {mensagem && <p className="text-text-muted">{mensagem}</p>}
      {!mensagem && !documento && <p className="text-text-muted">Carregando...</p>}
      {documento && (
        <article>
          <header className="mb-8 border-b border-border pb-4">
            <p className="text-sm text-text-muted">{documento.company_name}</p>
            <h1 className="text-2xl font-semibold">{TITULO[documento.tipo]}</h1>
            <p className="text-sm text-text-muted">
              Versão {documento.version}
              {documento.created_at &&
                ` · ${new Date(documento.created_at).toLocaleDateString('pt-BR')}`}
            </p>
          </header>
          <pre className="whitespace-pre-wrap font-sans leading-relaxed text-text">
            {documento.content}
          </pre>
        </article>
      )}
    </main>
  );
}
