import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/supabase', () => ({
  supabase: { auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) } },
}));

import { fetchReportPdf, getReportByScan } from './reports';

function respostaFalsa(body: unknown, status: number) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response;
}

describe('getReportByScan', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('devolve o relatório quando existe', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({ id: 'r1', score_conformidade: 80 }, 200));

    const relatorio = await getReportByScan('scan-1');

    expect(relatorio?.id).toBe('r1');
  });

  it('devolve null quando o relatório ainda não existe (404) — não é erro', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({ detail: 'não encontrado' }, 404));

    const relatorio = await getReportByScan('scan-1');

    expect(relatorio).toBeNull();
  });

  it('propaga outros erros (ex.: 500) em vez de engolir', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({ detail: 'erro interno' }, 500));

    await expect(getReportByScan('scan-1')).rejects.toMatchObject({ status: 500 });
  });
});

describe('fetchReportPdf', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('devolve o blob em resposta de sucesso', async () => {
    const blobFalso = new Blob(['%PDF-fake']);
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(blobFalso),
    } as unknown as Response);

    const blob = await fetchReportPdf('scan-1');

    expect(blob).toBe(blobFalso);
  });

  it('lança ApiError quando a resposta não é ok', async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false, status: 404 } as Response);

    await expect(fetchReportPdf('scan-1')).rejects.toMatchObject({ status: 404 });
  });
});
