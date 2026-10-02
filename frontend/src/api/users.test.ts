import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/supabase', () => ({
  supabase: { auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) } },
}));

import { getMe } from './users';

function respostaFalsa(body: unknown, status: number) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response;
}

describe('getMe', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('devolve o usuário quando o onboarding já foi feito', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({ id: 'u1', email: 'x@x.com' }, 200));

    const usuario = await getMe();

    expect(usuario?.id).toBe('u1');
  });

  it('devolve null em 403 (onboarding pendente) — não é erro', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({ detail: 'sem empresa' }, 403));

    expect(await getMe()).toBeNull();
  });

  it('devolve null em 401 (sem sessão válida) — não é erro', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({ detail: 'token inválido' }, 401));

    expect(await getMe()).toBeNull();
  });

  it('propaga erro 500', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({}, 500));

    await expect(getMe()).rejects.toMatchObject({ status: 500 });
  });
});
