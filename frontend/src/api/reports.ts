import { API_BASE_URL, apiFetch, ApiError, getAccessToken } from './client';
import type { Report } from '../types/api';

/** null quando o relatório ainda não existe (scan em andamento) — não é erro. */
export async function getReportByScan(scanId: string): Promise<Report | null> {
  try {
    return await apiFetch<Report>(`/reports/scan/${scanId}`);
  } catch (erro) {
    if (erro instanceof ApiError && erro.status === 404) {
      return null;
    }
    throw erro;
  }
}

/**
 * Baixa o PDF do relatório e devolve os bytes. Não usa apiFetch porque a
 * resposta é binária, não JSON — quem chama decide o que fazer com o Blob
 * (neste app, sempre disparar o download no navegador).
 */
export async function fetchReportPdf(scanId: string): Promise<Blob> {
  const token = await getAccessToken();
  const headers = new Headers();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/reports/scan/${scanId}/pdf`, { headers });

  if (!response.ok) {
    throw new ApiError(response.status, 'Não foi possível baixar o PDF do relatório.');
  }

  return response.blob();
}
