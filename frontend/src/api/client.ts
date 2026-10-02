import { supabase } from '../lib/supabase';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

/**
 * `detail` de erro do FastAPI vem em dois formatos: string simples (erros que
 * a gente levanta com HTTPException) ou lista de objetos de validação do
 * Pydantic (422, um por campo inválido: {loc, msg, type}). Sem tratar o
 * segundo caso, todo erro de validação vira o genérico "Erro 422 em /rota" —
 * inútil para o usuário entender o que preencheu errado.
 */
function extrairMensagemDeErro(corpo: unknown, status: number, path: string): string {
  const detail = (corpo as { detail?: unknown } | null)?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    const mensagens = detail
      .map((item: { loc?: unknown[]; msg?: string }) => {
        const campo = Array.isArray(item.loc) ? item.loc.at(-1) : undefined;
        return campo ? `${campo}: ${item.msg}` : item.msg;
      })
      .filter(Boolean);
    if (mensagens.length > 0) {
      return mensagens.join('; ');
    }
  }

  return `Erro ${status} em ${path}`;
}

/**
 * Cliente HTTP central: toda chamada à API passa por aqui, para que o token do
 * Supabase seja anexado uma única vez em vez de repetido em cada função de
 * src/api/. Sessão sem token ainda chama a rota — o backend decide se ela exige
 * autenticação; isso mantém o cliente simples e a regra de autorização num
 * lugar só (o backend).
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });

  if (!response.ok) {
    const corpo = await response.json().catch(() => ({}));
    const mensagem =
      response.status === 429
        ? 'Muitas requisições em pouco tempo. Aguarde um momento e tente de novo.'
        : extrairMensagemDeErro(corpo, response.status, path);
    throw new ApiError(response.status, mensagem);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/** Só o token da sessão atual — usado por chamadas que não passam por apiFetch
 * (ex.: download de arquivo binário, onde a resposta não é JSON). */
export async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}
