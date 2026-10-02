import { apiFetch } from './client';
import type { PolicyDocumentType, PublicPolicyDocument } from '../types/api';

/**
 * Slug em português usado na URL pública — é o link que a PME cola no rodapé
 * do próprio site, então "/privacidade" lê melhor que "/privacy_policy".
 */
export const SLUG_BY_TIPO: Record<PolicyDocumentType, string> = {
  privacy_policy: 'privacidade',
  terms_of_use: 'termos',
  cookie_notice: 'cookies',
};

export function tipoFromSlug(slug: string | undefined): PolicyDocumentType | null {
  const par = Object.entries(SLUG_BY_TIPO).find(([, s]) => s === slug);
  return par ? (par[0] as PolicyDocumentType) : null;
}

export function publicPolicyUrl(companyId: string, tipo: PolicyDocumentType): string {
  return `${window.location.origin}/p/${companyId}/${SLUG_BY_TIPO[tipo]}`;
}

export function getPublicPolicyDocument(
  companyId: string,
  tipo: PolicyDocumentType,
): Promise<PublicPolicyDocument> {
  return apiFetch<PublicPolicyDocument>(`/public/companies/${companyId}/policy-documents/${tipo}`);
}
