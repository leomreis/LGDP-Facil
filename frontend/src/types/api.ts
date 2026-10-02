// Espelha os schemas Pydantic do backend (backend/app/schemas/). Mantidos
// manualmente em sincronia — gerar via openapi-typescript é a evolução natural
// (ver Plano de Desenvolvimento, seção 3.2), mas exige o backend publicado.

export type FindingType = 'form' | 'cookies' | 'third_party_script';

export type CategoryType = 'cpf' | 'email' | 'phone' | 'address' | 'full_name' | 'other';

export type RiskType = 'low' | 'medium' | 'high';

export type ScanStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export type PolicyDocumentType = 'privacy_policy' | 'terms_of_use' | 'cookie_notice';

export type PolicyDocumentStatus = 'draft' | 'published';

export interface Company {
  id: string;
  name: string;
  cnpj: string;
  site_url: string | null;
  software_name: string | null;
  created_at: string;
}

export interface CompanyCreate {
  name: string;
  cnpj: string;
  site_url?: string | null;
  software_name?: string | null;
}

export interface ScanFinding {
  id: string;
  finding_type: FindingType;
  categoria_dado_pessoal: CategoryType;
  risk: RiskType;
  location: string;
}

export interface Scan {
  id: string;
  company_id: string;
  url: string;
  status: ScanStatus;
  created_at: string | null;
  completed_at: string | null;
}

export interface ScanDetail extends Scan {
  findings: ScanFinding[];
}

export interface Report {
  id: string;
  scan_id: string;
  score_conformidade: number;
  resumo_executivo: string;
  pdf_url: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PolicyDocument {
  id: string;
  company_id: string;
  tipo: PolicyDocumentType;
  content: string;
  version: string;
  status: PolicyDocumentStatus;
  created_at: string | null;
}

export interface OnboardingCreate {
  company_name: string;
  cnpj: string;
  site_url?: string | null;
  software_name?: string | null;
  user_name: string;
}

export interface OnboardingResponse {
  company: Company;
  user_id: string;
}

export interface User {
  id: string;
  company_id: string;
  name: string;
  email: string;
  role: string;
  created_at: string | null;
}

export interface TeamInviteCreate {
  email: string;
  name: string;
}
