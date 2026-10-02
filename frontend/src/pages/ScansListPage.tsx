import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { createScan, listScans } from '../api/scans';
import type { Scan } from '../types/api';
import { ScanStatusBadge } from '../components/scan/ScanStatusBadge';
import { Button } from '../components/ui/Button';

export function ScansListPage() {
  const [scans, setScans] = useState<Scan[] | null>(null);
  const [url, setUrl] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function carregar() {
    const lista = await listScans();
    setScans(lista);
  }

  useEffect(() => {
    carregar().catch((e) => setErro(e instanceof Error ? e.message : 'Erro ao carregar scans.'));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await createScan(url);
      setUrl('');
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível iniciar o scan.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Scans</h1>

      <form onSubmit={(event) => void handleSubmit(event)} className="mb-6 flex gap-2">
        <label htmlFor="url" className="sr-only">
          URL do site
        </label>
        <input
          id="url"
          type="url"
          placeholder="https://seusite.com.br"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          required
          className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-muted focus:border-primary focus:outline-none"
        />
        <Button type="submit" disabled={enviando}>
          {enviando ? 'Iniciando...' : 'Rodar novo scan'}
        </Button>
      </form>

      {erro && <p className="mb-4 text-sm text-danger">{erro}</p>}

      {scans === null && <p className="text-text-muted">Carregando...</p>}
      {scans !== null && scans.length === 0 && (
        <p className="text-text-muted">
          Nenhum scan ainda. Informe a URL do seu site acima para começar.
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {scans?.map((scan) => (
          <li
            key={scan.id}
            className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3"
          >
            <Link to={`/scans/${scan.id}`} className="flex-1 truncate text-primary hover:underline">
              {scan.url}
            </Link>
            <ScanStatusBadge status={scan.status} />
          </li>
        ))}
      </ul>
    </div>
  );
}
