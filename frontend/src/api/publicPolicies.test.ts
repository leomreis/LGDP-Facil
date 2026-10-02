import { describe, expect, it } from 'vitest';
import { SLUG_BY_TIPO, publicPolicyUrl, tipoFromSlug } from './publicPolicies';

describe('tipoFromSlug', () => {
  it('converte cada slug de volta no tipo correspondente', () => {
    for (const [tipo, slug] of Object.entries(SLUG_BY_TIPO)) {
      expect(tipoFromSlug(slug)).toBe(tipo);
    }
  });

  it('devolve null para slug desconhecido ou ausente', () => {
    expect(tipoFromSlug('contrato')).toBeNull();
    expect(tipoFromSlug(undefined)).toBeNull();
  });
});

describe('publicPolicyUrl', () => {
  it('monta o link público com o slug em português', () => {
    expect(publicPolicyUrl('abc-123', 'privacy_policy')).toBe(
      `${window.location.origin}/p/abc-123/privacidade`,
    );
  });
});
