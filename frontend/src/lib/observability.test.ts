import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@sentry/react', () => ({ init: vi.fn() }));
vi.mock('posthog-js', () => ({ default: { init: vi.fn() } }));

import * as Sentry from '@sentry/react';
import posthog from 'posthog-js';
import { initObservability } from './observability';

describe('initObservability', () => {
  const envOriginal = { ...import.meta.env };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    Object.assign(import.meta.env, envOriginal);
    delete (import.meta.env as Record<string, unknown>).VITE_SENTRY_DSN;
    delete (import.meta.env as Record<string, unknown>).VITE_POSTHOG_KEY;
  });

  it('não inicializa nada sem as variáveis de ambiente', () => {
    initObservability();

    expect(Sentry.init).not.toHaveBeenCalled();
    expect(posthog.init).not.toHaveBeenCalled();
  });

  it('inicializa o Sentry quando VITE_SENTRY_DSN está definida', () => {
    (import.meta.env as Record<string, unknown>).VITE_SENTRY_DSN = 'https://fake@sentry.io/1';

    initObservability();

    expect(Sentry.init).toHaveBeenCalledWith(
      expect.objectContaining({ dsn: 'https://fake@sentry.io/1' }),
    );
  });

  it('inicializa o PostHog quando VITE_POSTHOG_KEY está definida', () => {
    (import.meta.env as Record<string, unknown>).VITE_POSTHOG_KEY = 'phc_fake';

    initObservability();

    expect(posthog.init).toHaveBeenCalledWith('phc_fake', expect.any(Object));
  });
});
