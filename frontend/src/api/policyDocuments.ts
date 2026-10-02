import { apiFetch } from './client';
import type { PolicyDocument, PolicyDocumentStatus, PolicyDocumentType } from '../types/api';

export function listPolicyDocuments(): Promise<PolicyDocument[]> {
  return apiFetch<PolicyDocument[]>('/policy-documents');
}

export function createPolicyDocument(
  tipo: PolicyDocumentType,
  scanId: string,
): Promise<PolicyDocument> {
  return apiFetch<PolicyDocument>('/policy-documents', {
    method: 'POST',
    body: JSON.stringify({ tipo, scan_id: scanId }),
  });
}

export function updatePolicyDocumentStatus(
  documentId: string,
  status: PolicyDocumentStatus,
): Promise<PolicyDocument> {
  return apiFetch<PolicyDocument>(`/policy-documents/${documentId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}
