import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { getMe } from '../../api/users';

type Status = 'checking' | 'onboarded' | 'not-onboarded' | 'error';

/**
 * Sessão válida no Supabase não implica linha em `users` no backend — o
 * onboarding cria essa linha. Esta trava consulta /users/me uma vez e decide
 * entre deixar passar ou mandar para /onboarding.
 */
export function OnboardingGate() {
  const [status, setStatus] = useState<Status>('checking');

  useEffect(() => {
    let ativo = true;
    getMe()
      .then((user) => {
        if (ativo) setStatus(user ? 'onboarded' : 'not-onboarded');
      })
      .catch(() => {
        if (ativo) setStatus('error');
      });
    return () => {
      ativo = false;
    };
  }, []);

  if (status === 'checking') {
    return <p className="p-8 text-center text-text-muted">Carregando...</p>;
  }

  if (status === 'not-onboarded') {
    return <Navigate to="/onboarding" replace />;
  }

  if (status === 'error') {
    return (
      <p className="p-8 text-center text-danger">
        Não foi possível verificar sua conta. Recarregue a página.
      </p>
    );
  }

  return <Outlet />;
}
