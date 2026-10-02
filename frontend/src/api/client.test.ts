import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
    },
  },
}));

import { supabase } from '../lib/supabase';
import { apiFetch, ApiError } from './client';

const getSessionMock = vi.mocked(supabase.auth.getSession);

function respostaFalsa(body: unknown, status: number) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response;
}

describe('apiFetch', () => {
  beforeEach(() => {
    getSessionMock.mockResolvedValue({ data: { session: null } } as never);
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetAllMocks();
  });

  it('anexa o Authorization quando há sessão ativa', async () => {
    getSessionMock.mockResolvedValue({
      data: { session: { access_token: 'token-123' } },
    } as never);
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({ ok: true }, 200));

    await apiFetch('/scans');

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get('Authorization')).toBe('Bearer token-123');
  });

  it('não envia Authorization quando não há sessão', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({}, 200));

    await apiFetch('/health');

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.has('Authorization')).toBe(false);
  });

  it('devolve o corpo desserializado em uma resposta de sucesso', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({ id: 'abc' }, 200));

    const resultado = await apiFetch<{ id: string }>('/scans/abc');

    expect(resultado).toEqual({ id: 'abc' });
  });

  it('lança ApiError com o status e a mensagem do backend em erro', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({ detail: 'Scan não encontrado' }, 404));

    await expect(apiFetch('/scans/xyz')).rejects.toMatchObject({
      status: 404,
      message: 'Scan não encontrado',
    });
  });

  it('lança ApiError com mensagem genérica quando o backend não manda detail', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaFalsa({}, 500));

    await expect(apiFetch('/scans')).rejects.toBeInstanceOf(ApiError);
  });

  it('extrai a mensagem de um erro de validação do Pydantic (422, detail em lista)', async () => {
    vi.mocked(fetch).mockResolvedValue(
      respostaFalsa(
        {
          detail: [
            { loc: ['body', 'cnpj'], msg: 'Value error, CNPJ inválido', type: 'value_error' },
          ],
        },
        422,
      ),
    );

    await expect(apiFetch('/onboarding')).rejects.toMatchObject({
      status: 422,
      message: 'cnpj: Value error, CNPJ inválido',
    });
  });

  it('junta várias mensagens de validação quando mais de um campo falha', async () => {
    vi.mocked(fetch).mockResolvedValue(
      respostaFalsa(
        {
          detail: [
            { loc: ['body', 'cnpj'], msg: 'CNPJ inválido' },
            { loc: ['body', 'user_name'], msg: 'Field required' },
          ],
        },
        422,
      ),
    );

    await expect(apiFetch('/onboarding')).rejects.toMatchObject({
      message: 'cnpj: CNPJ inválido; user_name: Field required',
    });
  });

  it('devolve undefined em 204 sem tentar parsear corpo vazio', async () => {
    const jsonSpy = vi.fn();
    vi.mocked(fetch).mockResolvedValue({ ok: true, status: 204, json: jsonSpy } as never);

    const resultado = await apiFetch('/scans/abc');

    expect(resultado).toBeUndefined();
    expect(jsonSpy).not.toHaveBeenCalled();
  });
});
