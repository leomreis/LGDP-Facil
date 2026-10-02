import { apiFetch } from './client';
import type { Company, CompanyCreate } from '../types/api';

export function createCompany(data: CompanyCreate): Promise<Company> {
  return apiFetch<Company>('/companies', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
