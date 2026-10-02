import { apiFetch } from './client';
import type { Scan, ScanDetail } from '../types/api';

export function listScans(): Promise<Scan[]> {
  return apiFetch<Scan[]>('/scans');
}

export function getScan(scanId: string): Promise<ScanDetail> {
  return apiFetch<ScanDetail>(`/scans/${scanId}`);
}

export function createScan(url: string): Promise<Scan> {
  return apiFetch<Scan>('/scans', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}
