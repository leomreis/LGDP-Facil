import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getScan } from '../api/scans';
import { fetchReportPdf, getReportByScan } from '../api/reports';
import { createPolicyDocument } from '../api/policyDocuments';
import type { PolicyDocumentType, Report, ScanDetail } from '../types/api';
import { ScanStatusBadge } from '../components/scan/ScanStatusBadge';
import { RiskBadge } from '../components/scan/RiskBadge';
import { Button } from '../components/ui/Button';
import { downloadBlob } from '../lib/downloadBlob';

const POLL_INTERVAL_MS = 4000;

export function ScanDetailPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [gerandoDocumento, setGerandoDocumento] = useState<PolicyDocumentType | null>(null);
  const [baixandoPdf, setBaixandoPdf] = useState(false);

  const carregar = useCallback(async () => {
    if (!scanId) return;
    const [scanAtualizado, relatorio] = await Promise.all([
      getScan(scanId),
      getReportByScan(scanId),
    ]);
    setScan(scanAtualizado);
    setReport(relatorio);
  }, [scanId]);

  useEffect(() => {
    carregar().catch((e) => setErro(e instanceof Error ? e.message : 'Erro ao carregar o scan.'));
  }, [carregar]);

  // Enquanto o scan roda em background no servidor, a única forma de saber que
  // terminou é perguntar de novo — não há WebSocket nesta versão.
  useEffect(() => {
    if (!scan || scan.status === 'completed' || scan.status === 'failed') return;

    const intervalId = setInterval(() => {
      carregar().catch(() => undefined);
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [scan, carregar]);

  async function baixarPdf() {
    if (!scanId) return;
    setBaixandoPdf(true);
    setErro(null);
    try {
      const blob = await fetchReportPdf(scanId);
      downloadBlob(blob, `relatorio-${scanId}.pdf`);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível baixar o PDF.');
    } finally {
      setBaixandoPdf(false);
    }
  }

  async function gerarDocumento(tipo: PolicyDocumentType) {
    if (!scanId) return;
    setGerandoDocumento(tipo);
    setErro(null);
    try {
      await createPolicyDocument(tipo, scanId);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível gerar o documento.');
    } finally {
      setGerandoDocumento(null);
    }
  }

  if (erro) return <p className="text-danger">{erro}</p>;
  if (!scan) return <p className="text-text-muted">Carregando...</p>;

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <h1 className="truncate text-2xl font-semibold">{scan.url}</h1>
        <ScanStatusBadge status={scan.status} />
      </div>

      {(scan.status === 'pending' || scan.status === 'in_progress') && (
        <p className="mb-6 text-text-muted">O scan está rodando. Esta página atualiza sozinha.</p>
      )}

      {scan.status === 'failed' && (
        <p className="mb-6 text-danger">O scan falhou. Tente rodar novamente.</p>
      )}

      {report && (
        <section className="mb-6 rounded-xl border border-border bg-surface p-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Relatório de conformidade</h2>
            <Button
              variant="secondary"
              type="button"
              disabled={baixandoPdf}
              onClick={() => void baixarPdf()}
            >
              {baixandoPdf ? 'Gerando PDF...' : 'Baixar PDF'}
            </Button>
          </div>
          <p className="mb-3 text-2xl font-bold">{report.score_conformidade} / 100</p>
          <p className="whitespace-pre-wrap leading-relaxed text-text">{report.resumo_executivo}</p>
        </section>
      )}

      {scan.status === 'completed' && (
        <section className="mb-6">
          <h2 className="mb-3 text-lg font-semibold">Gerar documentos a partir deste scan</h2>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              type="button"
              disabled={gerandoDocumento !== null}
              onClick={() => void gerarDocumento('privacy_policy')}
            >
              {gerandoDocumento === 'privacy_policy'
                ? 'Gerando...'
                : 'Gerar política de privacidade'}
            </Button>
            <Button
              variant="secondary"
              type="button"
              disabled={gerandoDocumento !== null}
              onClick={() => void gerarDocumento('cookie_notice')}
            >
              {gerandoDocumento === 'cookie_notice' ? 'Gerando...' : 'Gerar aviso de cookies'}
            </Button>
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">Achados ({scan.findings.length})</h2>
        {scan.findings.length === 0 && scan.status === 'completed' && (
          <p className="text-text-muted">Nenhum dado pessoal encontrado neste scan.</p>
        )}
        <ul className="flex flex-col gap-2">
          {scan.findings.map((finding) => (
            <li
              key={finding.id}
              className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3"
            >
              <RiskBadge risk={finding.risk} />
              <span className="font-medium">{finding.categoria_dado_pessoal}</span>
              <span className="truncate text-sm text-text-muted">{finding.location}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
