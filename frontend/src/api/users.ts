import { apiFetch, ApiError } from './client';
import type { User } from '../types/api';

/** null quando o usuário ainda não concluiu o onboarding (403) — não é erro. */
export async function getMe(): Promise<User | null> {
  try {
    return await apiFetch<User>('/users/me');
  } catch (erro) {
    if (erro instanceof ApiError && (erro.status === 403 || erro.status === 401)) {
      return null;
    }
    throw erro;
  }
}
