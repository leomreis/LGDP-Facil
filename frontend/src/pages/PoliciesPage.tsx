import { useEffect, useState } from 'react';
import { listPolicyDocuments, updatePolicyDocumentStatus } from '../api/policyDocuments';
import type { PolicyDocument } from '../types/api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

const TIPO_LABEL: Record<PolicyDocument['tipo'], string> = {
  privacy_policy: 'Política de Privacidade',
  terms_of_use: 'Termos de Uso',
  cookie_notice: 'Aviso de Cookies',
};

export function PoliciesPage() {
  const [documentos, setDocumentos] = useState<PolicyDocument[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [selecionado, setSelecionado] = useState<PolicyDocument | null>(null);

  async function carregar() {
    setDocumentos(await listPolicyDocuments());
  }

  useEffect(() => {
    carregar().catch((e) =>
      setErro(e instanceof Error ? e.message : 'Erro ao carregar documentos.'),
    );
  }, []);

  async function publicar(documento: PolicyDocument) {
    try {
      await updatePolicyDocumentStatus(documento.id, 'published');
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível publicar o documento.');
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold">Políticas e avisos</h1>
      <p className="mb-6 text-text-muted">Documentos são gerados a partir de um scan concluído.</p>

      {erro && <p className="mb-4 text-sm text-danger">{erro}</p>}
      {documentos === null && <p className="text-text-muted">Carregando...</p>}
      {documentos !== null && documentos.length === 0 && (
        <p className="text-text-muted">
          Nenhum documento gerado ainda. Vá até um scan concluído para gerar um.
        </p>
      )}

      <div className="grid grid-cols-[260px_1fr] gap-6">
        <ul className="flex flex-col gap-2">
          {documentos?.map((documento) => (
            <li
              key={documento.id}
              className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2"
            >
              <button
                type="button"
                onClick={() => setSelecionado(documento)}
                className="flex-1 text-left text-sm text-text hover:text-primary"
              >
                {TIPO_LABEL[documento.tipo]} · {documento.version}
              </button>
              <Badge tone={documento.status === 'published' ? 'success' : 'warning'}>
                {documento.status === 'published' ? 'Publicado' : 'Rascunho'}
              </Badge>
            </li>
          ))}
        </ul>

        {selecionado && (
          <article className="rounded-xl border border-border bg-surface p-6">
            <header className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                {TIPO_LABEL[selecionado.tipo]} · {selecionado.version}
              </h2>
              {selecionado.status === 'draft' && (
                <Button type="button" onClick={() => void publicar(selecionado)}>
                  Publicar
                </Button>
              )}
            </header>
            <pre className="whitespace-pre-wrap font-sans leading-relaxed text-text">
              {selecionado.content}
            </pre>
          </article>
        )}
      </div>
    </div>
  );
}
