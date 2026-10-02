import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../lib/useAuth';

export function ProtectedRoute() {
  const { session, loading } = useAuth();

  if (loading) {
    return <p className="p-8 text-center text-text-muted">Carregando...</p>;
  }

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
