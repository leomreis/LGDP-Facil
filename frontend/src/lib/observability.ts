import * as Sentry from '@sentry/react';
import posthog from 'posthog-js';

/**
 * Sem as variáveis de ambiente correspondentes, cada init() é um no-op — o
 * app funciona normalmente sem conta nenhuma no Sentry/PostHog, como hoje.
 */
export function initObservability(): void {
  const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
  if (sentryDsn) {
    Sentry.init({ dsn: sentryDsn, environment: import.meta.env.MODE });
  }

  const posthogKey = import.meta.env.VITE_POSTHOG_KEY;
  if (posthogKey) {
    posthog.init(posthogKey, {
      api_host: import.meta.env.VITE_POSTHOG_HOST ?? 'https://us.i.posthog.com',
    });
  }
}
