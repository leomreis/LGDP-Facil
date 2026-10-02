import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../../lib/useAuth';
import { Button } from '../ui/Button';

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm transition-colors ${isActive ? 'text-primary' : 'text-text-muted hover:text-text'}`;

export function AppShell() {
  const { signOut } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="flex items-center gap-6 border-b border-border px-8 py-4">
        <span className="font-bold">LGPD Fácil</span>
        <nav className="flex flex-1 gap-4">
          <NavLink to="/scans" className={navLinkClass}>
            Scans
          </NavLink>
          <NavLink to="/policies" className={navLinkClass}>
            Políticas
          </NavLink>
          <NavLink to="/team" className={navLinkClass}>
            Equipe
          </NavLink>
        </nav>
        <Button variant="secondary" type="button" onClick={() => void signOut()}>
          Sair
        </Button>
      </header>
      <main className="mx-auto max-w-3xl px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
